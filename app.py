"""Thin Streamlit UI for the no-LLM purpose-driven discovery pipeline."""

from __future__ import annotations

import json
import csv
import io
from collections import Counter
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

import streamlit as st

from algorithm_library import load_algorithm_library
from app_settings import SETTINGS
from annotation_schema import (
    SentenceAnnotation, annotations_csv, annotations_jsonl, load_annotations,
)
from alignment import align
from config import DEFAULT_DB, FIXTURE_DIR
from coverage_analysis import coverage_matrix
from discovery_pipeline import StructuralDiscoveryResult, discover_structural_gaps
from direction_families import create_direction_families
from gap_mining import corpus_summary
from io_utils import experiment_to_markdown, records_to_csv, to_json
from mechanism_mining import cross_domain_only, extract_mechanisms
from models import Paper, PurposeContract
from paper_fetchers import (
    FetchDiagnostics,
    deduplicate_papers,
    fetch_papers_cached_detailed,
)
from portfolio import quality_diversity_portfolio
from query_generation import (
    detect_algorithm_bindings, generate_external_queries,
    generate_focused_algorithm_queries, generate_ml_queries,
    generate_problem_queries, normalize_cross_domain_problem,
    select_external_domains,
)
from research_runs import ResearchRun
from retrieval_service import retrieve_corpus
from research_memory import ResearchMemory
from search_engine import search_candidates
from signatures import load_mechanism_seeds
from trend_analysis import trend_indicators
from weak_supervision import GapLabel, label_sentence
from evaluation.benchmark_tasks import load_benchmark_tasks
from evaluation.report_generation import report_json, report_markdown
from evaluation.run_benchmark import run_offline_benchmark
from evaluation.schemas import HumanReview
from research_runs import utc_now

PAGES = [
    "1 · Goal setup", "2 · Latest ML/DL gap radar", "3 · Gap evidence",
    "4 · External mechanism search", "5 · Structural alignment",
    "6 · Research direction families", "7 · Candidate algorithms",
    "8 · Novelty and falsification", "9 · Minimal experiment",
    "10 · Research memory",
]


def load_fixture(name: str) -> list[Paper]:
    return [Paper(**item) for item in json.loads((FIXTURE_DIR / name).read_text())]


def offline_diagnostics(
    fixture_name: str,
    papers: list[Paper],
    queries: list[str],
    publication_window: tuple[int, int],
) -> FetchDiagnostics:
    """Describe an explicit fixture run with the same schema as live retrieval."""
    return FetchDiagnostics(
        search_mode="OFFLINE FIXTURE",
        sources_queried=[fixture_name],
        query_strings=queries,
        retrieval_timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        returned_by_source={fixture_name: len(papers)},
        number_before_deduplication=len(papers),
        number_after_deduplication=len(papers),
        publication_date_range=publication_window,
        source_failures={},
    )


def combine_diagnostics(
    runs: list[FetchDiagnostics],
    papers_after_deduplication: int,
    fallback_occurred: bool = False,
    fallback_reason: str = "",
) -> FetchDiagnostics:
    """Aggregate the domain-specific calls made by one external-search action."""
    modes = {run.search_mode for run in runs}
    mode = "LIVE" if "LIVE" in modes else "CACHE"
    counts: dict[str, int] = {}
    failures: dict[str, str] = {}
    for run in runs:
        for source, count in run.returned_by_source.items():
            counts[source] = counts.get(source, 0) + count
        failures.update(run.source_failures)
    return FetchDiagnostics(
        search_mode=mode,
        sources_queried=sorted({source for run in runs for source in run.sources_queried}),
        query_strings=[query for run in runs for query in run.query_strings],
        retrieval_timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        returned_by_source=counts,
        number_before_deduplication=sum(
            run.number_before_deduplication for run in runs
        ),
        number_after_deduplication=papers_after_deduplication,
        publication_date_range=runs[0].publication_date_range,
        source_failures=failures,
        fallback_occurred=fallback_occurred,
        fallback_reason=fallback_reason,
        cache_created_at=", ".join(
            run.cache_created_at for run in runs if run.cache_created_at
        ),
    )


def render_search_diagnostics(
    diagnostics: FetchDiagnostics | None, heading: str = "Search provenance"
) -> None:
    """Render enough provenance to distinguish live, cached, and fixture runs."""
    if diagnostics is None:
        return
    st.subheader(heading)
    mode_col, dedup_col, range_col = st.columns(3)
    mode_col.metric("Search mode", diagnostics.search_mode)
    dedup_col.metric(
        "Papers",
        diagnostics.number_after_deduplication,
        f"{diagnostics.number_before_deduplication} before deduplication",
    )
    range_col.metric(
        "Publication range",
        f"{diagnostics.publication_date_range[0]}–{diagnostics.publication_date_range[1]}",
    )
    st.caption(f"Retrieval timestamp (UTC): {diagnostics.retrieval_timestamp}")
    if diagnostics.cache_created_at:
        st.caption(
            f"Cache created (UTC): {diagnostics.cache_created_at} · "
            f"TTL: {diagnostics.cache_lifetime_seconds} seconds"
        )
    st.write("Sources queried:", ", ".join(diagnostics.sources_queried))
    st.dataframe(
        [
            {"source": source, "returned": count}
            for source, count in diagnostics.returned_by_source.items()
        ],
        use_container_width=True,
        hide_index=True,
    )
    with st.expander("Query strings", expanded=True):
        for query in diagnostics.query_strings:
            st.code(query)
    st.write("Fallback occurred:", "Yes" if diagnostics.fallback_occurred else "No")
    if diagnostics.fallback_reason:
        st.warning(diagnostics.fallback_reason)
    if diagnostics.source_failures:
        st.error("One or more sources failed; partial results remain available.")
        st.json(diagnostics.source_failures)
    else:
        st.success("Source failures: none")


def engine_state_defaults(settings: object) -> dict[str, object]:
    """Normalize requested mode, including legacy objects retained by hot reload."""
    warnings = list(getattr(settings, "configuration_warnings", ()))
    requested = getattr(settings, "gap_engine_mode", None)
    if requested is None:
        requested = getattr(
            settings, "engine_mode",
            getattr(settings, "requested_mode", "lightweight"),
        )
        warnings.append(
            "A legacy settings object was detected during reload; "
            "normalized it to the canonical gap_engine_mode schema."
        )
    requested = str(requested).strip().casefold()
    if requested not in {"lightweight", "enhanced", "full"}:
        warnings.append(
            f"Invalid requested engine mode {requested!r}; using lightweight."
        )
        requested = "lightweight"
    return {
        "requested_mode": requested,
        "active_mode": "lightweight",
        "model_failures": [],
        "configuration_warnings": warnings,
    }


def initialize_state() -> None:
    """Initialize all persistent domain and run-state keys in one place."""
    defaults = {
        "purpose": None, "ml_papers": [], "gaps": [], "selected_gap": None,
        "external_papers": [], "mechanisms": [], "rejected_mechanisms": [],
        "alignments": [], "candidate_portfolio": [], "direction_families": [],
        "candidate_run_diagnostics": None, "fetch_failures": {},
        "external_queries": {}, "seed": 42, "ml_search_diagnostics": None,
        "external_search_diagnostics": None,
        "coverage_records": [], "coverage_gaps": [], "assumption_mismatches": [],
        "contradictory_gaps": [], "research_clusters": [],
        "retrieval_scores": [],
        "known_solution_results": {},
        "current_research_run": None, "current_external_run": None,
        "current_ml_corpus": [], "current_gap_results": [],
        "selected_gap_id": "", "algorithm_bindings": [],
        "problem_query_audit": None, "focused_query_audit": None,
        "domain_selections": [], "cross_domain_signature": None,
        "quality_evaluation_report": None,
        "engine_diagnostics": engine_state_defaults(SETTINGS),
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def apply_discovery_result(result: StructuralDiscoveryResult) -> None:
    """Publish one canonical pipeline result to Streamlit session state."""
    st.session_state.ml_papers = result.papers
    st.session_state.gaps = result.gaps
    st.session_state.current_ml_corpus = result.papers
    st.session_state.current_gap_results = result.gaps
    st.session_state.retrieval_scores = result.retrieval_scores
    st.session_state.coverage_records = result.coverage_records
    st.session_state.coverage_gaps = result.coverage_gaps
    st.session_state.assumption_mismatches = result.assumption_mismatches
    st.session_state.contradictory_gaps = result.contradictions
    st.session_state.research_clusters = result.research_clusters
    st.session_state.known_solution_results = result.known_solution_results
    configuration_warnings = st.session_state.engine_diagnostics.get(
        "configuration_warnings", []
    )
    st.session_state.engine_diagnostics = {
        **result.diagnostics,
        "configuration_warnings": configuration_warnings,
    }


def invalidate_downstream_for_purpose() -> None:
    """Prevent a new purpose from displaying results from an older run."""
    for key, empty in {
        "selected_gap": None, "selected_gap_id": "", "external_papers": [],
        "mechanisms": [], "rejected_mechanisms": [], "alignments": [],
        "direction_families": [], "candidate_portfolio": [],
        "external_search_diagnostics": None, "current_external_run": None,
    }.items():
        st.session_state[key] = empty


def invalidate_downstream_for_gap() -> None:
    for key in (
        "external_papers", "mechanisms", "rejected_mechanisms", "alignments",
        "direction_families", "candidate_portfolio",
    ):
        st.session_state[key] = []
    st.session_state.external_search_diagnostics = None
    st.session_state.current_external_run = None


def render_research_run(run: ResearchRun | None, heading: str) -> None:
    """Render one canonical provenance record without reconstructing mode."""
    if run is None:
        return
    st.subheader(heading)
    if run.actual_search_mode == "OFFLINE_FIXTURE":
        st.warning(
            "OFFLINE DEMONSTRATION — bundled test papers are being used. "
            "This is not a current literature review."
        )
    elif run.actual_search_mode == "FAILED":
        st.error("Live retrieval failed. No usable literature corpus was produced.")
    else:
        st.success(f"{run.actual_search_mode} LITERATURE RUN")
    st.write({
        "Run ID": run.run_id,
        "Requested mode": run.requested_search_mode,
        "Actual mode": run.actual_search_mode,
        "Retrieval origin": sorted({
            origin for source in run.source_results
            for origin in [source.source_type]
        }),
        "Sources attempted": run.sources_attempted,
        "Live request attempted": run.live_request_attempted,
        "Live request succeeded": run.live_request_succeeded,
        "Cache used": run.cache_used,
        "Cache age seconds": round(run.cache_age_seconds, 1),
        "Cache TTL seconds": run.cache_ttl_seconds,
        "Fallback occurred": run.fallback_occurred,
        "Fallback reason": run.fallback_reason or "none",
        "Requested publication range": (
            f"{run.publication_window_requested[0]}–"
            f"{run.publication_window_requested[1]}"
        ),
        "Actual returned publication range": (
            f"{run.actual_publication_year_min}–{run.actual_publication_year_max}"
            if run.actual_publication_year_min else "no papers"
        ),
        "Retrieved": run.raw_paper_count,
        "After deduplication": run.deduplicated_paper_count,
        "Retrieved at UTC": run.created_at_utc,
        "Fixture paths": run.fixture_paths,
        "Fixture version": run.fixture_version or "not applicable",
    })
    st.dataframe([{
        "source": item.source, "origin": item.source_type,
        "attempted": bool(item.request_count or item.cache_hits),
        "succeeded": item.success_count > 0 or item.cache_hits > 0,
        "request count": item.request_count,
        "raw returned": item.raw_returned_count,
        "unique returned": item.unique_returned_count,
        "cache hits": item.cache_hits,
        "failures": item.failure_count,
        "API status": item.api_status,
        "failure messages": "; ".join(item.failure_messages),
        "duration": item.duration_seconds,
    } for item in run.source_results], use_container_width=True, hide_index=True)
    if run.source_failures:
        st.error("Source failures")
        st.json(run.source_failures)
    with st.expander("Query strings", expanded=True):
        for query in [*run.ml_queries, *run.focused_algorithm_queries]:
            st.code(query)


def navigate_to(page: str) -> None:
    """Update the sidebar widget through a pre-rerun button callback."""
    st.session_state["_workflow_page"] = page


def choose_search_mode(mode: str, force_fresh: bool = False) -> None:
    """Return to Step 1 with an explicit retrieval choice."""
    st.session_state["_purpose_search_mode"] = mode
    st.session_state["_purpose_force_fresh"] = force_fresh
    st.session_state["_workflow_page"] = PAGES[0]


def candidate_prerequisites() -> dict[str, tuple[bool, str]]:
    """Return Page 7 requirements and actionable explanations."""
    purpose = st.session_state.purpose
    gap = st.session_state.selected_gap
    mechanisms = st.session_state.mechanisms
    accepted = [
        result for result in st.session_state.alignments if not result.rejected
    ]
    library = load_algorithm_library()
    compatible_algorithm = False
    if gap:
        compatible_algorithm = (
            gap.affected_algorithm.casefold() in library
            or any(
                record.family == gap.affected_algorithm_family
                or gap.task in record.tasks
                for record in library.values()
            )
        )
    return {
        "Purpose contract": (
            purpose is not None,
            "Complete Step 1: Goal setup",
        ),
        "Selected gap": (
            gap is not None,
            "Complete Step 2: Latest ML/DL gap radar",
        ),
        "External mechanisms": (
            bool(mechanisms),
            "Complete Step 4: External mechanism search",
        ),
        "Accepted structural alignments": (
            bool(accepted),
            "Complete Step 5: Structural alignment",
        ),
        "Direction families ready/generated": (
            bool(st.session_state.direction_families) or bool(accepted),
            "Complete Step 6: Research direction families",
        ),
        "Compatible base algorithm": (
            compatible_algorithm,
            "Select a gap linked to a supported algorithm",
        ),
        "Primary metric": (
            bool(purpose and purpose.primary_metric),
            "Define a primary metric in Step 1",
        ),
        "Inference information": (
            bool(purpose and purpose.available_inference_information),
            "Define inference-time information in Step 1",
        ),
    }


def summarize_rejections(
    candidates: list[object], rejected_paths: list[dict[str, object]]
) -> dict[str, object]:
    """Aggregate search rejection traces into stable user-facing categories."""
    categories = Counter()
    mappings = {
        "purpose": "missing purpose fit",
        "mechanism-slot": "mechanism-slot incompatibility",
        "cross-disciplinarity": "false cross-disciplinarity",
        "inference": "unavailable inference information",
        "operator-slot": "operator incompatibility",
        "alignment": "weak structural alignment",
        "duplicate": "duplicate-method penalty",
        "resource": "resource-budget violation",
        "weakness": "algorithm-weakness mismatch",
    }
    for path in rejected_paths:
        for reason in path.get("reasons", []):
            normalized = str(reason).casefold()
            category = next(
                (label for cue, label in mappings.items() if cue in normalized),
                "other hard rejection reasons",
            )
            categories[category] += 1
    families = {candidate.base_algorithm_family for candidate in candidates}
    return {
        "status": "success" if candidates else "empty",
        "sampled_paths": len(candidates) + len(rejected_paths),
        "surviving_candidates": len(candidates),
        "algorithm_families": len(families),
        "rejections": dict(categories),
        "rejected_paths": rejected_paths,
        "failed_stage": "",
        "error": "",
    }


def sidebar() -> str:
    st.sidebar.title("目的驱动 · Discovery Engine")
    st.sidebar.caption("No LLMs. Evidence → purpose → mechanism → experiment.")
    with st.sidebar.expander("Advanced engine settings"):
        st.write({
            "Engine mode": SETTINGS.gap_engine_mode,
            "SPECTER2 enabled": SETTINGS.enable_specter2,
            "SciBERT enabled": SETTINGS.enable_scibert,
            "SciBERT checkpoint": SETTINGS.scibert_checkpoint or "not configured",
            "Device": SETTINGS.transformer_device,
            "Batch size": SETTINGS.transformer_batch_size,
            "Paper limit": SETTINGS.transformer_max_papers,
            "Sentence limit": SETTINGS.transformer_max_sentences,
            "Clustering threshold": SETTINGS.clustering_threshold,
            "Semantic dedup threshold": SETTINGS.semantic_deduplication_threshold,
            "Minimum coverage support": SETTINGS.minimum_coverage_support,
            "Maximum unknown ratio": SETTINGS.maximum_unknown_ratio,
        })
        st.caption(
            "Expensive modes are controlled by environment variables and "
            "take effect after restart. Lightweight is the deployment-safe default."
        )
    for warning in st.session_state.engine_diagnostics.get(
        "configuration_warnings", []
    ):
        st.sidebar.warning(warning)
    with st.sidebar.expander("Research Tools"):
        st.checkbox(
            "Quality Evaluation", key="_show_quality_evaluation",
            help="Optional benchmark and human-review tools.",
        )
    return st.sidebar.radio("Workflow", PAGES, key="_workflow_page")


def quality_evaluation_panel() -> None:
    """Optional benchmark and human-review surface outside the ten-step flow."""
    st.divider()
    st.header("Quality Evaluation")
    st.warning(
        "Automated quality metrics are meaningful only against reviewed "
        "annotations. Synthetic offline labels are CI fixtures, not ground truth."
    )
    tasks = load_benchmark_tasks()
    task_id = st.selectbox(
        "Benchmark task", list(tasks), key="_quality_task",
        format_func=lambda key: tasks[key].title,
    )
    if st.button("Run deterministic offline evaluation", key="_quality_run"):
        with st.spinner("Evaluating production pipeline…"):
            st.session_state.quality_evaluation_report = run_offline_benchmark(
                tasks[task_id]
            )
    report = st.session_state.quality_evaluation_report
    if report:
        st.subheader("Retrieval review")
        st.json(report.retrieval_metrics)
        st.subheader("Query contribution")
        st.dataframe(
            [asdict(item) for item in report.query_contributions],
            use_container_width=True,
        )
        review_tabs = st.tabs([
            "Gap review", "Coverage and mismatch", "Bindings and solutions",
            "External and mechanisms", "Alignments and candidates",
        ])
        review_tabs[0].dataframe([asdict(item) for item in report.gap_audits])
        review_tabs[1].dataframe([
            asdict(item) for item in [
                *report.coverage_audits, *report.mismatch_audits
            ]
        ])
        review_tabs[2].dataframe([
            asdict(item) for item in [
                *report.binding_audits, *report.known_solution_audits
            ]
        ])
        review_tabs[3].dataframe([
            asdict(item) for item in [
                *report.external_query_audits, *report.mechanism_audits
            ]
        ])
        review_tabs[4].dataframe([
            asdict(item) for item in [
                *report.alignment_audits, *report.candidate_audits
            ]
        ])
        st.subheader("Stage funnel")
        st.write({"counts": asdict(report.funnel), "conversion rates": report.funnel.rates()})
        st.subheader("Error distribution and dominant bottleneck")
        st.write(report.error_counts)
        st.info(f"Dominant bottleneck: {report.dominant_bottleneck}")
        st.subheader("Before/after comparison")
        st.json(report.before_after)
        st.download_button(
            "Export evaluation JSON", report_json(report),
            f"{report.task_id}-evaluation.json", key="_quality_export_json",
        )
        st.download_button(
            "Export evaluation Markdown", report_markdown(report),
            f"{report.task_id}-evaluation.md", key="_quality_export_md",
        )
    with st.expander("Human review annotation"):
        item_id = st.text_input("Item ID", key="_quality_review_item")
        item_type = st.selectbox(
            "Item type", [
                "paper", "gap", "coverage_gap", "assumption_mismatch",
                "algorithm_binding", "external_query", "mechanism",
                "alignment", "candidate",
            ], key="_quality_review_type",
        )
        label = st.text_input("Review label", key="_quality_review_label")
        reviewer = st.text_input("Reviewer", key="_quality_reviewer")
        notes = st.text_area("Notes and uncertainty", key="_quality_notes")
        uncertain = st.checkbox("Uncertain", key="_quality_uncertain")
        if st.button("Save review", key="_quality_save_review"):
            run = st.session_state.current_research_run
            review = HumanReview(
                run.run_id if run else "evaluation-only", item_id, item_type,
                task_id, label, {}, reviewer or "anonymous", utc_now(), notes,
                "quality-evaluation-v1", uncertain,
            )
            memory = ResearchMemory(DEFAULT_DB)
            memory.save_evaluation_review(review)
            memory.close()
            st.success("Review saved to Research Memory.")
        memory = ResearchMemory(DEFAULT_DB)
        reviews = memory.evaluation_reviews()
        memory.close()
        if reviews:
            rows = [item["payload"] for item in reviews]
            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
            st.download_button(
                "Export reviews JSONL",
                "\n".join(json.dumps(row, default=str) for row in rows),
                "quality-reviews.jsonl", key="_quality_reviews_jsonl",
            )
            st.download_button(
                "Export reviews CSV", buffer.getvalue(),
                "quality-reviews.csv", key="_quality_reviews_csv",
            )
            review_markdown = "\n\n".join(
                f"## {row['item_type']}: {row['item_id']}\n\n"
                f"- Label: {row['label']}\n- Reviewer: {row['reviewer']}\n"
                f"- Uncertain: {row['uncertain']}\n- Notes: {row['notes']}"
                for row in rows
            )
            st.download_button(
                "Export reviews Markdown", review_markdown,
                "quality-reviews.md", key="_quality_reviews_md",
            )


def annotation_tool() -> None:
    """Optional bounded human review UI; never required by the main workflow."""
    path = FIXTURE_DIR.parent / "annotations" / "gap_sentences.jsonl"
    records = load_annotations(path, SETTINGS.max_annotation_rows)
    if not records:
        st.info("No seed annotations are available.")
        return
    labels = {
        f"{record.sentence_id} · {record.target_sentence[:80]}": record
        for record in records
    }
    selected = labels[st.selectbox(
        "Annotation sentence", labels, key="_annotation_sentence"
    )]
    st.write({
        "Section": selected.section, "Previous": selected.previous_sentence,
        "Target": selected.target_sentence, "Next": selected.next_sentence,
    })
    weak = label_sentence(selected.target_sentence, selected.section)
    st.caption(f"Weak labels: {', '.join(weak.labels)} · confidence {weak.confidence}")
    chosen = st.multiselect(
        "Human labels", [label.value for label in GapLabel],
        default=selected.labels, key="_annotation_labels",
    )
    uncertain = st.checkbox("Mark uncertain", key="_annotation_uncertain")
    notes = st.text_input("Annotation notes", key="_annotation_notes")
    if st.button("Save annotation to research memory", key="_annotation_save"):
        corrected = SentenceAnnotation(
            **{**asdict(selected), "labels": chosen,
               "annotator": "streamlit-human",
               "adjudication_status": "uncertain" if uncertain else "reviewed",
               "notes": notes}
        )
        memory = ResearchMemory(DEFAULT_DB)
        memory.save_structural(
            "sentence_annotation", corrected.sentence_id, corrected,
            SETTINGS.gap_engine_mode, "annotation-v1",
        )
        memory.close()
        st.success("Annotation saved locally.")
    st.download_button(
        "Export seed annotations JSONL", annotations_jsonl(records),
        "gap-sentences.jsonl", key="_annotation_export_jsonl",
    )
    st.download_button(
        "Export seed annotations CSV", annotations_csv(records),
        "gap-sentences.csv", key="_annotation_export_csv",
    )


def goal_page() -> None:
    st.title("Purpose contract")
    mode = st.radio(
        "Mode", ["User-defined purpose", "Gap radar"], key="_purpose_mode"
    )
    with st.form("_purpose_form"):
        col1, col2 = st.columns(2)
        task = col1.text_input("Task", "online learning", key="_purpose_task")
        data_type = col2.text_input(
            "Data type", "tabular streams", key="_purpose_data_type"
        )
        use_case = col1.text_input(
            "Application", "adaptive decision support", key="_purpose_use_case"
        )
        failure = col2.text_input(
            "Current failure", "recurring concept drift", key="_purpose_failure"
        )
        improvement = col1.text_input(
            "Desired improvement",
            "reduce post-shift recovery time",
            key="_purpose_improvement",
        )
        metric = col2.text_input(
            "Primary metric", "average online accuracy", key="_purpose_metric"
        )
        secondary = col1.text_input(
            "Secondary metrics",
            "recovery time, memory use",
            key="_purpose_secondary",
        )
        preserve = col2.text_input(
            "Must not degrade",
            "stable-regime accuracy, calibration",
            key="_purpose_preserve",
        )
        training = col1.text_input(
            "Training information",
            "features, delayed outcome feedback",
            key="_purpose_training",
        )
        inference = col2.text_input(
            "Inference information",
            "input features, prediction residual, regime similarity",
            key="_purpose_inference",
        )
        algorithm = st.selectbox(
            "Algorithm restriction",
            ["Evidence-based detection"] + sorted(load_algorithm_library()),
            key="_purpose_algorithm",
            help="Leave evidence-based detection selected to avoid premature binding.",
        )
        risk = col1.selectbox(
            "Risk tolerance",
            ["low", "medium", "high"],
            index=1,
            key="_purpose_risk",
        )
        scale = col2.selectbox(
            "Combination scale",
            ["small", "medium", "large"],
            key="_purpose_scale",
        )
        years = st.slider(
            "Publication window",
            2018,
            date.today().year,
            (2022, date.today().year),
            key="_purpose_years",
        )
        search_mode = st.radio(
            "Search data source",
            ["Live scholarly APIs", "Cached live results",
             "Offline demonstration fixtures"],
            key="_purpose_search_mode",
        )
        force_fresh = st.checkbox(
            "Force fresh live search",
            value=False,
            key="_purpose_force_fresh",
        )
        allow_cache = st.checkbox("Allow cache", value=True, key="_purpose_allow_cache")
        allow_offline_fallback = st.checkbox(
            "Allow offline fallback", value=False,
            key="_purpose_allow_offline_fallback",
        )
        openalex_enabled = col1.checkbox(
            "OpenAlex enabled", value=True, key="_purpose_openalex"
        )
        arxiv_enabled = col2.checkbox(
            "arXiv enabled", value=True, key="_purpose_arxiv"
        )
        maximum_per_query = col1.number_input(
            "Maximum papers per query", 1, 50, 8, key="_purpose_max_per_query"
        )
        maximum_total = col2.number_input(
            "Maximum total papers", 5, 200, 80, key="_purpose_max_total"
        )
        submitted = st.form_submit_button(
            "Discover ML/DL gaps", type="primary"
        )
    if submitted:
        previous_purpose = st.session_state.purpose
        previous_run = st.session_state.current_research_run
        same_purpose = bool(
            previous_purpose
            and previous_purpose.task == task
            and previous_purpose.data_type == data_type
            and previous_purpose.use_case == use_case
            and previous_purpose.current_failure == failure
            and previous_purpose.desired_improvement == improvement
            and previous_purpose.primary_metric == metric
            and previous_purpose.publication_window == years
        )
        restriction = (
            load_algorithm_library()[algorithm]
            if algorithm != "Evidence-based detection" else None
        )
        purpose = PurposeContract(
            purpose_id=(
                previous_purpose.purpose_id if same_purpose
                else f"purpose:{uuid4().hex[:10]}"
            ),
            mode="user" if mode.startswith("User") else "gap_radar",
            use_case=use_case, task=task, data_type=data_type, current_failure=failure,
            desired_improvement=improvement, primary_metric=metric,
            secondary_metrics=[x.strip() for x in secondary.split(",") if x.strip()],
            must_not_degrade=[x.strip() for x in preserve.split(",") if x.strip()],
            available_training_information=[x.strip() for x in training.split(",") if x.strip()],
            available_inference_information=[x.strip() for x in inference.split(",") if x.strip()],
            allowed_algorithm_families=(
                [restriction.family] if restriction else []
            ), risk_tolerance=risk,
            preferred_candidate_scale=scale, publication_window=years,
        )
        if not same_purpose:
            invalidate_downstream_for_purpose()
        st.session_state.purpose = purpose
        broad_queries, broad_audit = generate_problem_queries(purpose)
        requested_mode = {
            "Live scholarly APIs": "LIVE",
            "Cached live results": "CACHE",
            "Offline demonstration fixtures": "OFFLINE_FIXTURE",
        }[search_mode]
        sources = [
            source for source, enabled in (
                ("openalex", openalex_enabled), ("arxiv", arxiv_enabled)
            ) if enabled
        ]
        papers, run = retrieve_corpus(
            purpose, broad_queries, requested_mode=requested_mode,
            sources=sources, maximum_per_query=int(maximum_per_query),
            maximum_total=int(maximum_total), allow_cache=allow_cache,
            allow_offline_fallback=allow_offline_fallback,
            force_fresh=force_fresh, fixture_loader=lambda: load_fixture(
                "ml_papers.json"
            ), fixture_path="data/offline_fixtures/ml_papers.json",
        )
        if (
            force_fresh and run.actual_search_mode == "FAILED"
            and same_purpose and previous_run
            and previous_run.actual_search_mode != "FAILED"
        ):
            st.session_state.purpose = previous_purpose
            st.error(
                "Fresh retrieval failed. The previous successful research run "
                "was preserved."
            )
            render_research_run(previous_run, "Preserved ML/DL paper search")
            return
        bindings = detect_algorithm_bindings(papers, purpose)
        focused_queries, focused_audit = generate_focused_algorithm_queries(
            purpose, bindings, SETTINGS.algorithm_binding_confidence_threshold
        )
        run.focused_algorithm_queries = focused_queries
        if focused_queries and requested_mode != "OFFLINE_FIXTURE" and papers:
            focused_papers, focused_run = retrieve_corpus(
                purpose, focused_queries, requested_mode=requested_mode,
                sources=sources, maximum_per_query=int(maximum_per_query),
                maximum_total=int(maximum_total), allow_cache=allow_cache,
                allow_offline_fallback=False, force_fresh=force_fresh,
            )
            papers = deduplicate_papers([*papers, *focused_papers])[:int(maximum_total)]
            run.source_results.extend(focused_run.source_results)
            run.source_failures.update(focused_run.source_failures)
            run.raw_paper_count += focused_run.raw_paper_count
            run.finalize_from_papers(papers)
        binding = (
            bindings[0] if bindings and bindings[0].confidence >=
            SETTINGS.algorithm_binding_confidence_threshold else None
        )
        discovery = discover_structural_gaps(
            papers, purpose,
            restriction.name if restriction else (
                binding.algorithm if binding else "Unspecified"
            ),
        )
        for gap in discovery.gaps:
            gap.research_run_id = run.run_id
        apply_discovery_result(discovery)
        run.structural_gap_count = len(discovery.gaps)
        st.session_state.current_research_run = run
        st.session_state.algorithm_bindings = bindings
        st.session_state.problem_query_audit = broad_audit
        st.session_state.focused_query_audit = focused_audit
        st.session_state.ml_search_diagnostics = None
        st.session_state.fetch_failures = run.source_failures
        st.success(
            f"Mined {len(discovery.gaps)} gap records from "
            f"{len(discovery.papers)} papers."
        )
    render_research_run(
        st.session_state.current_research_run, "Latest ML/DL paper search"
    )


def gap_radar_page() -> None:
    st.title("Latest ML/DL gap radar")
    run = st.session_state.current_research_run
    render_research_run(run, "Evidence provenance")
    action_columns = st.columns(4)
    action_columns[0].button(
        "Run live search", key="_radar_live",
        on_click=choose_search_mode, args=("Live scholarly APIs", False),
    )
    action_columns[1].button(
        "Force fresh search", key="_radar_fresh",
        on_click=choose_search_mode, args=("Live scholarly APIs", True),
    )
    action_columns[2].button(
        "Use cached live corpus", key="_radar_cache",
        on_click=choose_search_mode, args=("Cached live results", False),
    )
    action_columns[3].button(
        "Load offline demonstration", key="_radar_fixture",
        on_click=choose_search_mode,
        args=("Offline demonstration fixtures", False),
    )
    st.info(
        f"Gap engine mode: {st.session_state.engine_diagnostics['active_mode'].upper()} · "
        f"requested: {st.session_state.engine_diagnostics['requested_mode'].upper()}"
    )
    gaps = st.session_state.gaps
    if not gaps:
        st.info("Create a purpose contract and discover gaps first.")
        return
    if run and run.actual_search_mode != "OFFLINE_FIXTURE" and len(
        st.session_state.ml_papers
    ) < SETTINGS.minimum_live_corpus_size:
        st.warning(
            "Insufficient live literature coverage for reliable structural gap "
            f"detection. The current corpus contains {len(st.session_state.ml_papers)} "
            "papers. Explicit gaps remain exploratory; coverage and trend claims "
            "must be treated as provisional."
        )
    if st.session_state.algorithm_bindings:
        st.subheader("Evidence-based algorithm binding")
        st.dataframe([
            asdict(item) for item in st.session_state.algorithm_bindings
        ], use_container_width=True)
    st.json(corpus_summary(st.session_state.ml_papers, gaps))
    diagnostics = st.session_state.engine_diagnostics
    st.write({
        "retrieval method": diagnostics.get("retrieval_method", "SPARSE ONLY"),
        "embedding model": diagnostics.get("embedding_model", "none"),
        "sparse reranking": diagnostics.get("sparse_reranking", False),
        "dense reranking": diagnostics.get("dense_reranking", False),
        "model failures": diagnostics.get("model_failures", []),
        "papers processed": diagnostics.get("papers_processed", 0),
        "sentences processed": diagnostics.get("sentences_processed", 0),
        "paper-processing seconds": diagnostics.get("paper_processing_seconds", 0),
        "estimated memory tier": diagnostics.get("estimated_memory_tier", "low"),
        "truncated by resource limit": diagnostics.get("papers_truncated", False),
    })
    with st.expander("Retrieval score components"):
        st.dataframe([
            asdict(score) for score in st.session_state.retrieval_scores
        ], use_container_width=True)
    gap_types = sorted({
        gap.structural_gap_subtype or gap.gap_type for gap in gaps
    })
    selected_types = st.multiselect(
        "Gap type filters", gap_types, default=gap_types, key="_gap_type_filters"
    )
    filtered = [
        gap for gap in gaps
        if (gap.structural_gap_subtype or gap.gap_type) in selected_types
    ]
    labels = {
        f"{g.title} · {g.gap_type} · confidence {g.confidence_score:.2f} · evidence {g.evidence_count}": g
        for g in sorted(filtered, key=lambda x: (x.confidence_score, x.evidence_count), reverse=True)
    }
    if not labels:
        st.warning("No gaps match the selected filters.")
        return
    chosen = st.selectbox(
        "Select an evidence-backed gap", labels, key="_gap_radar_selection"
    )
    if st.button("Use selected gap", type="primary", key="_gap_radar_submit"):
        if st.session_state.selected_gap_id != labels[chosen].gap_id:
            invalidate_downstream_for_gap()
        st.session_state.selected_gap = labels[chosen]
        st.session_state.selected_gap_id = labels[chosen].gap_id
        if run:
            run.selected_gap_id = labels[chosen].gap_id
        st.success("Gap selected. Continue to evidence or external mechanism search.")
    st.dataframe([{
        "gap": g.title, "type": g.structural_gap_subtype or g.gap_type,
        "algorithm": g.affected_algorithm,
        "failure": g.failure_type, "evidence": g.evidence_count,
        "confidence": g.confidence_score, "testability": g.testability_score,
        "metadata completeness": g.metadata_completeness,
        "detection": g.detection_method,
    } for g in filtered], use_container_width=True)
    with st.expander("Coverage Matrix", expanded=False):
        records = st.session_state.coverage_records
        row = st.selectbox(
            "Row dimension", ["algorithm_family", "task", "data_type"],
            key="_coverage_row",
        )
        column = st.selectbox(
            "Column dimension",
            ["metric_categories", "distribution_conditions",
             "missingness_conditions", "evaluation_protocols"],
            key="_coverage_column",
        )
        normalized = st.checkbox(
            "Normalized view", key="_coverage_normalized"
        )
        matrix_rows = coverage_matrix(records, row, column, normalized) if records else []
        st.dataframe(matrix_rows, use_container_width=True)
        st.download_button(
            "Export coverage CSV", records_to_csv(matrix_rows),
            "coverage-matrix.csv", key="_coverage_export",
        )
        unknown = sum(
            record.algorithm_family == "UNKNOWN" for record in records
        )
        st.caption(
            f"Unknown algorithm-family records: {unknown}/{len(records)}"
            if records else "No coverage records."
        )
    with st.expander("Assumption Mismatch view"):
        st.dataframe([{
            "Assumption": item.assumption.assumption_statement,
            "Observed condition": item.observed_condition.condition_type,
            "Relation": item.contradiction_relation,
            "Failure consequence": item.expected_failure_mode,
            "Evidence": item.observed_condition.evidence_sentence,
            "Confidence": item.confidence,
        } for item in st.session_state.assumption_mismatches], use_container_width=True)
    with st.expander("Contradictory evidence view"):
        st.dataframe([{
            "Title": item.title, "Comparable fields": str(item.comparable_fields),
            "Support": ", ".join(item.supporting_paper_ids),
            "Conflict": ", ".join(item.conflicting_paper_ids),
            "Confidence": item.confidence,
        } for item in st.session_state.contradictory_gaps], use_container_width=True)
    with st.expander("Research Clusters"):
        st.dataframe([{
            "Cluster": cluster.cluster_id,
            "Title terms": ", ".join(cluster.label_terms),
            "Representative papers": ", ".join(cluster.representative_papers),
            "Paper count": len(cluster.paper_ids),
            "Year range": (
                f"{min(cluster.year_distribution)}–{max(cluster.year_distribution)}"
                if cluster.year_distribution else ""
            ),
            "Tasks": str(cluster.task_distribution),
            "Algorithms": str(cluster.algorithm_distribution),
            "Conditions": str(cluster.condition_distribution),
            "Metrics": str(cluster.metric_distribution),
            "Cohesion": cluster.cohesion,
        } for cluster in st.session_state.research_clusters], use_container_width=True)
    with st.expander("Research Tools · Sentence annotation"):
        annotation_tool()


def evidence_page() -> None:
    st.title("Gap evidence")
    gap = st.session_state.selected_gap
    if not gap:
        st.info("Select a gap in the radar.")
        return
    st.subheader(gap.title)
    st.write({
        "detection origin": gap.structural_gap_subtype or gap.gap_type,
        "task": gap.task, "current method": gap.current_method_pattern,
        "failure condition": gap.failure_type, "observable signal": gap.observable_failure_signal,
        "why it matters / response": gap.required_response, "assumptions": gap.unresolved_assumptions,
        "must preserve": gap.must_preserve,
        "missing dimension": gap.missing_dimension,
        "known mitigations": gap.known_mitigations,
        "known-solution status": (
            asdict(st.session_state.known_solution_results[gap.gap_id])
            if gap.gap_id in st.session_state.known_solution_results else {}
        ),
        "unresolved remainder": gap.unresolved_remainder,
        "field provenance": gap.field_provenance,
        "confidence decomposition": gap.evidence_strength_components,
        "comparison evidence": gap.comparison_evidence,
        "contradiction evidence": gap.contradiction_evidence,
        "missing evidence": [] if gap.evidence_count > 1 else ["independent corroboration"],
    })
    for sentence, section, paper_id in zip(
        gap.evidence_sentences, gap.evidence_sections, gap.evidence_paper_ids
    ):
        st.markdown(f"> {sentence}\n\nSection: `{section}` · Paper: `{paper_id}`")


def mechanism_page() -> None:
    st.title("External mechanism search")
    gap = st.session_state.selected_gap
    if not gap:
        st.info("Select a verified gap first.")
        return
    signature = normalize_cross_domain_problem(gap)
    selections = select_external_domains(
        signature, SETTINGS.maximum_external_domains
    )
    selected_domains = [item.domain for item in selections if item.selected]
    queries = generate_external_queries(gap, selected_domains)
    st.session_state.cross_domain_signature = signature
    st.session_state.domain_selections = selections
    st.session_state.external_queries = queries
    st.subheader("Normalized cross-domain problem signature")
    st.json(asdict(signature))
    st.subheader("Ranked external domains")
    st.dataframe([asdict(item) for item in selections], use_container_width=True)
    st.subheader("Discipline-native query translations")
    for domain, domain_queries in queries.items():
        with st.expander(domain, expanded=True):
            for query in domain_queries:
                st.code(query)
    st.caption(
        "Rejected raw query candidates: none. Queries are generated directly "
        "from controlled discipline profiles and still pass deterministic validation."
    )
    external_mode = st.radio(
        "External search data source",
        ["Live scholarly APIs", "Cached live results",
         "Offline demonstration fixtures"],
        key="_mechanism_search_mode",
    )
    force_fresh = st.checkbox(
        "Force fresh search (bypass local cache)",
        value=False,
        key="_mechanism_force_fresh",
        help="Applies only to live mode. API rate limits and retry delays remain active.",
    )
    if st.button(
        "Fetch and extract mechanisms", type="primary", key="_mechanism_fetch"
    ):
        requested_mode = {
            "Live scholarly APIs": "LIVE",
            "Cached live results": "CACHE",
            "Offline demonstration fixtures": "OFFLINE_FIXTURE",
        }[external_mode]
        indexed_external_queries = [
            (domain, query) for domain, domain_queries in queries.items()
            for query in domain_queries
        ]
        external_query_list = [query for _, query in indexed_external_queries]
        papers, external_run = retrieve_corpus(
            st.session_state.purpose, external_query_list,
            requested_mode=requested_mode,
            sources=["openalex", "arxiv"], maximum_per_query=6,
            maximum_total=60, allow_cache=True,
            allow_offline_fallback=False, force_fresh=force_fresh,
            fixture_loader=lambda: load_fixture("external_papers.json"),
            fixture_path="data/offline_fixtures/external_papers.json",
        )
        external_run.external_queries_by_domain = queries
        current_run = st.session_state.current_research_run
        if current_run:
            external_run.parent_run_id = current_run.run_id
            external_run.run_id = current_run.run_id
            current_run.external_queries_by_domain = queries
            current_run.stage_records["external_retrieval"] = {
                "actual_search_mode": external_run.actual_search_mode,
                "paper_count": len(papers),
                "sources": external_run.sources_attempted,
            }
        for paper in papers:
            indices = [
                int(query_id.split(":", 1)[1])
                for query_id in paper.query_ids if query_id.startswith("q:")
            ]
            if indices:
                paper.domain = indexed_external_queries[indices[0]][0]
        mechanisms, rejected = extract_mechanisms(papers)
        mechanism_fallback = not mechanisms
        if not mechanisms:
            mechanisms = load_mechanism_seeds()
        for mechanism in mechanisms:
            mechanism.research_run_id = external_run.run_id
        external_run.mechanism_count = len(mechanisms)
        if mechanism_fallback:
            external_run.warnings.append(
                "No mechanism was extracted; curated mechanism seeds were used."
            )
        st.session_state.external_papers = papers
        st.session_state.current_external_run = external_run
        st.session_state.external_search_diagnostics = None
        st.session_state.mechanisms = cross_domain_only(mechanisms)
        st.session_state.rejected_mechanisms = rejected
        st.session_state.fetch_failures.update(external_run.source_failures)
    render_research_run(
        st.session_state.current_external_run,
        "Latest external paper search",
    )
    st.dataframe([{
        "mechanism": m.name, "domain": m.source_domain,
        "signal": m.observed_signal, "response": m.response_rule,
        "evidence": m.evidence_count, "confidence": m.confidence_score,
    } for m in st.session_state.mechanisms], use_container_width=True)
    st.caption(f"Rejected invalid phrases: {len(st.session_state.rejected_mechanisms)}")
    with st.expander("Rejected extraction details"):
        st.json(st.session_state.rejected_mechanisms)


def alignment_page() -> None:
    st.title("Structural alignment")
    gap, mechanisms = st.session_state.selected_gap, st.session_state.mechanisms
    if not gap or not mechanisms:
        st.info("Select a gap and extract mechanisms first.")
        return
    results = [align(gap, mechanism, st.session_state.purpose) for mechanism in mechanisms]
    current_run = st.session_state.current_research_run
    for result in results:
        result.research_run_id = current_run.run_id if current_run else ""
    st.session_state.alignments = results
    st.dataframe([{
        "mechanism": result.mechanism_id, "score": round(result.score, 2),
        "slot": ", ".join(result.matched_slots), "rejected": result.rejected,
        "conflicts": "; ".join(result.conflicts),
        "missing": "; ".join(result.missing_information),
    } for result in results], use_container_width=True)
    for result in results:
        with st.expander(result.mechanism_id):
            st.json(asdict(result))


def generate_candidates() -> dict[str, object]:
    """Generate and persist one canonical candidate portfolio plus diagnostics."""
    checks = candidate_prerequisites()
    blocking = [
        name for name, (ready, _) in checks.items()
        if not ready and name != "Direction families ready/generated"
    ]
    if blocking:
        raise ValueError(
            "Missing candidate prerequisites: " + ", ".join(blocking)
        )
    memory = ResearchMemory(DEFAULT_DB)
    try:
        result = search_candidates(
            st.session_state.purpose, [st.session_state.selected_gap],
            st.session_state.mechanisms, st.session_state.seed,
            st.session_state.purpose.preferred_candidate_scale, 24,
            memory.failure_penalties(),
        )
    finally:
        memory.close()
    portfolio = quality_diversity_portfolio(result.candidates, 12)
    current_run = st.session_state.current_research_run
    for candidate in portfolio:
        candidate.research_run_id = current_run.run_id if current_run else ""
    families = create_direction_families(portfolio)
    for family in families:
        family.research_run_id = current_run.run_id if current_run else ""
    diagnostics = summarize_rejections(portfolio, result.rejected_paths)
    st.session_state.candidate_portfolio = portfolio
    st.session_state.direction_families = families
    st.session_state.candidate_run_diagnostics = diagnostics
    return diagnostics


def prepare_missing_candidate_stages(
    progress_callback: object | None = None,
) -> list[str]:
    """Run missing pre-search stages using current state or bundled evidence."""
    stages: list[str] = []

    def report(value: int, label: str) -> None:
        stages.append(label)
        if callable(progress_callback):
            progress_callback(value, label)

    purpose = st.session_state.purpose
    if purpose is None:
        raise ValueError("Purpose contract is missing. Complete Step 1 first.")

    report(20, "1/5 Preparing gap")
    if not st.session_state.gaps:
        run = st.session_state.current_research_run
        if not run or run.actual_search_mode != "OFFLINE_FIXTURE":
            raise ValueError(
                "No gap corpus is available. Complete Step 1 with live, cached, "
                "or explicitly selected offline evidence first."
            )
        papers = load_fixture("ml_papers.json")
        queries = generate_ml_queries(purpose)
        st.session_state.ml_search_diagnostics = offline_diagnostics(
            "data/offline_fixtures/ml_papers.json",
            papers,
            queries,
            purpose.publication_window,
        )
        apply_discovery_result(discover_structural_gaps(papers, purpose))
    if not st.session_state.selected_gap:
        if not st.session_state.gaps:
            raise ValueError("Gap preparation produced no evidence-backed gaps.")
        allowed = set(purpose.allowed_algorithm_families)
        st.session_state.selected_gap = max(
            st.session_state.gaps,
            key=lambda gap: (
                gap.failure_type.casefold() == purpose.current_failure.casefold(),
                not allowed or gap.affected_algorithm_family in allowed,
                gap.confidence_score,
                gap.evidence_count,
            ),
        )

    report(40, "2/5 Retrieving mechanisms")
    if not st.session_state.mechanisms:
        run = st.session_state.current_research_run
        if not run or run.actual_search_mode != "OFFLINE_FIXTURE":
            raise ValueError(
                "External evidence is missing. Complete Step 4; live or cached "
                "runs are never silently replaced with demonstration fixtures."
            )
        papers = load_fixture("external_papers.json")
        mechanisms, rejected = extract_mechanisms(papers)
        mechanism_fallback = not mechanisms
        if mechanism_fallback:
            mechanisms = load_mechanism_seeds()
        st.session_state.external_papers = papers
        st.session_state.mechanisms = cross_domain_only(mechanisms)
        st.session_state.rejected_mechanisms = rejected
        queries = generate_external_queries(st.session_state.selected_gap)
        diagnostics = offline_diagnostics(
            "data/offline_fixtures/external_papers.json",
            papers,
            [query for values in queries.values() for query in values],
            purpose.publication_window,
        )
        diagnostics.fallback_occurred = mechanism_fallback
        diagnostics.fallback_reason = (
            "No mechanism was extracted; curated mechanism seeds were used."
            if mechanism_fallback else ""
        )
        st.session_state.external_search_diagnostics = diagnostics

    report(60, "3/5 Aligning structures")
    if not st.session_state.alignments:
        st.session_state.alignments = [
            align(st.session_state.selected_gap, mechanism, purpose)
            for mechanism in st.session_state.mechanisms
        ]
    if not any(not result.rejected for result in st.session_state.alignments):
        raise ValueError(
            "No structural alignments passed hard validation. "
            "Return to Step 4 or select another gap."
        )

    report(80, "4/5 Synthesizing candidates")
    diagnostics = generate_candidates()
    report(100, "5/5 Building portfolio")
    diagnostics["stages"] = stages
    diagnostics["retrieval_mode"] = (
        st.session_state.external_search_diagnostics.search_mode
        if st.session_state.external_search_diagnostics else "UNKNOWN"
    )
    st.session_state.candidate_run_diagnostics = diagnostics
    return stages


def family_page() -> None:
    st.title("Research direction families")
    if st.button(
        "Run stochastic structured search", type="primary", key="_family_search"
    ):
        try:
            with st.spinner("Generating direction families and candidates…"):
                diagnostics = generate_candidates()
            st.success(
                f"Generated {diagnostics['surviving_candidates']} candidates "
                f"across {diagnostics['algorithm_families']} algorithm families."
            )
        except Exception as exc:
            st.session_state.candidate_run_diagnostics = {
                "status": "failure", "failed_stage": "direction-family generation",
                "error": str(exc), "sampled_paths": 0, "surviving_candidates": 0,
                "algorithm_families": 0, "rejections": {}, "rejected_paths": [],
            }
            st.error(f"Direction-family generation failed: {exc}")
    if not st.session_state.direction_families:
        st.info("Run search after selecting a gap and mechanisms.")
        return
    for family in st.session_state.direction_families:
        with st.expander(f"{family.name} · risk {family.risk_level}", expanded=True):
            st.json(asdict(family))


def render_candidate_diagnostics() -> None:
    """Explain success, empty portfolios, and failed candidate runs."""
    diagnostics = st.session_state.candidate_run_diagnostics
    if not diagnostics:
        return
    status = diagnostics.get("status")
    if status == "success":
        st.success(
            f"Generated {diagnostics['surviving_candidates']} candidates across "
            f"{diagnostics['algorithm_families']} algorithm families."
        )
    elif status == "empty":
        st.warning("No candidates survived validation.")
    elif status == "failure":
        st.error(
            f"Candidate generation failed during "
            f"{diagnostics.get('failed_stage') or 'unknown stage'}: "
            f"{diagnostics.get('error') or 'unknown error'}"
        )
    if diagnostics.get("retrieval_mode"):
        st.info(f"Paper retrieval mode: {diagnostics['retrieval_mode']}")
    if diagnostics.get("stages"):
        st.write("Completed stages:", " → ".join(diagnostics["stages"]))
    st.write(f"Sampled paths: {diagnostics.get('sampled_paths', 0)}")
    if diagnostics.get("rejections"):
        st.subheader("Rejection summary")
        st.dataframe(
            [
                {"reason": reason, "count": count}
                for reason, count in diagnostics["rejections"].items()
            ],
            use_container_width=True,
            hide_index=True,
        )
    if status == "empty":
        st.caption(
            "Recovery options: return to mechanism search, select another gap, "
            "increase the search scale, or use the offline fixture demo. "
            "Hard scientific validation rules were not weakened."
        )
    with st.expander("Rejected path details"):
        st.json(diagnostics.get("rejected_paths", []))


def candidates_page() -> None:
    st.title("Candidate algorithms")
    st.subheader("Candidate generation prerequisites")
    checks = candidate_prerequisites()
    for name, (ready, action) in checks.items():
        st.markdown(f"{'✓' if ready else '✗'} **{name}**"
                    + ("" if ready else f" — {action}"))
    missing = [(name, action) for name, (ready, action) in checks.items() if not ready]
    if missing:
        next_action = missing[0][1]
        st.warning(next_action)
        target = (
            PAGES[0] if "Step 1" in next_action
            else PAGES[1] if "Step 2" in next_action
            else PAGES[3] if "Step 4" in next_action
            else PAGES[4] if "Step 5" in next_action
            else PAGES[5]
        )
        st.button(
            next_action,
            key="_candidate_go_to_missing_step",
            on_click=navigate_to,
            args=(target,),
        )

    st.session_state.setdefault("_candidate_seed", st.session_state.seed)
    seed = st.number_input(
        "Reproducible seed", step=1, key="_candidate_seed"
    )
    st.session_state.seed = int(seed)
    if st.button(
        "Generate from current purpose",
        type="primary",
        key="_candidate_generate_end_to_end",
        disabled=st.session_state.purpose is None,
    ):
        progress = st.progress(0, text="Preparing candidate workflow…")

        def update_progress(value: int, label: str) -> None:
            progress.progress(value, text=label)

        try:
            prepare_missing_candidate_stages(update_progress)
        except Exception as exc:
            st.session_state.candidate_run_diagnostics = {
                "status": "failure",
                "failed_stage": (
                    st.session_state.candidate_run_diagnostics.get("failed_stage", "")
                    if st.session_state.candidate_run_diagnostics else
                    "end-to-end preparation"
                ),
                "error": str(exc), "sampled_paths": 0,
                "surviving_candidates": 0, "algorithm_families": 0,
                "rejections": {}, "rejected_paths": [],
            }
        finally:
            progress.empty()
    if st.button(
        "Regenerate portfolio", type="primary", key="_candidate_regenerate"
    ):
        try:
            with st.spinner("Generating candidate portfolio…"):
                generate_candidates()
        except Exception as exc:
            st.session_state.candidate_run_diagnostics = {
                "status": "failure", "failed_stage": "candidate synthesis",
                "error": str(exc), "sampled_paths": 0,
                "surviving_candidates": 0, "algorithm_families": 0,
                "rejections": {}, "rejected_paths": [],
            }
    render_candidate_diagnostics()
    for candidate in st.session_state.candidate_portfolio:
        with st.expander(f"{candidate.candidate_name} · {candidate.confidence}", expanded=True):
            st.write({
                "scale": candidate.stochastic_trace["search_scale"],
                "base algorithm": candidate.base_algorithm, "gap": candidate.gap_summary,
                "mechanisms": candidate.borrowed_mechanisms, "slot": candidate.affected_component,
                "operators": candidate.selected_operators, "new state": candidate.new_state_variables,
                "expected improvement": candidate.expected_improvement,
                "must not degrade": candidate.must_not_degrade,
                "inference information": candidate.required_inference_information,
                "risk / failure modes": candidate.expected_failure_modes,
            })
            st.json(asdict(candidate.scores))
            st.caption(f"Sampled path: {candidate.stochastic_trace['sampled_structural_path']}")


def novelty_page() -> None:
    st.title("Novelty and falsification")
    for candidate in st.session_state.candidate_portfolio:
        with st.expander(candidate.candidate_name):
            st.write({
                "novelty status": candidate.novelty_status,
                "structural fingerprint": candidate.structural_fingerprint or "computed on export",
                "nearest known methods": candidate.nearest_known_method_patterns,
                "novelty queries": candidate.novelty_queries,
                "strongest rejection reason": candidate.strongest_rejection_reason,
                "kill criterion": candidate.kill_criterion,
                "information audit": candidate.minimal_experiment.information_audit,
            })
            st.markdown("\n".join(f"- {test}" for test in candidate.falsification_tests))
    with st.expander("Rejected search paths"):
        diagnostics = st.session_state.candidate_run_diagnostics or {}
        st.json(diagnostics.get("rejected_paths", []))


def experiment_page() -> None:
    st.title("Minimal experiment")
    candidates = st.session_state.candidate_portfolio
    if not candidates:
        st.info("Generate candidates first.")
        return
    labels = {candidate.candidate_name: candidate for candidate in candidates}
    candidate = labels[
        st.selectbox("Candidate", labels, key="_experiment_candidate")
    ]
    st.json(asdict(candidate.minimal_experiment))
    st.download_button(
        "Download JSON",
        to_json(candidate.minimal_experiment),
        f"{candidate.candidate_id.replace(':', '-')}-experiment.json",
        key="_experiment_download_json",
    )
    st.download_button(
        "Download Markdown",
        experiment_to_markdown(candidate.minimal_experiment),
        f"{candidate.candidate_id.replace(':', '-')}-experiment.md",
        key="_experiment_download_markdown",
    )


def memory_page() -> None:
    st.title("Research memory")
    memory = ResearchMemory(DEFAULT_DB)
    if st.button("Save current run", key="_memory_save"):
        run = st.session_state.current_research_run
        if run:
            run.mechanism_count = len(st.session_state.mechanisms)
            run.candidate_count = len(st.session_state.candidate_portfolio)
            memory.save("research_run", run.run_id, run)
        for paper in [
            *st.session_state.ml_papers, *st.session_state.external_papers
        ]:
            memory.save("paper", paper.paper_id, paper)
        for gap in st.session_state.gaps:
            memory.save("gap", gap.gap_id, gap)
        for mechanism in st.session_state.mechanisms:
            memory.save("mechanism", mechanism.mechanism_id, mechanism)
        for family in st.session_state.direction_families:
            memory.save("direction_family", family.family_id, family)
        for candidate in st.session_state.candidate_portfolio:
            memory.save("candidate", candidate.candidate_id, candidate)
        for record in st.session_state.coverage_records:
            memory.save_structural(
                "coverage_record", record.record_id, record,
                SETTINGS.gap_engine_mode, "coverage-v1",
            )
        for gap in st.session_state.coverage_gaps:
            memory.save_structural(
                "coverage_gap", gap.gap_id, gap,
                SETTINGS.gap_engine_mode, "coverage-v1",
            )
        for mismatch in st.session_state.assumption_mismatches:
            memory.save_structural(
                "assumption_mismatch", mismatch.mismatch_id, mismatch,
                SETTINGS.gap_engine_mode, "assumption-v1",
            )
        for contradiction in st.session_state.contradictory_gaps:
            memory.save_structural(
                "contradictory_evidence", contradiction.contradiction_id,
                contradiction, SETTINGS.gap_engine_mode, "contradiction-v1",
            )
        for cluster in st.session_state.research_clusters:
            memory.save_structural(
                "research_cluster", cluster.cluster_id, cluster,
                SETTINGS.gap_engine_mode,
                st.session_state.engine_diagnostics.get("embedding_version", ""),
            )
        diagnostics = st.session_state.candidate_run_diagnostics or {}
        for index, rejection in enumerate(diagnostics.get("rejected_paths", [])):
            fingerprint = "|".join(str(rejection.get(key, ""))
                                   for key in ("gap", "mechanism", "operator"))
            memory.remember_failure(fingerprint, "weak evidence", json.dumps(rejection))
        st.success("Saved run provenance, papers, scientific records, and failures.")
    tabs = st.tabs([
        "Runs", "Gaps", "Mechanisms", "Families", "Candidates", "Failures"
    ])
    for tab, kind in zip(tabs[:5], [
        "research_run", "gap", "mechanism", "direction_family", "candidate"
    ]):
        tab.json(memory.list(kind))
    tabs[5].json(memory.failures())
    exported = {
        kind: memory.list(kind) for kind in ("gap", "mechanism", "direction_family", "candidate")
    }
    st.download_button(
        "Export memory JSON",
        json.dumps(exported, indent=2),
        "research-memory.json",
        key="_memory_download_json",
    )
    flat = [{"kind": kind, **record} for kind, records in exported.items() for record in records]
    st.download_button(
        "Export memory CSV",
        records_to_csv(flat),
        "research-memory.csv",
        key="_memory_download_csv",
    )
    markdown = "# Research memory\n\n" + "\n\n".join(
        f"## {kind.replace('_', ' ').title()}\n\n```json\n{json.dumps(records, indent=2)}\n```"
        for kind, records in exported.items()
    )
    st.download_button(
        "Export memory Markdown",
        markdown,
        "research-memory.md",
        key="_memory_download_markdown",
    )
    memory.close()


def main() -> None:
    st.set_page_config(page_title="Purpose-Driven Algorithm Discovery", layout="wide")
    initialize_state()
    page = sidebar()
    handlers = [goal_page, gap_radar_page, evidence_page, mechanism_page, alignment_page,
                family_page, candidates_page, novelty_page, experiment_page, memory_page]
    handlers[PAGES.index(page)]()
    if st.session_state.get("_show_quality_evaluation"):
        quality_evaluation_panel()
    if st.session_state.ml_papers:
        with st.sidebar.expander("Trend radar"):
            st.json(trend_indicators(st.session_state.ml_papers + st.session_state.external_papers))
    if st.session_state.fetch_failures:
        st.sidebar.warning("Partial source failures occurred; available results remain usable.")
        st.sidebar.json(st.session_state.fetch_failures)


if __name__ == "__main__":
    main()
