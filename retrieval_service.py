"""Live-first retrieval orchestration with provenance-derived actual modes."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import time
from typing import Callable
from uuid import uuid4

from app_settings import SETTINGS
from models import Paper, PurposeContract
from openalex_client import (
    OpenAlexClient, OpenAlexRequestError, QueryBudget, default_query_budget,
    get_openalex_client,
)
from paper_fetchers import (
    PaperCache, deduplicate_papers, fetch_openalex, fetch_arxiv,
    fetch_papers_detailed,
)
from run_models import (
    ResearchRun, SourceRetrievalResult, StageRun, paper_provenance, utc_now,
)
from pipeline_quality import apply_estimated_relevance
from text_processing import fingerprint

FixtureLoader = Callable[..., object]


def _cache_key(
    query: str, source: str, maximum: int, years: tuple[int, int],
) -> str:
    normalized_query = " ".join(query.casefold().split())
    selected_fields = (
        "id,title,publication_year,doi,primary_location,"
        "abstract_inverted_index,cited_by_count"
        if source == "openalex" else "atom-default"
    )
    return (
        f"live-v3:{source}:{normalized_query}:{years[0]}:{years[1]}:"
        f"{selected_fields}:per_page={maximum}:problem-query-v2"
    )


def retrieve_corpus(
    purpose: PurposeContract,
    queries: list[str],
    *,
    requested_mode: str = "LIVE",
    sources: list[str] | None = None,
    maximum_per_query: int = 12,
    maximum_total: int = 80,
    allow_cache: bool = True,
    allow_offline_fallback: bool = False,
    force_fresh: bool = False,
    adapters: dict[str, Callable[..., list[Paper]]] | None = None,
    cache_directory: Path = Path(".paper_cache"),
    fixture_loader: FixtureLoader | None = None,
    fixture_path: str = "",
    engine_mode: str = SETTINGS.gap_engine_mode,
    stage_name: str = "broad_ml_retrieval",
    openalex_client_instance: OpenAlexClient | None = None,
    openalex_budget: QueryBudget | None = None,
) -> tuple[list[Paper], ResearchRun]:
    """Retrieve papers and derive truth from paper-level provenance."""
    started = time.perf_counter()
    requested_mode = requested_mode.upper().replace(" ", "_")
    run = ResearchRun.create(
        purpose.purpose_id, requested_mode, engine_mode,
        purpose.publication_window,
    )
    run.ml_queries = list(queries)
    run.query_count = len(queries)
    run.broad_query_count = len(queries) if stage_name == "broad_ml_retrieval" else 0
    run.focused_query_count = len(queries) if stage_name == "focused_ml_retrieval" else 0
    run.external_query_count = len(queries) if stage_name == "external_retrieval" else 0
    run.total_query_count = len(queries)
    run.cache_ttl_seconds = SETTINGS.cache_ttl_seconds
    sources = sources or ["openalex", "arxiv"]
    run.sources_attempted = list(sources)
    cache = PaperCache(cache_directory)
    openalex_client = openalex_client_instance or get_openalex_client()
    if openalex_budget is None:
        openalex_budget = openalex_client.begin_run(
            default_query_budget(openalex_client.authentication_mode)
        )
    if adapters is None:
        adapters = {
            "openalex": lambda query, maximum, start, end: fetch_openalex(
                query, maximum, start, end, client=openalex_client,
                budget=openalex_budget, stage_name=stage_name,
            ),
            "arxiv": fetch_arxiv,
        }
    all_papers: list[Paper] = []
    stage = StageRun(
        stage_id=f"{run.run_id}:{stage_name}", stage_name=stage_name,
        parent_run_id=run.run_id, started_at=run.created_at_utc,
        requested_mode=requested_mode, query_count=len(queries),
        queries=list(queries),
    )

    if requested_mode == "OFFLINE_FIXTURE":
        fixture_papers = fixture_loader() if fixture_loader else []
        for rank, paper in enumerate(fixture_papers, 1):
            paper_provenance(
                paper, "offline_fixture", "fixture", f"fixture:{uuid4().hex[:8]}",
                fixture_path=fixture_path, rank=rank,
            )
        all_papers.extend(fixture_papers)
        run.fixture_paths = [fixture_path] if fixture_path else []
        run.fixture_version = "bundled-v1"
        run.raw_paper_count = len(fixture_papers)
        run.source_results.append(SourceRetrievalResult(
            source=fixture_path or "offline_fixture",
            source_type="fixture", queries_attempted=list(queries),
            request_count=1, success_count=1 if fixture_papers else 0,
            failure_count=0 if fixture_papers else 1,
            raw_returned_count=len(fixture_papers),
            unique_returned_count=len(fixture_papers),
            api_status="fixture loaded", started_at=run.created_at_utc,
            completed_at=utc_now(),
            actual_origin="OFFLINE_FIXTURE",
            paper_ids=[paper.paper_id for paper in fixture_papers],
        ))
    else:
        run.live_request_attempted = requested_mode == "LIVE"
        for source in sources:
            source_started = time.perf_counter()
            result = SourceRetrievalResult(
                source=source, source_type="scholarly_api",
                queries_attempted=list(queries), started_at=utc_now(),
            )
            source_papers: list[Paper] = []
            for query_index, query in enumerate(queries):
                key = _cache_key(
                    query, source, maximum_per_query,
                    purpose.publication_window,
                )
                run.cache_keys.append(fingerprint(key))
                cached = (
                    cache.get_entry(key) if allow_cache and not force_fresh else None
                )
                if cached is not None:
                    cached_papers, _, created_at = cached
                    result.cache_hits += 1
                    run.cache_created_at = utc_now() if not created_at else (
                        __import__("datetime").datetime.fromtimestamp(
                            created_at, __import__("datetime").timezone.utc
                        ).isoformat(timespec="seconds")
                    )
                    run.cache_age_seconds = max(
                        run.cache_age_seconds, time.time() - created_at
                    )
                    result.cache_age_seconds.append(time.time() - created_at)
                    result.actual_origin = "CACHE_ONLY"
                    result.api_status = "not_called_cache_hit"
                    for rank, paper in enumerate(cached_papers, 1):
                        paper_provenance(
                            paper, f"cache_{source}", f"q:{query_index}",
                            f"cache:{fingerprint(key)}", cache_key=fingerprint(key),
                            rank=rank,
                        )
                    source_papers.extend(cached_papers)
                    result.raw_returned_count += len(cached_papers)
                    continue
                result.cache_misses += 1
                if requested_mode == "CACHE":
                    continue
                result.request_count += 1
                try:
                    fetched, diagnostics = fetch_papers_detailed(
                        query, [source], maximum_per_query,
                        *purpose.publication_window, adapters=adapters,
                    )
                    if diagnostics.source_failures and not fetched:
                        result.failure_count += 1
                        result.failure_messages.extend(
                            diagnostics.source_failures.values()
                        )
                    else:
                        result.success_count += 1
                        result.actual_origin = (
                            "MIXED" if result.cache_hits else "LIVE"
                        )
                    result.raw_returned_count += len(fetched)
                    result.api_status = "success" if fetched else "empty"
                    for rank, paper in enumerate(fetched, 1):
                        paper_provenance(
                            paper, f"live_{source}", f"q:{query_index}",
                            f"request:{uuid4().hex[:10]}", rank=rank,
                        )
                    source_papers.extend(fetched)
                    if fetched:
                        cache.put_entry(key, fetched, asdict(diagnostics))
                except OpenAlexRequestError as exc:
                    result.failure_count += 1
                    result.api_status = exc.category
                    result.failure_messages.append(str(exc))
                    skipped = len(queries) - query_index - 1
                    openalex_client.state.skipped_queries += skipped
                    break
                except Exception as exc:
                    result.failure_count += 1
                    result.failure_messages.append(f"{type(exc).__name__}: {exc}")
                if SETTINGS.rate_limit_seconds:
                    time.sleep(SETTINGS.rate_limit_seconds)
            unique_source = deduplicate_papers(source_papers)
            result.unique_returned_count = len(unique_source)
            result.paper_ids = [paper.paper_id for paper in unique_source]
            result.completed_at = utc_now()
            result.duration_seconds = round(time.perf_counter() - source_started, 4)
            result.rate_limit_wait_seconds = (
                SETTINGS.rate_limit_seconds * result.request_count
            )
            if result.failure_messages:
                run.source_failures[source] = "; ".join(result.failure_messages)
            run.source_results.append(result)
            all_papers.extend(unique_source)

        if not all_papers and allow_offline_fallback and fixture_loader:
            fixture_papers = fixture_loader()
            for rank, paper in enumerate(fixture_papers, 1):
                paper_provenance(
                    paper, "offline_fixture", "fallback",
                    f"fixture:{uuid4().hex[:8]}", fixture_path=fixture_path,
                    rank=rank,
                )
            all_papers.extend(fixture_papers)
            run.fixture_paths = [fixture_path] if fixture_path else []
            run.fixture_version = "bundled-v1"
            run.fallback_occurred = True
            run.fallback_reason = (
                "All selected scholarly sources produced no usable papers; "
                "the user-authorized offline demonstration was loaded."
            )
            run.warnings.append(
                "DEMONSTRATION ONLY: bundled papers are not a current literature review."
            )
            run.source_results.append(SourceRetrievalResult(
                source=fixture_path or "offline_fixture", source_type="fixture",
                queries_attempted=list(queries), request_count=1,
                success_count=1, raw_returned_count=len(fixture_papers),
                unique_returned_count=len(fixture_papers),
                fallback_contribution=len(fixture_papers),
                started_at=utc_now(), completed_at=utc_now(),
                actual_origin="OFFLINE_FIXTURE",
                paper_ids=[paper.paper_id for paper in fixture_papers],
            ))

    run.raw_paper_count = max(
        run.raw_paper_count,
        sum(item.raw_returned_count for item in run.source_results),
    )
    papers = deduplicate_papers(all_papers)
    if len(papers) > maximum_total:
        papers = papers[:maximum_total]
        run.truncation_applied = True
        run.truncation_reason = f"Maximum total papers limited the corpus to {maximum_total}."
    apply_estimated_relevance(papers, purpose)
    run.finalize_from_papers(papers)
    run.retrieval_duration_seconds = round(time.perf_counter() - started, 4)
    run.overall_wall_clock_duration_seconds = run.retrieval_duration_seconds
    run.sum_source_request_duration_seconds = round(sum(
        item.duration_seconds for item in run.source_results
    ), 4)
    stage.completed_at = utc_now()
    stage.wall_clock_duration_seconds = run.retrieval_duration_seconds
    stage.actual_mode = run.actual_search_mode
    stage.source_results = list(run.source_results)
    stage.raw_input_count = run.raw_paper_count
    stage.output_count = len(papers)
    stage.accepted_count = run.automatically_relevant_paper_count
    stage.rejected_count = len(papers) - stage.accepted_count
    stage.cache_hits = sum(item.cache_hits for item in run.source_results)
    stage.cache_misses = sum(item.cache_misses for item in run.source_results)
    stage.sum_source_request_duration_seconds = (
        run.sum_source_request_duration_seconds
    )
    stage.truncation = run.truncation_reason
    stage.model_backend = "source adapters"
    stage.model_version = "retrieval-service-v2"
    stage.metadata["query_performance"] = [{
        "query_id": f"q:{index}",
        "query": query,
        "retained_paper_count": sum(
            f"q:{index}" in paper.query_ids for paper in papers
        ),
        "automatically_relevant_count": sum(
            f"q:{index}" in paper.query_ids
            and paper.estimated_relevance_label in {
                "ESTIMATED_HIGH", "ESTIMATED_MEDIUM",
            }
            for paper in papers
        ),
        "live_paper_count": sum(
            f"q:{index}" in paper.query_ids
            and paper.retrieval_origin.startswith("live_")
            for paper in papers
        ),
        "cache_paper_count": sum(
            f"q:{index}" in paper.query_ids
            and paper.retrieval_origin.startswith("cache_")
            for paper in papers
        ),
    } for index, query in enumerate(queries)]
    if "openalex" in sources:
        stage.metadata["openalex_rate_limit"] = (
            openalex_client.state.safe_dict()
        )
        stage.metadata["openalex_query_budget"] = {
            "authentication_mode": openalex_budget.authentication_mode,
            "total_limit": openalex_budget.total_limit,
            "total_used": openalex_budget.total_used,
            "stage_limits": dict(openalex_budget.stage_limits),
            "stage_used": dict(openalex_budget.stage_used),
        }
        if openalex_client.authentication_mode == "ANONYMOUS":
            run.warnings.append(
                "OpenAlex is operating with a conservative anonymous request budget."
            )
    run.stages.append(stage)
    if run.actual_search_mode == "FAILED":
        run.errors.append("No usable literature corpus was produced.")
    return papers, run
