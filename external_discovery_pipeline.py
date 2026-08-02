"""Direction-scoped external evidence discovery, independent of Streamlit."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from alignment import align
from app_settings import SETTINGS
from mechanism_mining import cross_domain_only, extract_mechanisms
from models import AlignmentResult, GapSignature, MechanismSignature, Paper, PurposeContract
from openalex_client import default_query_budget, get_openalex_client
from paper_fetchers import deduplicate_papers
from query_generation import (
    CrossDomainProblemSignature, DomainSelection, generate_external_queries,
    normalize_cross_domain_problem, select_external_domains,
)
from retrieval_service import retrieve_corpus
from run_models import ResearchRun, StageRun, utc_now
from signatures import load_mechanism_seeds
from ux_models import DirectionSummary


@dataclass(frozen=True)
class SearchPolicy:
    requested_mode: str
    sources: tuple[str, ...] = ("openalex", "arxiv")
    allow_cache: bool = True
    force_fresh: bool = False
    allow_offline_fallback: bool = False
    maximum_per_query: int = 6
    maximum_total: int = 60

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_mode": self.requested_mode,
            "sources": list(self.sources),
            "allow_cache": self.allow_cache,
            "force_fresh": self.force_fresh,
            "allow_offline_fallback": self.allow_offline_fallback,
            "maximum_per_query": self.maximum_per_query,
            "maximum_total": self.maximum_total,
        }

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "SearchPolicy":
        return cls(
            requested_mode=str(value.get("requested_mode", "LIVE")),
            sources=tuple(value.get("sources", ("openalex", "arxiv"))),
            allow_cache=bool(value.get("allow_cache", True)),
            force_fresh=bool(value.get("force_fresh", False)),
            allow_offline_fallback=bool(value.get("allow_offline_fallback", False)),
            maximum_per_query=int(value.get("maximum_per_query", 6)),
            maximum_total=int(value.get("maximum_total", 60)),
        )


@dataclass
class ExternalDiscoveryResult:
    parent_run_id: str
    selected_direction_id: str
    selected_gap_id: str
    cross_domain_problem_signature: CrossDomainProblemSignature
    ranked_domain_selections: list[DomainSelection]
    accepted_queries_by_domain: dict[str, list[str]]
    rejected_queries: list[dict[str, str]]
    papers: list[Paper]
    retrieval_run: ResearchRun
    mechanisms: list[MechanismSignature]
    rejected_mechanisms: list[dict[str, str]]
    alignments: list[AlignmentResult]
    accepted_alignments: list[AlignmentResult]
    stage_diagnostics: dict[str, object]
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    reused_from_session: bool = False

    def identity(self) -> tuple[str, str, str]:
        return self.parent_run_id, self.selected_direction_id, self.selected_gap_id


def _stage(
    run: ResearchRun, name: str, raw: int, output: int, accepted: int,
    rejected: int, backend: str, warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> StageRun:
    return StageRun(
        stage_id=f"{run.run_id}:{name}", stage_name=name,
        parent_run_id=run.run_id, started_at=utc_now(), completed_at=utc_now(),
        requested_mode=run.requested_search_mode,
        actual_mode=run.actual_search_mode, raw_input_count=raw,
        output_count=output, accepted_count=accepted, rejected_count=rejected,
        model_backend=backend, warnings=warnings or [], errors=errors or [],
    )


def discover_external_mechanisms_for_direction(
    *, purpose: PurposeContract, direction: DirectionSummary, gap: GapSignature,
    parent_run: ResearchRun, search_policy: SearchPolicy,
    fixture_loader: Callable[[], list[Paper]] | None = None,
    adapters: dict[str, Callable[..., list[Paper]]] | None = None,
    progress_callback: Callable[[int, str], None] | None = None,
    cache_directory: Path = Path(".paper_cache"),
) -> ExternalDiscoveryResult:
    """Run domain selection through hard structural alignment for one direction."""
    progress = progress_callback or (lambda value, label: None)
    progress(5, "1/6 Translating the research gap")
    signature = normalize_cross_domain_problem(gap)
    progress(18, "2/6 Selecting external disciplines")
    selections = select_external_domains(signature, SETTINGS.maximum_external_domains)
    selected_domains = [item.domain for item in selections if item.selected]
    base_queries = generate_external_queries(gap, selected_domains)
    # Keep external queries native to their source discipline. The ML slot is
    # introduced later during typed structural alignment, never retrieval.
    all_queries_by_domain = {
        domain: list(queries) for domain, queries in base_queries.items()
    }
    queries_by_domain = {
        domain: list(queries[:2])
        for domain, queries in list(all_queries_by_domain.items())[:3]
    }
    query_pairs = [
        (domain, query) for domain, queries in queries_by_domain.items()
        for query in queries
    ]
    queries = [query for _, query in query_pairs]
    errors: list[str] = []
    warnings: list[str] = []
    if not selected_domains:
        errors.append("No external domains passed relevance selection.")
    if not queries:
        errors.append("External query generation produced no accepted queries.")

    requested_mode = search_policy.requested_mode.upper().replace(" ", "_")
    progress(35, "3/6 Searching external literature")
    openalex_client = get_openalex_client()
    openalex_budget = openalex_client.begin_run(
        default_query_budget(openalex_client.authentication_mode)
    )
    papers, retrieval_run = retrieve_corpus(
        purpose, queries, requested_mode=requested_mode,
        sources=list(search_policy.sources),
        maximum_per_query=search_policy.maximum_per_query,
        maximum_total=search_policy.maximum_total,
        allow_cache=search_policy.allow_cache,
        force_fresh=search_policy.force_fresh,
        allow_offline_fallback=search_policy.allow_offline_fallback,
        adapters=adapters, fixture_loader=fixture_loader,
        cache_directory=cache_directory,
        fixture_path="data/offline_fixtures/external_papers.json",
        stage_name="external_retrieval",
        openalex_client_instance=openalex_client,
        openalex_budget=openalex_budget,
    )
    stage_two_used = False
    initial_mechanisms, _ = extract_mechanisms(papers)
    domain_items = list(all_queries_by_domain.items())
    stage_two_pairs = [
        (domain, domain_queries[2])
        for domain, domain_queries in domain_items[:3]
        if len(domain_queries) > 2
    ]
    if len(domain_items) > 3 and domain_items[3][1]:
        stage_two_pairs.append((domain_items[3][0], domain_items[3][1][0]))
    stage_two_pairs = stage_two_pairs[:4]
    needs_live_expansion = (
        requested_mode == "LIVE"
        and (len(papers) < 8 or len(cross_domain_only(initial_mechanisms)) < 3)
        and openalex_client.state.circuit_state == "CLOSED"
    )
    # Cache replay must probe the complete bounded query plan: a prior live run
    # may have expanded adaptively, and cache-only mode cannot infer that choice
    # from the stage-one response alone.
    needs_cache_replay = requested_mode == "CACHE"
    if stage_two_pairs and (needs_live_expansion or needs_cache_replay):
        stage_two_used = True
        stage_two_queries = [query for _, query in stage_two_pairs]
        more_papers, more_run = retrieve_corpus(
            purpose, stage_two_queries, requested_mode=requested_mode,
            sources=list(search_policy.sources),
            maximum_per_query=search_policy.maximum_per_query,
            maximum_total=search_policy.maximum_total,
            allow_cache=search_policy.allow_cache,
            force_fresh=search_policy.force_fresh,
            allow_offline_fallback=False, adapters=adapters,
            cache_directory=cache_directory, stage_name="external_retrieval",
            openalex_client_instance=openalex_client,
            openalex_budget=openalex_budget,
        )
        for domain, query in stage_two_pairs:
            queries_by_domain.setdefault(domain, []).append(query)
        second_offset = len(query_pairs)
        for paper in more_papers:
            indices = [
                int(item.split(":", 1)[1]) for item in paper.query_ids
                if item.startswith("q:")
            ]
            if indices and indices[0] < len(stage_two_pairs):
                paper.domain = stage_two_pairs[indices[0]][0]
                paper.query_ids = [
                    f"q:{second_offset + indices[0]}"
                    if item.startswith("q:") else item
                    for item in paper.query_ids
                ]
        query_pairs.extend(stage_two_pairs)
        queries.extend(stage_two_queries)
        papers = deduplicate_papers([*papers, *more_papers])[
            :search_policy.maximum_total
        ]
        retrieval_run.source_results.extend(more_run.source_results)
        retrieval_run.source_failures.update(more_run.source_failures)
        retrieval_run.stages.extend(more_run.stages)
        retrieval_run.raw_paper_count += more_run.raw_paper_count
        retrieval_run.query_count += more_run.query_count
        retrieval_run.total_query_count += more_run.total_query_count
        retrieval_run.external_query_count += more_run.external_query_count
        retrieval_run.finalize_from_papers(papers)
    retrieval_run.parent_run_id = parent_run.run_id
    retrieval_run.selected_direction_id = direction.direction_id
    retrieval_run.selected_gap_id = gap.gap_id
    retrieval_run.external_queries_by_domain = queries_by_domain
    for paper in papers:
        indices = [
            int(item.split(":", 1)[1]) for item in paper.query_ids
            if item.startswith("q:")
        ]
        if indices and indices[0] < len(query_pairs):
            paper.domain = query_pairs[indices[0]][0]

    if requested_mode == "CACHE" and not papers:
        errors.append(
            "No matching cached external evidence was found. Run a live "
            "external search or choose another direction."
        )
    elif not papers:
        errors.append("External literature retrieval produced no usable papers.")

    progress(55, "4/6 Extracting mechanisms")
    mechanisms, rejected_mechanisms = extract_mechanisms(papers)
    mechanisms = cross_domain_only(mechanisms)
    if not mechanisms and requested_mode == "OFFLINE_FIXTURE":
        mechanisms = cross_domain_only(load_mechanism_seeds())
        warnings.append(
            "OFFLINE DEMONSTRATION: curated mechanism seeds were used because "
            "the bundled papers yielded no operational mechanism."
        )
    elif papers and not mechanisms:
        errors.append("External papers were found, but no operational mechanism passed extraction.")
    for mechanism in mechanisms:
        mechanism.research_run_id = parent_run.run_id
    progress(72, "5/6 Testing structural alignment")
    alignments = [align(gap, mechanism, purpose) for mechanism in mechanisms]
    for item in alignments:
        item.research_run_id = parent_run.run_id
    accepted = [item for item in alignments if not item.rejected]
    if mechanisms and not accepted:
        errors.append("Mechanisms were extracted, but no structural alignment passed hard validation.")

    retrieved_paper_ids = {paper.paper_id for paper in papers}
    mechanism_paper_ids = {
        paper_id for mechanism in mechanisms for paper_id in mechanism.evidence_paper_ids
    } & retrieved_paper_ids
    if (retrieval_run.automatically_relevant_paper_count == 0
            and mechanism_paper_ids):
        warnings.append(
            "No external paper passed problem-relevance scoring although "
            "operational mechanism language was extracted; candidates remain "
            "subject to hard evidence and alignment gates."
        )
    for source in retrieval_run.source_results:
        source.mechanism_bearing_paper_count = len(
            set(source.paper_ids) & mechanism_paper_ids
        )
    parent_run.external_requested_mode = requested_mode
    parent_run.external_actual_mode = retrieval_run.actual_search_mode
    parent_run.external_queries_by_domain = queries_by_domain
    parent_run.external_query_count = len(queries)
    parent_run.total_query_count = (
        parent_run.broad_query_count + parent_run.focused_query_count
        + parent_run.external_query_count
    )
    parent_run.query_count = parent_run.total_query_count
    parent_run.external_paper_ids = [paper.paper_id for paper in papers]
    parent_run.mechanism_bearing_paper_ids = sorted(mechanism_paper_ids)
    parent_run.mechanism_count = len(mechanisms)
    parent_run.alignment_count = len(accepted)
    parent_run.source_stage_result_count = (
        len(parent_run.source_results) + len(retrieval_run.source_results)
    )
    parent_run.source_failures.update({
        f"external:{source}": message
        for source, message in retrieval_run.source_failures.items()
    })
    parent_run.selected_direction_id = direction.direction_id
    parent_run.selected_gap_id = gap.gap_id
    parent_run.stage_records["external_discovery"] = {
        "parent_run_id": parent_run.run_id,
        "selected_direction_id": direction.direction_id,
        "selected_gap_id": gap.gap_id,
        "query_profile_version": parent_run.query_profile_version,
        "translation_profile_version": parent_run.translation_profile_version,
        "requested_mode": requested_mode,
        "actual_mode": retrieval_run.actual_search_mode,
        "queries_by_domain": queries_by_domain,
        "paper_ids": parent_run.external_paper_ids,
        "mechanism_bearing_paper_ids": parent_run.mechanism_bearing_paper_ids,
        "source_results": [item.to_dict() for item in retrieval_run.source_results],
        "mechanism_count": len(mechanisms),
        "alignment_count": len(accepted),
    }
    domain_stage = _stage(
        parent_run, "external_domain_selection", len(selections),
        len(selected_domains), len(selected_domains),
        len(selections) - len(selected_domains), "controlled_domain_profiles",
    )
    for stage in retrieval_run.stages:
        stage.parent_run_id = parent_run.run_id
        stage.stage_id = f"{parent_run.run_id}:external_retrieval"
    mechanism_stage = _stage(
        parent_run, "mechanism_extraction", len(papers), len(mechanisms),
        len(mechanisms), len(rejected_mechanisms), "typed_deterministic_extractor",
        warnings=warnings, errors=[item for item in errors if "mechanism" in item.lower()],
    )
    alignment_stage = _stage(
        parent_run, "structural_alignment", len(mechanisms), len(alignments),
        len(accepted), len(alignments) - len(accepted),
        "deterministic_structural_matcher",
        errors=[item for item in errors if "alignment" in item.lower()],
    )
    parent_run.stages = [
        stage for stage in parent_run.stages if stage.stage_name not in {
            "external_domain_selection", "external_retrieval",
            "mechanism_extraction", "structural_alignment",
        }
    ]
    parent_run.stages.extend([
        domain_stage, *retrieval_run.stages, mechanism_stage, alignment_stage,
    ])
    return ExternalDiscoveryResult(
        parent_run.run_id, direction.direction_id, gap.gap_id, signature,
        selections, queries_by_domain, [], papers, retrieval_run, mechanisms,
        rejected_mechanisms, alignments, accepted,
        {
            "completed_stages": [
                "gap_translation", "domain_selection", "external_retrieval",
                "mechanism_extraction", "structural_alignment",
            ],
            "query_count": len(queries), "paper_count": len(papers),
            "mechanism_count": len(mechanisms),
            "accepted_alignment_count": len(accepted),
            "adaptive_stage_two_used": stage_two_used,
            "stage_one_query_count": (
                len(queries) - len(stage_two_pairs) if stage_two_used
                else len(queries)
            ),
            "stage_two_query_count": len(stage_two_pairs) if stage_two_used else 0,
            "search_policy": search_policy.to_dict(),
        }, warnings, errors,
    )
