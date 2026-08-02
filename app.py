"""Thin Streamlit UI for the no-LLM purpose-driven discovery pipeline."""

from __future__ import annotations

import json
import csv
import io
import time
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
from run_models import ResearchRun, SelectedGapSnapshot, StageRun
from retrieval_service import retrieve_corpus
from pipeline_quality import generate_quality_warnings
from research_memory import ResearchMemory
from search_engine import search_candidates
from signatures import load_mechanism_seeds
from trend_analysis import trend_indicators
from weak_supervision import GapLabel, label_sentence
from build_info import build_information
from evaluation.capabilities import (
    AuditBuildResult, load_result_audit_capability,
)
from run_models import utc_now
from result_explanation import research_result
from ux_models import (
    PIPELINE_VERSION, SELECTED_IDEA_SCHEMA_VERSION, SelectedIdeaContext,
    build_direction_portfolio, build_idea_derivation, build_idea_explanation,
    candidate_from_dict, candidate_modification, candidate_to_dict,
    derivation_from_dict, derivation_to_dict, direction_from_dict,
    direction_to_dict, gap_from_dict, gap_to_dict, selected_idea_fingerprints,
)
from diagram_builders import (
    before_after_spec, evidence_to_idea_spec, experiment_spec,
    mechanism_transfer_spec,
)
from external_discovery_pipeline import SearchPolicy
from session_schema import SESSION_STATE_SCHEMA_VERSION, resolve_external_result
from idea_pipeline import derive_ideas_for_direction
from primary_idea_selection import select_primary_idea

PRIMARY_STEPS = [
    "1 · Discover directions / 发现方向",
    "2 · Analyze the gap / 分析 Gap",
    "3 · Explain the idea / 解释新想法",
]
PAGES = PRIMARY_STEPS  # Compatibility for non-UI helpers.


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
        "evidence_events": [], "canonical_gap_families": [],
        "promoted_gap_families": [], "exploratory_gap_families": [],
        "promoted_gaps": [], "exploratory_gaps": [],
        "current_purpose_contract": None,
        "current_direction_portfolio": [],
        "selected_direction_id": "",
        "selected_direction_snapshot": None,
        "selected_gap_family_id": "",
        "current_idea_portfolio": [],
        "selected_idea_id": "",
        "selected_candidate_snapshot": None,
        "selected_derivation_snapshot": None,
        "selected_idea_context": None,
        "selected_idea_selection_error": "",
        "selected_idea_selection_version": SELECTED_IDEA_SCHEMA_VERSION,
        "selected_idea_selection_error_details": {},
        "primary_idea_selection_record": None,
        "automatic_recovery_attempted": False,
        "pending_primary_step": "",
        "workflow_guidance": "",
        "current_result_explanation": None,
        "current_result_audit": None,
        "current_audit_build_result": None,
        "audit_unavailable_notice_shown": False,
        "current_diagram_specs": [],
        "current_external_result": None,
        "session_state_schema_version": SESSION_STATE_SCHEMA_VERSION,
        "external_result_resolution": "ABSENT",
        "external_result_migration_message": "",
        "external_result_rebuild_required": False,
        "active_primary_step": PRIMARY_STEPS[0],
        "ux_performance": {},
        "engine_diagnostics": engine_state_defaults(SETTINGS),
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    migrate_external_session_state()


def _external_identity() -> tuple[str, str, str] | None:
    run = st.session_state.current_research_run
    direction = st.session_state.selected_direction_snapshot
    gap = st.session_state.selected_gap
    if not (run and direction and gap):
        return None
    return run.run_id, direction.direction_id, gap.gap_id


def resolve_current_external_result():
    """Return a normalized typed view while persisting only versioned data."""
    resolution = resolve_external_result(
        st.session_state.current_external_result, _external_identity()
    )
    st.session_state.external_result_resolution = resolution.status
    st.session_state.external_result_migration_message = resolution.message
    if resolution.status in {"CURRENT", "MIGRATED", "PARTIALLY_MIGRATED"} and resolution.result:
        st.session_state.current_external_result = resolution.result.to_dict()
        return resolution.result
    return None


def _clear_external_downstream_state() -> None:
    """Invalidate only state derived from external discovery."""
    replacements = {
        "current_external_result": None, "current_external_run": None,
        "external_papers": [], "mechanisms": [], "rejected_mechanisms": [],
        "alignments": [], "candidate_portfolio": [], "direction_families": [],
        "current_idea_portfolio": [], "selected_idea_id": "",
        "selected_candidate_snapshot": None, "selected_derivation_snapshot": None,
        "selected_idea_context": None, "primary_idea_selection_record": None,
        "current_result_explanation": None, "current_result_audit": None,
    }
    for key, value in replacements.items():
        st.session_state[key] = value


def migrate_external_session_state() -> None:
    """Hot-reload migration entry point, executed once on every app run."""
    value = st.session_state.current_external_result
    if value is None:
        st.session_state.session_state_schema_version = SESSION_STATE_SCHEMA_VERSION
        return
    resolution = resolve_external_result(value, _external_identity())
    st.session_state.external_result_resolution = resolution.status
    st.session_state.external_result_migration_message = resolution.message
    if resolution.status in {"CURRENT", "MIGRATED", "PARTIALLY_MIGRATED"} and resolution.result:
        st.session_state.current_external_result = resolution.result.to_dict()
    elif resolution.status in {"IDENTITY_MISMATCH", "INVALID_SCHEMA", "UNRECOVERABLE"}:
        _clear_external_downstream_state()
        st.session_state.external_result_rebuild_required = True
    st.session_state.session_state_schema_version = SESSION_STATE_SCHEMA_VERSION


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
    st.session_state.evidence_events = result.consolidation.evidence_events
    st.session_state.canonical_gap_families = result.consolidation.families
    st.session_state.promoted_gap_families = result.consolidation.promoted
    st.session_state.exploratory_gap_families = result.consolidation.exploratory
    by_id = {gap.gap_id: gap for gap in result.gaps}
    st.session_state.promoted_gaps = [
        by_id[family.representative_gap_id]
        for family in result.consolidation.promoted
    ]
    st.session_state.exploratory_gaps = [
        by_id[family.representative_gap_id]
        for family in result.consolidation.exploratory
    ]
    configuration_warnings = st.session_state.engine_diagnostics.get(
        "configuration_warnings", []
    )
    st.session_state.engine_diagnostics = {
        **result.diagnostics,
        "configuration_warnings": configuration_warnings,
    }


def record_discovery_stages(
    run: ResearchRun, result: StructuralDiscoveryResult
) -> None:
    durations = result.diagnostics.get("stage_durations", {})
    stage_values = {
        "paper_reranking": (len(result.papers), len(result.papers)),
        "paper_clustering": (len(result.papers), len(result.research_clusters)),
        "gap_extraction": (
            len(result.papers), len(result.consolidation.raw_instances)
        ),
        "gap_consolidation": (
            len(result.consolidation.raw_instances),
            len(result.consolidation.families),
        ),
        "known_solution_search": (
            len(result.consolidation.families),
            len(result.known_solution_results),
        ),
    }
    for name, (raw_count, output_count) in stage_values.items():
        seconds = float(durations.get(name, 0))
        run.stages.append(StageRun(
            stage_id=f"{run.run_id}:{name}", stage_name=name,
            parent_run_id=run.run_id, started_at=run.created_at_utc,
            completed_at=utc_now(), wall_clock_duration_seconds=seconds,
            requested_mode=SETTINGS.gap_engine_mode,
            actual_mode=str(result.diagnostics.get("active_mode", "lightweight")),
            raw_input_count=raw_count, output_count=output_count,
            accepted_count=output_count,
            model_backend=str(result.diagnostics.get("embedding_model", "none")),
            model_version=str(result.diagnostics.get("embedding_version", "")),
        ))
    run.evidence_event_count = len(result.consolidation.evidence_events)
    run.raw_gap_instance_count = len(result.consolidation.raw_instances)
    run.canonical_gap_family_count = len(result.consolidation.families)
    run.promoted_gap_count = len(result.consolidation.promoted)
    run.exploratory_gap_count = len(result.consolidation.exploratory)
    evidence_papers = {
        event.paper_id for event in result.consolidation.evidence_events
        if event.paper_id not in {"corpus", "purpose"}
        and event.paper_id in {paper.paper_id for paper in result.papers}
    }
    run.evidence_bearing_paper_count = len(evidence_papers)
    run.papers_used_for_gap_generation = len(result.papers)
    run.papers_used_for_known_solution_search = len(result.papers)


def upsert_stage(run: ResearchRun | None, stage: StageRun) -> None:
    """Replace the latest record for a deterministic UI stage."""
    if not run:
        return
    run.stages = [
        item for item in run.stages if item.stage_name != stage.stage_name
    ]
    run.stages.append(stage)


def invalidate_downstream_for_purpose() -> None:
    """Prevent a new purpose from displaying results from an older run."""
    for key, empty in {
        "selected_gap": None, "selected_gap_id": "", "external_papers": [],
        "mechanisms": [], "rejected_mechanisms": [], "alignments": [],
        "direction_families": [], "candidate_portfolio": [],
        "external_search_diagnostics": None, "current_external_run": None,
        "current_direction_portfolio": [], "selected_direction_id": "",
        "selected_direction_snapshot": None, "selected_gap_family_id": "",
        "current_idea_portfolio": [], "selected_idea_id": "",
        "selected_candidate_snapshot": None,
        "selected_derivation_snapshot": None,
        "selected_idea_context": None,
        "selected_idea_selection_error": "",
        "selected_idea_selection_version": SELECTED_IDEA_SCHEMA_VERSION,
        "selected_idea_selection_error_details": {},
        "primary_idea_selection_record": None,
        "automatic_recovery_attempted": False,
        "current_result_explanation": None, "current_diagram_specs": [],
        "current_result_audit": None,
        "current_audit_build_result": None,
        "current_external_result": None,
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
    st.session_state.current_external_result = None
    st.session_state.current_idea_portfolio = []
    st.session_state.selected_idea_id = ""
    st.session_state.selected_candidate_snapshot = None
    st.session_state.selected_derivation_snapshot = None
    st.session_state.selected_idea_context = None
    st.session_state.selected_idea_selection_error = ""
    st.session_state.selected_idea_selection_error_details = {}
    st.session_state.primary_idea_selection_record = None
    st.session_state.automatic_recovery_attempted = False
    st.session_state.current_result_explanation = None
    st.session_state.current_result_audit = None
    st.session_state.current_audit_build_result = None
    st.session_state.current_diagram_specs = []


def snapshot_selected_gap(gap: object, run: ResearchRun) -> dict[str, object]:
    """Freeze the readable gap evidence used by downstream candidates."""
    return asdict(SelectedGapSnapshot(
        gap_id=gap.gap_id,
        title=gap.title,
        plain_language_statement=(
            f"{gap.failure_type} affects {gap.affected_component}; "
            f"the unresolved need is {gap.required_response}."
        ),
        gap_type=gap.structural_gap_subtype or gap.gap_type,
        affected_task=gap.task,
        affected_algorithm_family=gap.affected_algorithm_family,
        binding_granularity=(
            "exact algorithm" if gap.affected_algorithm != "Unspecified"
            else "algorithm family"
        ),
        failure_condition=gap.failure_type,
        affected_metric=gap.primary_metric,
        evidence_papers=tuple(gap.evidence_paper_ids),
        known_solutions=tuple(gap.known_mitigations),
        unresolved_remainder=gap.unresolved_remainder,
        confidence=gap.confidence_score,
        selected_timestamp=utc_now(),
        parent_run_id=run.run_id,
    ))


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
        "Candidate papers": run.candidate_paper_count,
        "Automatically relevant": run.automatically_relevant_paper_count,
        "Human reviewed": run.human_reviewed_paper_count,
        "Human-confirmed relevant": run.human_confirmed_relevant_paper_count,
        "Evidence-bearing": run.evidence_bearing_paper_count,
        "Broad / focused / external / total queries": (
            f"{run.broad_query_count} / {run.focused_query_count} / "
            f"{run.external_query_count} / {run.total_query_count}"
        ),
        "Unique sources / source-stage results": (
            f"{run.unique_source_count} / {run.source_stage_result_count}"
        ),
        "Overall wall-clock seconds": run.overall_wall_clock_duration_seconds,
        "Sum source-request seconds": run.sum_source_request_duration_seconds,
        "Retrieved at UTC": run.created_at_utc,
        "Fixture paths": run.fixture_paths,
        "Fixture version": run.fixture_version or "not applicable",
    })
    st.dataframe([{
        "source": item.source, "origin": item.actual_origin or item.source_type,
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
    if run.quality_warnings:
        st.error("Automated quality warnings")
        st.dataframe([
            asdict(warning) for warning in run.quality_warnings
        ], use_container_width=True, hide_index=True)
    if run.stages:
        with st.expander("Stage-scoped provenance"):
            st.dataframe([{
                "stage": stage.stage_name,
                "duration": stage.wall_clock_duration_seconds,
                "queries": stage.query_count,
                "input": stage.raw_input_count,
                "output": stage.output_count,
                "accepted": stage.accepted_count,
                "rejected": stage.rejected_count,
                "mode": stage.actual_mode,
                "backend": stage.model_backend,
            } for stage in run.stages], use_container_width=True, hide_index=True)
    with st.expander("Query strings", expanded=True):
        for query in [*run.ml_queries, *run.focused_algorithm_queries]:
            st.code(query)


def navigate_to(page: str) -> None:
    """Update the sidebar widget through a pre-rerun button callback."""
    st.session_state["_primary_step"] = page
    st.session_state.active_primary_step = page


def choose_search_mode(mode: str, force_fresh: bool = False) -> None:
    """Return to Discover directions with an explicit retrieval choice."""
    st.session_state["_purpose_search_mode"] = mode
    st.session_state["_purpose_force_fresh"] = force_fresh
    st.session_state["_primary_step"] = PRIMARY_STEPS[0]


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
            "Return to Discover directions",
        ),
        "Selected gap": (
            gap is not None,
            "Select a research direction",
        ),
        "External mechanisms": (
            bool(mechanisms),
            "Search external evidence",
        ),
        "Accepted structural alignments": (
            bool(accepted),
            "Inspect structural alignment",
        ),
        "Direction families ready/generated": (
            bool(st.session_state.direction_families) or bool(accepted),
            "Derive candidate ideas",
        ),
        "Compatible base algorithm": (
            compatible_algorithm,
            "Select a gap linked to a supported algorithm",
        ),
        "Primary metric": (
            bool(purpose and purpose.primary_metric),
            "Define a primary metric in Discover directions",
        ),
        "Inference information": (
            bool(purpose and purpose.available_inference_information),
            "Define inference-time information in Discover directions",
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
    st.sidebar.markdown("**1 发现方向 → 2 分析 Gap → 3 解释新想法**")
    step = st.sidebar.radio(
        "Primary workflow", PRIMARY_STEPS, key="_primary_step"
    )
    st.session_state.active_primary_step = step
    with st.sidebar.expander("Research Tools / 研究工具", expanded=False):
        st.selectbox(
            "Technical view",
            [
                "None", "Research run provenance", "Full retrieval diagnostics",
                "Coverage and evidence audit", "Structural alignment audit",
                "Multi-angle result audit", "Quality Evaluation",
                "Annotation tools", "Research memory",
                "Build information",
            ],
            key="_research_tool",
        )
    info = build_information(SETTINGS.gap_engine_mode)
    app_fingerprint = info["source_fingerprints"].get("app.py", "missing")
    st.sidebar.divider()
    st.sidebar.caption(f"Build: {info['commit_sha'][:8]}")
    st.sidebar.caption(f"Pipeline: {info['pipeline_version']}")
    st.sidebar.caption(f"UX schema: {info['ux_schema_version']}")
    st.sidebar.caption(f"Source fingerprint: {app_fingerprint[:8]}")
    st.sidebar.caption(
        "Deployment consistency: "
        + info["deployment_consistency"]["status"]
    )
    return step


def quality_evaluation_panel() -> None:
    """Optional benchmark and human-review surface outside the ten-step flow."""
    st.divider()
    st.header("Quality Evaluation")
    try:
        from evaluation.benchmark_tasks import load_benchmark_tasks
        from evaluation.report_generation import report_json, report_markdown
        from evaluation.run_benchmark import run_offline_benchmark
        from evaluation.schemas import HumanReview
    except Exception as exc:
        st.warning(
            "Quality evaluation is temporarily unavailable. The primary "
            "research workflow remains available."
        )
        with st.expander("Technical details"):
            st.write({
                "Error type": type(exc).__name__,
                "Sanitized error": " ".join(str(exc).split())[:500],
                "Recommended action": "Reboot or redeploy the current main commit.",
            })
        return
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
            memory = ResearchMemory(DEFAULT_DB)
            try:
                for audit in st.session_state.quality_evaluation_report.result_audits:
                    memory.save_result_audit(audit)
            finally:
                memory.close()
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
        st.subheader("Complete result audits")
        for audit in report.result_audits:
            render_result_audit(audit, full=True)
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
            stage_name="broad_ml_retrieval",
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
                stage_name="focused_ml_retrieval",
            )
            papers = deduplicate_papers([*papers, *focused_papers])[:int(maximum_total)]
            run.source_results.extend(focused_run.source_results)
            run.stages.extend(focused_run.stages)
            run.source_failures.update(focused_run.source_failures)
            run.raw_paper_count += focused_run.raw_paper_count
            run.focused_query_count = len(focused_queries)
            run.total_query_count = run.broad_query_count + run.focused_query_count
            run.query_count = run.total_query_count
            run.finalize_from_papers(papers)
        binding = (
            bindings[0] if bindings and bindings[0].confidence >=
            SETTINGS.algorithm_binding_confidence_threshold else None
        )
        discovery = discover_structural_gaps(
            papers, purpose,
            restriction.name if restriction else (
                binding.algorithm if (
                    binding and binding.binding_granularity == "exact algorithm"
                ) else "Unspecified"
            ),
        )
        for gap in discovery.gaps:
            gap.research_run_id = run.run_id
        apply_discovery_result(discovery)
        run.structural_gap_count = len(discovery.gaps)
        record_discovery_stages(run, discovery)
        generate_quality_warnings(run)
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
    gaps = st.session_state.promoted_gaps
    if not gaps:
        st.info(
            "No gap family passed promotion gates. Review exploratory families "
            "and raw instances in the audit sections."
        )
        with st.expander("Exploratory gap families", expanded=True):
            st.dataframe([
                {
                    "family": family.representative_title,
                    "status": family.promotion_status,
                    "supporting papers": family.empirical_support_count,
                    "reasons": "; ".join(family.rejection_reasons),
                }
                for family in st.session_state.exploratory_gap_families
            ], use_container_width=True)
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
    st.write({
        "Evidence events": len(st.session_state.evidence_events),
        "Raw gap instances": len(st.session_state.gaps),
        "Canonical gap families": len(st.session_state.canonical_gap_families),
        "Promoted research gaps": len(st.session_state.promoted_gap_families),
        "Exploratory families": len(st.session_state.exploratory_gap_families),
    })
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
            run.selected_gap_snapshot = snapshot_selected_gap(labels[chosen], run)
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
    with st.expander("Exploratory gap families"):
        st.dataframe([
            {
                "family": family.representative_title,
                "status": family.promotion_status,
                "support": family.empirical_support_count,
                "known mitigations": ", ".join(family.known_mitigations),
                "unresolved": family.unresolved_remainder,
                "rejection reasons": "; ".join(family.rejection_reasons),
            }
            for family in st.session_state.exploratory_gap_families
        ], use_container_width=True)
    with st.expander("Raw gap instances · technical audit"):
        st.dataframe([
            {
                "gap_id": gap.gap_id, "title": gap.title,
                "type": gap.structural_gap_subtype or gap.gap_type,
                "papers": len(set(gap.evidence_paper_ids)),
                "confidence": gap.confidence_score,
            } for gap in st.session_state.gaps
        ], use_container_width=True)


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
    """Technical view of the same reusable pipeline used by Part 2."""
    st.title("External mechanism search · technical view")
    if not st.session_state.selected_direction_snapshot:
        st.info("Select a research direction before searching external evidence.")
        return
    if st.button("Run direction-scoped external pipeline", key="_mechanism_fetch"):
        build_current_idea_portfolio()
    result = resolve_current_external_result()
    if not result:
        st.info("Search external evidence from Analyze the gap or run it here.")
        return
    st.json({
        "identity": result.identity(),
        "problem": asdict(result.cross_domain_problem_signature),
        "domains": [asdict(item) for item in result.ranked_domain_selections],
        "queries": result.accepted_queries_by_domain,
        "diagnostics": result.stage_diagnostics,
        "warnings": result.warnings,
        "errors": result.errors,
    })
    render_research_run(result.retrieval_run, "External retrieval provenance")
    st.dataframe([{
        "mechanism": item.name, "domain": item.source_domain,
        "signal": item.observed_signal, "state": item.internal_state,
        "trigger": item.trigger_condition, "response": item.response_rule,
        "evidence": item.evidence_count,
    } for item in result.mechanisms], use_container_width=True)


def alignment_page() -> None:
    st.title("Structural alignment")
    gap, mechanisms = st.session_state.selected_gap, st.session_state.mechanisms
    if not gap or not mechanisms:
        st.info("Select a gap and extract mechanisms first.")
        return
    started = datetime.now(timezone.utc)
    results = [align(gap, mechanism, st.session_state.purpose) for mechanism in mechanisms]
    current_run = st.session_state.current_research_run
    for result in results:
        result.research_run_id = current_run.run_id if current_run else ""
    st.session_state.alignments = results
    if current_run:
        strong = sum(not item.rejected and item.score >= .7 for item in results)
        plausible = sum(not item.rejected and item.score < .7 for item in results)
        current_run.alignment_funnel = {
            "raw_pairs": len(results), "compatible": strong + plausible,
            "plausible": plausible, "strong": strong,
            "rejected": sum(item.rejected for item in results),
            "candidates": current_run.candidate_count,
        }
        upsert_stage(current_run, StageRun(
            stage_id=f"{current_run.run_id}:structural_alignment",
            stage_name="structural_alignment",
            parent_run_id=current_run.run_id,
            started_at=started.isoformat(timespec="seconds"),
            completed_at=utc_now(),
            wall_clock_duration_seconds=(
                datetime.now(timezone.utc) - started
            ).total_seconds(),
            raw_input_count=len(mechanisms),
            output_count=len(results),
            accepted_count=strong + plausible,
            rejected_count=sum(item.rejected for item in results),
            model_backend="deterministic_structural_matcher",
        ))
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
    accepted_alignments = [
        item for item in st.session_state.alignments if not item.rejected
    ]
    best_alignment = max(
        accepted_alignments, key=lambda item: item.score, default=None
    )
    for candidate in portfolio:
        candidate.research_run_id = current_run.run_id if current_run else ""
        candidate.alignment_id = (
            f"{best_alignment.gap_id}:{best_alignment.mechanism_id}"
            if best_alignment else ""
        )
        candidate.alignment_acceptance = (
            "STRONG" if best_alignment and best_alignment.score >= .7
            else "PLAUSIBLE_ACCEPTED" if best_alignment else ""
        )
        candidate.selected_gap_snapshot = dict(
            current_run.selected_gap_snapshot if current_run else {}
        )
    families = create_direction_families(portfolio)
    for family in families:
        family.research_run_id = current_run.run_id if current_run else ""
    diagnostics = summarize_rejections(portfolio, result.rejected_paths)
    if current_run:
        current_run.candidate_count = len(portfolio)
        current_run.alignment_funnel = {
            "raw_pairs": len(st.session_state.alignments),
            "compatible": len(accepted_alignments),
            "plausible": sum(
                not item.rejected and item.score < .7
                for item in st.session_state.alignments
            ),
            "strong": sum(
                not item.rejected and item.score >= .7
                for item in st.session_state.alignments
            ),
            "rejected": sum(item.rejected for item in st.session_state.alignments),
            "candidates": len(portfolio),
        }
        upsert_stage(current_run, StageRun(
            stage_id=f"{current_run.run_id}:candidate_synthesis",
            stage_name="candidate_synthesis",
            parent_run_id=current_run.run_id,
            started_at=utc_now(), completed_at=utc_now(),
            raw_input_count=diagnostics.get("sampled_paths", 0),
            output_count=len(result.candidates),
            accepted_count=len(result.candidates),
            rejected_count=len(result.rejected_paths),
            model_backend="typed_stochastic_search",
        ))
        upsert_stage(current_run, StageRun(
            stage_id=f"{current_run.run_id}:portfolio_selection",
            stage_name="portfolio_selection",
            parent_run_id=current_run.run_id,
            started_at=utc_now(), completed_at=utc_now(),
            raw_input_count=len(result.candidates),
            output_count=len(portfolio), accepted_count=len(portfolio),
            rejected_count=max(0, len(result.candidates) - len(portfolio)),
            model_backend="quality_diversity_portfolio",
        ))
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
        raise ValueError("Purpose contract is missing. Return to Discover directions.")

    report(20, "1/5 Preparing gap")
    if not st.session_state.gaps:
        run = st.session_state.current_research_run
        if not run or run.actual_search_mode != "OFFLINE_FIXTURE":
            raise ValueError(
                "No gap corpus is available. Run Discover directions with live, cached, "
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
        selectable_gaps = st.session_state.promoted_gaps
        if not selectable_gaps:
            raise ValueError(
                "Gap preparation produced no promoted evidence-backed gap family."
            )
        allowed = set(purpose.allowed_algorithm_families)
        st.session_state.selected_gap = max(
            selectable_gaps,
            key=lambda gap: (
                gap.affected_component != "model_selection",
                gap.failure_type.casefold() == purpose.current_failure.casefold(),
                not allowed or gap.affected_algorithm_family in allowed,
                gap.confidence_score,
                gap.evidence_count,
            ),
        )
        run = st.session_state.current_research_run
        if run:
            run.selected_gap_id = st.session_state.selected_gap.gap_id
            run.selected_gap_snapshot = snapshot_selected_gap(
                st.session_state.selected_gap, run
            )

    report(40, "2/5 Retrieving mechanisms")
    if not st.session_state.mechanisms:
        run = st.session_state.current_research_run
        if not run or run.actual_search_mode != "OFFLINE_FIXTURE":
            raise ValueError(
                "External evidence is missing. Search external evidence for the "
                "selected direction; live or cached runs are never silently "
                "replaced with demonstration fixtures."
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
            "Search different external evidence or choose another direction."
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
            PRIMARY_STEPS[0]
            if next_action in {"Return to Discover directions", "Select a research direction"}
            else PRIMARY_STEPS[1]
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
    if st.session_state.candidate_portfolio:
        candidate = st.session_state.candidate_portfolio[0]
        mechanism = next((
            item for item in st.session_state.mechanisms
            if item.mechanism_id in candidate.borrowed_mechanisms
        ), st.session_state.mechanisms[0] if st.session_state.mechanisms else None)
        alignment = next((
            item for item in st.session_state.alignments
            if candidate.alignment_id == f"{item.gap_id}:{item.mechanism_id}"
        ), None)
        result = research_result(
            st.session_state.current_research_run,
            st.session_state.selected_gap, mechanism, alignment, candidate,
        )
        st.header("Research Result / 研究结果")
        st.success(result["conclusion"])
        st.subheader("Derivation at a glance")
        st.write(result["derivation_funnel"])
        st.subheader("BEFORE → CHANGE → EXPECTED")
        st.write({
            "BEFORE": result["before"], "CHANGE": result["change"],
            "EXPECTED": result["expected"],
        })
        st.subheader("Evidence and uncertainty")
        st.write({
            "SUPPORTED": result["supported"],
            "SYSTEM-INFERRED": result["system_inferred"],
            "UNKNOWN": result["unknown"],
        })
        with st.expander("Technical details · raw result"):
            st.json(result)
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


def execute_direction_search(
    task: str, failure: str, improvement: str, data_type: str,
    use_case: str, metric: str, years: tuple[int, int], search_mode: str,
    sources: list[str], force_fresh: bool, allow_cache: bool,
    allow_offline_fallback: bool, maximum_per_query: int, maximum_total: int,
) -> None:
    """Run the unchanged retrieval/discovery pipeline for the Part 1 action."""
    previous = st.session_state.purpose
    same_purpose = bool(
        previous and previous.task == task and previous.data_type == data_type
        and previous.current_failure == failure
        and previous.desired_improvement == improvement
        and previous.publication_window == years
    )
    purpose = PurposeContract(
        previous.purpose_id if same_purpose else f"purpose:{uuid4().hex[:10]}",
        "user", use_case, task, data_type, failure, improvement, metric,
        ["recovery time", "memory use"], ["stable-regime accuracy"],
        available_training_information=["features", "delayed outcome feedback"],
        available_inference_information=[
            "input features", "prediction residual", "regime similarity",
        ],
        risk_tolerance="medium", preferred_candidate_scale="small",
        publication_window=years,
    )
    if not same_purpose:
        invalidate_downstream_for_purpose()
    st.session_state.purpose = purpose
    st.session_state.current_purpose_contract = purpose
    broad_queries, broad_audit = generate_problem_queries(purpose)
    requested_mode = {
        "Live scholarly APIs": "LIVE",
        "Cached live results": "CACHE",
        "Offline demonstration fixtures": "OFFLINE_FIXTURE",
    }[search_mode]
    papers, run = retrieve_corpus(
        purpose, broad_queries, requested_mode=requested_mode, sources=sources,
        maximum_per_query=maximum_per_query, maximum_total=maximum_total,
        allow_cache=allow_cache, allow_offline_fallback=allow_offline_fallback,
        force_fresh=force_fresh,
        fixture_loader=lambda: load_fixture("ml_papers.json"),
        fixture_path="data/offline_fixtures/ml_papers.json",
        stage_name="broad_ml_retrieval",
    )
    run.search_policy = SearchPolicy(
        requested_mode=requested_mode, sources=tuple(sources),
        allow_cache=allow_cache, force_fresh=force_fresh,
        allow_offline_fallback=allow_offline_fallback,
        maximum_per_query=maximum_per_query,
        maximum_total=maximum_total,
    ).to_dict()
    bindings = detect_algorithm_bindings(papers, purpose)
    focused_queries, focused_audit = generate_focused_algorithm_queries(
        purpose, bindings, SETTINGS.algorithm_binding_confidence_threshold
    )
    run.focused_algorithm_queries = focused_queries
    if focused_queries and requested_mode != "OFFLINE_FIXTURE" and papers:
        focused_papers, focused_run = retrieve_corpus(
            purpose, focused_queries, requested_mode=requested_mode,
            sources=sources, maximum_per_query=maximum_per_query,
            maximum_total=maximum_total, allow_cache=allow_cache,
            force_fresh=force_fresh, stage_name="focused_ml_retrieval",
        )
        papers = deduplicate_papers([*papers, *focused_papers])[:maximum_total]
        run.source_results.extend(focused_run.source_results)
        run.stages.extend(focused_run.stages)
        run.source_failures.update(focused_run.source_failures)
        run.raw_paper_count += focused_run.raw_paper_count
        run.focused_query_count = len(focused_queries)
        run.total_query_count = run.broad_query_count + run.focused_query_count
        run.query_count = run.total_query_count
        run.finalize_from_papers(papers)
    binding = (
        bindings[0] if bindings and bindings[0].confidence >=
        SETTINGS.algorithm_binding_confidence_threshold else None
    )
    discovery = discover_structural_gaps(
        papers, purpose,
        binding.algorithm if binding and binding.binding_granularity ==
        "exact algorithm" else "Unspecified",
    )
    for gap in discovery.gaps:
        gap.research_run_id = run.run_id
    apply_discovery_result(discovery)
    record_discovery_stages(run, discovery)
    run.structural_gap_count = len(discovery.gaps)
    generate_quality_warnings(run)
    portfolio = build_direction_portfolio(
        run.run_id, purpose, discovery.consolidation.promoted,
        discovery.gaps, discovery.papers,
    )
    st.session_state.current_research_run = run
    st.session_state.current_direction_portfolio = portfolio
    st.session_state.algorithm_bindings = bindings
    st.session_state.problem_query_audit = broad_audit
    st.session_state.focused_query_audit = focused_audit
    st.session_state.fetch_failures = run.source_failures


def select_direction(direction_id: str) -> None:
    directions = {
        item.direction_id: item
        for item in st.session_state.current_direction_portfolio
    }
    direction = directions[direction_id]
    if st.session_state.selected_direction_id != direction_id:
        invalidate_downstream_for_gap()
    gap = next(
        item for item in st.session_state.promoted_gaps
        if item.gap_id == direction.selected_gap_id
    )
    st.session_state.selected_direction_id = direction_id
    st.session_state.selected_direction_snapshot = direction
    st.session_state.selected_gap_family_id = direction.gap_family_ids[0]
    st.session_state.selected_gap = gap
    st.session_state.selected_gap_id = gap.gap_id
    run = st.session_state.current_research_run
    if run:
        run.selected_gap_id = gap.gap_id
        run.selected_gap_snapshot = snapshot_selected_gap(gap, run)
    st.session_state["_primary_step"] = PRIMARY_STEPS[1]
    st.session_state.active_primary_step = PRIMARY_STEPS[1]


def _selection_context(
    *, candidate: object, derivation: object, direction: object, gap: object,
    run: ResearchRun, active_direction_id: str, active_gap_id: str,
    resolution_source: str = "immutable snapshot",
) -> SelectedIdeaContext:
    """Validate and construct a selection without mutating session state."""
    errors = []
    partial = []
    if candidate.candidate_id != derivation.candidate_id:
        errors.append("candidate and derivation IDs differ")
    if derivation.parent_run_id != run.run_id:
        errors.append("derivation belongs to another research run")
    if candidate.research_run_id:
        if candidate.research_run_id != run.run_id:
            errors.append("candidate belongs to another research run")
    else:
        partial.append("legacy candidate has no research_run_id")
    if derivation.direction_id != direction.direction_id:
        errors.append("derivation belongs to another direction")
    if direction.direction_id != active_direction_id:
        errors.append("selected direction snapshot does not match session state")
    if gap.gap_id != active_gap_id:
        errors.append("selected gap does not match session state")
    candidate_gap_id = candidate.selected_gap_snapshot.get("gap_id", "")
    if candidate_gap_id:
        if candidate_gap_id != gap.gap_id:
            errors.append("candidate gap snapshot belongs to another gap")
    else:
        partial.append("legacy candidate has no selected gap ID")
    if errors:
        raise ValueError("; ".join(errors))
    candidate_snapshot = candidate_to_dict(candidate)
    derivation_snapshot = derivation_to_dict(derivation)
    candidate_fingerprint, derivation_fingerprint = selected_idea_fingerprints(
        candidate_snapshot, derivation_snapshot,
    )
    return SelectedIdeaContext(
        selection_id=f"selection:{uuid4().hex}", selected_at_utc=utc_now(),
        parent_run_id=run.run_id, direction_id=direction.direction_id,
        gap_id=gap.gap_id, gap_family_id=derivation.gap_family_id,
        candidate_id=candidate.candidate_id,
        derivation_id=derivation.derivation_id,
        candidate_snapshot=candidate_snapshot,
        derivation_snapshot=derivation_snapshot,
        direction_snapshot=direction_to_dict(direction), gap_snapshot=gap_to_dict(gap),
        pipeline_version=derivation.pipeline_version,
        schema_version=SELECTED_IDEA_SCHEMA_VERSION,
        candidate_fingerprint=candidate_fingerprint,
        derivation_fingerprint=derivation_fingerprint,
        resolution_source=resolution_source,
        validation_status="LEGACY_CONTEXT" if partial else "COMPLETE",
        validation_notes=tuple(partial),
    )


def commit_idea_selection(
    *, candidate: object, derivation: object, direction: object, gap: object,
    run: ResearchRun, state: object | None = None,
) -> SelectedIdeaContext:
    """Atomically commit a complete Part 2 → Part 3 selection."""
    target = st.session_state if state is None else state
    context = _selection_context(
        candidate=candidate, derivation=derivation, direction=direction,
        gap=gap, run=run,
        active_direction_id=target["selected_direction_id"],
        active_gap_id=target["selected_gap_id"],
    )
    target.update({
        "selected_idea_id": context.candidate_id,
        "selected_candidate_snapshot": context.candidate_snapshot,
        "selected_derivation_snapshot": context.derivation_snapshot,
        "selected_idea_context": context.to_dict(),
        "selected_idea_selection_error": "",
        "selected_idea_selection_version": context.schema_version,
        "current_result_explanation": None,
        "current_result_audit": None,
        "current_audit_build_result": None,
        "current_diagram_specs": [],
    })
    stored = SelectedIdeaContext.from_dict(target["selected_idea_context"])
    if not (
        stored.candidate_id == candidate.candidate_id
        and stored.derivation_id == derivation.derivation_id
        and stored.direction_id == direction.direction_id
        and stored.gap_id == gap.gap_id
        and target["selected_idea_id"] == candidate.candidate_id
    ):
        raise RuntimeError("selected idea state verification failed")
    try:
        if state is not None:
            return context
        memory = ResearchMemory(DEFAULT_DB)
        try:
            memory.save_structural(
                "selected_idea_context", context.selection_id, context,
                model_version=context.pipeline_version,
            )
        finally:
            memory.close()
    except Exception:
        pass  # Session state is authoritative; persistence is best effort.
    return context


def commit_selected_idea_by_id(
    candidate_id: str, state: object | None = None,
) -> SelectedIdeaContext:
    """Resolve, atomically commit, and verify one selected candidate ID."""
    target = st.session_state if state is None else state
    candidates = {
        item.candidate_id: item for item in target["candidate_portfolio"]
    }
    derivations = {
        item.candidate_id: item for item in target["current_idea_portfolio"]
    }
    if candidate_id not in candidates:
        raise ValueError(f"candidate {candidate_id!r} is not in the current portfolio")
    if candidate_id not in derivations:
        raise ValueError(f"candidate {candidate_id!r} has no matching derivation")
    return commit_idea_selection(
        candidate=candidates[candidate_id], derivation=derivations[candidate_id],
        direction=target["selected_direction_snapshot"],
        gap=target["selected_gap"], run=target["current_research_run"],
        state=target,
    )


def validate_selected_idea_state() -> str:
    """Classify selection integrity before Part 3 resolves its snapshots."""
    if st.session_state.selected_idea_selection_error:
        return "SELECTION_COMMIT_FAILED"
    raw = st.session_state.selected_idea_context
    if raw is None:
        if st.session_state.selected_idea_id:
            return "RECOVERABLE_ID_ONLY"
        if (st.session_state.candidate_portfolio
                and st.session_state.current_idea_portfolio):
            return "NOT_SELECTED_PORTFOLIO_AVAILABLE"
        return "NOT_SELECTED_NO_PORTFOLIO"
    try:
        context = (
            SelectedIdeaContext.from_dict(raw) if isinstance(raw, dict) else raw
        )
        candidate = candidate_from_dict(context.candidate_snapshot)
        derivation = derivation_from_dict(context.derivation_snapshot)
    except Exception:
        return "SNAPSHOT_INVALID"
    run = st.session_state.current_research_run
    if not run or context.parent_run_id != run.run_id:
        return "RUN_MISMATCH"
    if context.direction_id != st.session_state.selected_direction_id:
        return "DIRECTION_MISMATCH"
    if context.gap_id != st.session_state.selected_gap_id:
        return "GAP_MISMATCH"
    if candidate.candidate_id != derivation.candidate_id:
        return "CANDIDATE_DERIVATION_MISMATCH"
    return context.validation_status


def resolve_selected_idea() -> tuple[object, object, object, object, SelectedIdeaContext] | None:
    """Resolve immutable snapshots first, then upgrade a legacy ID-only state."""
    raw = st.session_state.selected_idea_context
    if raw is not None:
        context = SelectedIdeaContext.from_dict(raw) if isinstance(raw, dict) else raw
        return (
            candidate_from_dict(context.candidate_snapshot),
            derivation_from_dict(context.derivation_snapshot),
            direction_from_dict(context.direction_snapshot),
            gap_from_dict(context.gap_snapshot), context,
        )
    candidate = next((item for item in st.session_state.candidate_portfolio
                      if item.candidate_id == st.session_state.selected_idea_id), None)
    derivation = next((item for item in st.session_state.current_idea_portfolio
                       if item.candidate_id == st.session_state.selected_idea_id), None)
    if not candidate or not derivation:
        return None
    context = _selection_context(
        candidate=candidate, derivation=derivation,
        direction=st.session_state.selected_direction_snapshot,
        gap=st.session_state.selected_gap,
        run=st.session_state.current_research_run,
        active_direction_id=st.session_state.selected_direction_id,
        active_gap_id=st.session_state.selected_gap_id,
        resolution_source="session portfolio recovery",
    )
    st.session_state.update({
        "selected_candidate_snapshot": context.candidate_snapshot,
        "selected_derivation_snapshot": context.derivation_snapshot,
        "selected_idea_context": context.to_dict(),
        "selected_idea_selection_version": context.schema_version,
    })
    return candidate, derivation, st.session_state.selected_direction_snapshot, st.session_state.selected_gap, context


def selected_idea_name() -> str:
    candidate_id = st.session_state.selected_idea_id
    if not candidate_id:
        return "none"
    raw = st.session_state.selected_candidate_snapshot or {}
    return str(raw.get("candidate_name", candidate_id))


def selected_idea_invariant_violations() -> list[str]:
    """Return strict cross-portfolio and selected-context consistency failures."""
    violations = []
    candidate_ids = {
        item.candidate_id for item in st.session_state.candidate_portfolio
    }
    derivation_ids = {
        item.candidate_id for item in st.session_state.current_idea_portfolio
    }
    missing = derivation_ids - candidate_ids
    if missing:
        violations.append(
            "Derivations lack candidates: " + ", ".join(sorted(missing))
        )
    selected = st.session_state.selected_idea_id
    if selected and st.session_state.selected_idea_context is None:
        if selected not in candidate_ids or selected not in derivation_ids:
            violations.append("Selected idea has neither context nor recoverable portfolios.")
    if validate_selected_idea_state() in {"COMPLETE", "LEGACY_CONTEXT"}:
        resolved = resolve_selected_idea()
        if resolved and resolved[0].candidate_id != selected:
            violations.append("Rendered candidate would differ from selected_idea_id.")
    return violations


def render_workflow_status() -> None:
    """Show state facts separately from the page the user is viewing."""
    ideas = st.session_state.current_idea_portfolio
    ready = validate_selected_idea_state() in {"COMPLETE", "LEGACY_CONTEXT"}
    st.subheader("Workflow status / 流程状态")
    selection = st.session_state.primary_idea_selection_record or {}
    columns = st.columns(6)
    columns[0].metric("Research direction", "selected" if st.session_state.selected_direction_id else "not selected")
    columns[1].metric("External evidence", "ready" if st.session_state.current_external_result else "not ready")
    columns[2].metric(
        "Candidate ideas",
        f"{len(ideas)} evaluated internally" if ideas else "0 passed validation",
    )
    columns[3].metric("Primary idea", selected_idea_name())
    columns[4].metric("Selection", "automatic" if selection.get("status") == "SELECTED" else "not available")
    columns[5].metric(
        "Part 3", "ready" if ready else "unavailable — no defensible idea",
    )
    violations = selected_idea_invariant_violations()
    if violations:
        st.error("Selected-idea state invariant failed.")
        with st.expander("Technical details · state invariants"):
            render_bullets(violations)


def selection_error_details(candidate_id: str, exc: BaseException) -> dict[str, str]:
    derivation = next((item for item in st.session_state.current_idea_portfolio
                       if item.candidate_id == candidate_id), None)
    return {
        "Exception type": type(exc).__name__,
        "Message": " ".join(str(exc).split())[:500],
        "Candidate ID": candidate_id,
        "Derivation ID": getattr(derivation, "derivation_id", "not found"),
        "Run ID": getattr(st.session_state.current_research_run, "run_id", "not set"),
        "Direction ID": st.session_state.selected_direction_id or "not set",
        "Gap ID": st.session_state.selected_gap_id or "not set",
    }


def render_primary_idea_summary() -> None:
    """Render the already committed primary idea and optional alternatives."""
    candidates = {
        item.candidate_id: item for item in st.session_state.candidate_portfolio
    }
    derivations = {
        item.candidate_id: item for item in st.session_state.current_idea_portfolio
    }
    record = st.session_state.primary_idea_selection_record or {}
    selected_id = str(record.get("selected_candidate_id", ""))
    if selected_id not in candidates or selected_id not in derivations:
        return
    candidate = candidates[selected_id]
    derivation = derivations[selected_id]
    st.header("Primary idea derived / 已推导主想法")
    render_fields({
        "Title": candidate.candidate_name,
        "Why this idea was selected": record.get("selection_reason", "Selected by deterministic hard-gated ranking."),
        "Starting algorithm": candidate.base_algorithm,
        "Algorithm family": candidate.base_algorithm_family,
        "Change": candidate_modification(candidate),
        "Modification slot": derivation.modification_slot,
        "External mechanism": derivation.mechanism_name,
        "Expected metric effect": candidate.expected_improvement,
        "Main risk": candidate.expected_failure_modes[0]
        if candidate.expected_failure_modes else "unknown",
        "Confidence": record.get("confidence", candidate.confidence),
    })
    if st.button(
        "Continue to explanation / 查看完整解释",
        key="_continue_to_explanation", type="primary",
    ):
        st.session_state.pending_primary_step = PRIMARY_STEPS[2]
        st.session_state.workflow_guidance = ""
        st.rerun()
    alternatives = [
        item for item in record.get("ranking_records", [])
        if item.get("candidate_id") != selected_id
    ]
    if alternatives:
        with st.expander("Other ideas considered / 其他备选想法", expanded=False):
            for item in sorted(
                alternatives,
                key=lambda value: (not value.get("passed_hard_gates"),
                                   value.get("rank") or 999,
                                   value.get("candidate_id", "")),
            ):
                alternative = candidates.get(item.get("candidate_id"))
                if alternative:
                    render_fields({
                        "Title": alternative.candidate_name,
                        "Main advantage": alternative.expected_improvement,
                        "Main weakness": item.get("non_selection_reason")
                        or readable_items(item.get("gate_failures", [])),
                        "Score": item.get("weighted_score", 0),
                    })


def set_external_live_retry() -> None:
    """Explicitly authorize a live retry after a cache-only miss."""
    run = st.session_state.current_research_run
    if not run:
        return
    policy = SearchPolicy.from_dict(run.search_policy or {})
    run.search_policy = SearchPolicy(
        requested_mode="LIVE", sources=policy.sources,
        allow_cache=policy.allow_cache, force_fresh=False,
        allow_offline_fallback=policy.allow_offline_fallback,
        maximum_per_query=policy.maximum_per_query,
        maximum_total=policy.maximum_total,
    ).to_dict()
    for key, value in {
        "current_external_result": None, "external_papers": [],
        "mechanisms": [], "rejected_mechanisms": [], "alignments": [],
        "candidate_portfolio": [], "current_idea_portfolio": [],
        "current_result_explanation": None, "current_diagram_specs": [],
        "current_result_audit": None,
        "current_audit_build_result": None,
    }.items():
        st.session_state[key] = value


def render_compact_run_summary() -> None:
    run = st.session_state.current_research_run
    if not run:
        return
    st.subheader("Research evidence / 研究证据")
    if run.actual_search_mode == "OFFLINE_FIXTURE":
        st.warning(
            "Offline demonstration — bundled papers are not a current "
            "literature review."
        )
    render_openalex_status(run)
    columns = st.columns(4)
    columns[0].metric("Candidate papers", run.candidate_paper_count)
    columns[1].metric(
        "Automatically relevant", run.automatically_relevant_paper_count
    )
    columns[2].metric("Human reviewed", run.human_reviewed_paper_count)
    columns[3].metric("Evidence-bearing", run.evidence_bearing_paper_count)
    st.caption(
        f"Mode: {run.actual_search_mode} · Sources: "
        f"{', '.join(run.sources_attempted) or 'fixture'} · "
        f"Actual years: {run.actual_publication_year_min or '—'}–"
        f"{run.actual_publication_year_max or '—'} · "
        f"Canonical families: {run.canonical_gap_family_count} · "
        f"Promoted directions: {run.promoted_gap_count}"
    )


def openalex_status(run: ResearchRun | None) -> dict[str, object]:
    if not run:
        return {}
    stage = next((
        item for item in reversed(run.stages)
        if item.metadata.get("openalex_rate_limit")
    ), None)
    return dict(stage.metadata.get("openalex_rate_limit", {})) if stage else {}


def render_openalex_status(run: ResearchRun | None) -> None:
    """Render one concise, credential-free OpenAlex state message."""
    state = openalex_status(run)
    if not state:
        return
    if state.get("daily_limit_exhausted"):
        retained_arxiv = next((
            item.unique_returned_count for item in run.source_results
            if item.source == "arxiv"
        ), 0)
        st.warning(
            "OpenAlex request limit reached. "
            f"Successful requests: {state.get('requests_this_run', 0)} · "
            f"Skipped queries: {state.get('skipped_queries', 0)} · "
            f"arXiv papers retained: {retained_arxiv} · "
            f"Reset: {state.get('reset_at') or 'not reported'}."
        )
    elif state.get("authentication_mode") == "ANONYMOUS":
        st.info(
            "OpenAlex is operating with a conservative anonymous request budget."
        )


def render_related_papers(direction: object) -> None:
    papers = {
        paper.paper_id: paper for paper in st.session_state.ml_papers
    }
    gap = next((
        item for item in st.session_state.gaps
        if item.gap_id == direction.selected_gap_id
    ), None)
    excerpts = {
        paper_id: sentence for paper_id, sentence in zip(
            gap.evidence_paper_ids, gap.evidence_sentences
        )
    } if gap else {}
    grouped: dict[str, list[Paper]] = {}
    for paper_id in direction.evidence_paper_ids:
        paper = papers.get(paper_id)
        if paper:
            grouped.setdefault(
                direction.paper_roles.get(paper_id, "foundational context"), []
            ).append(paper)
    if not grouped:
        st.caption("No paper-level record is available for this direction.")
    for role, records in grouped.items():
        st.markdown(f"**{role.title()}**")
        for paper in records:
            st.markdown(
                f"- [{paper.title}]({paper.url or paper.doi or '#'}) "
                f"({paper.year}, {paper.source})  \n"
                f"  Estimated: `{paper.estimated_relevance_label}` · "
                f"Human review: `{paper.reviewed_relevance_label or 'not reviewed'}`  \n"
                f"  Evidence: {excerpts.get(paper.paper_id, 'Connected through the canonical gap family.')}"
            )


def discover_directions_page() -> None:
    st.title("Discover directions / 发现方向")
    st.caption(
        "Find evidence-backed candidate research directions and the papers "
        "that support them."
    )
    with st.form("_direction_search_form"):
        task = st.text_input(
            "What area or task are you interested in?",
            "online learning", key="_purpose_task",
        )
        failure = st.text_input(
            "What problem or failure concerns you?",
            "recurring concept drift with slow recovery", key="_purpose_failure",
        )
        improvement = st.text_input(
            "What kind of improvement matters?",
            "reduce recovery time without excessive memory growth",
            key="_purpose_improvement",
        )
        data_type = st.text_input(
            "What data or application setting is involved?",
            "tabular streams", key="_purpose_data_type",
        )
        years = st.slider(
            "Publication year range", 2018, date.today().year,
            (2022, date.today().year), key="_purpose_years",
        )
        with st.expander("Advanced search settings"):
            use_case = st.text_input(
                "Application", "adaptive decision support",
                key="_purpose_use_case",
            )
            metric = st.text_input(
                "Primary metric", "recovery time", key="_purpose_metric"
            )
            search_mode = st.radio(
                "Search data source",
                ["Live scholarly APIs", "Cached live results",
                 "Offline demonstration fixtures"],
                key="_purpose_search_mode",
            )
            force_fresh = st.checkbox(
                "Force fresh live search", key="_purpose_force_fresh"
            )
            allow_cache = st.checkbox(
                "Allow cache", value=True, key="_purpose_allow_cache"
            )
            allow_fallback = st.checkbox(
                "Allow offline fallback", key="_purpose_allow_offline_fallback"
            )
            openalex = st.checkbox(
                "OpenAlex enabled", value=True, key="_purpose_openalex"
            )
            arxiv = st.checkbox(
                "arXiv enabled", value=True, key="_purpose_arxiv"
            )
            maximum_per_query = st.number_input(
                "Maximum papers per query", 1, 50, 8,
                key="_purpose_max_per_query",
            )
            maximum_total = st.number_input(
                "Maximum total papers", 5, 200, 80,
                key="_purpose_max_total",
            )
        submitted = st.form_submit_button(
            "Find research directions / 寻找研究方向", type="primary"
        )
    if submitted:
        part_started = time.perf_counter()
        progress = st.progress(0, text="1/8 Searching recent ML/DL papers")
        try:
            execute_direction_search(
                task, failure, improvement, data_type, use_case, metric, years,
                search_mode,
                [name for name, enabled in (
                    ("openalex", openalex), ("arxiv", arxiv)
                ) if enabled],
                force_fresh, allow_cache, allow_fallback,
                int(maximum_per_query), int(maximum_total),
            )
            progress.progress(100, text="8/8 Ranking research directions")
            st.session_state.ux_performance["part_1_search_seconds"] = round(
                time.perf_counter() - part_started, 4
            )
        finally:
            progress.empty()
    render_compact_run_summary()
    directions = st.session_state.current_direction_portfolio
    if not directions:
        st.info(
            "Enter a research problem and select “Find research directions.”"
        )
        if st.session_state.exploratory_gap_families:
            with st.expander("Exploratory directions and rejection summary"):
                st.dataframe([{
                    "direction": item.representative_title,
                    "status": item.promotion_status,
                    "reason": "; ".join(item.rejection_reasons),
                } for item in st.session_state.exploratory_gap_families])
        return
    st.header("Promising research directions / 候选研究方向")
    for index, direction in enumerate(directions):
        with st.container(border=True):
            st.subheader(direction.title)
            st.write(direction.plain_language_summary)
            render_fields({
                "Task": direction.task,
                "Failure condition": direction.failure_condition,
                "Algorithm family": direction.affected_algorithm_family,
                "Gap types": ", ".join(direction.gap_types),
                "Why it matters": direction.unresolved_remainder,
                "Primary metric": direction.primary_metric,
                "Evidence papers": direction.evidence_bearing_paper_count,
                "Independent sources": direction.independent_source_count,
                "Known solutions": direction.known_solution_status,
                "Confidence": round(direction.evidence_confidence, 2),
                "Risk": direction.risk_level,
                "Uncertainty": readable_items(direction.uncertainties),
            })
            with st.expander("View related papers / 查看相关论文"):
                render_related_papers(direction)
            st.button(
                "Analyze this direction / 分析这个方向",
                key=f"_select_direction_{index}",
                type="primary",
                on_click=select_direction,
                args=(direction.direction_id,),
            )


def build_current_idea_portfolio(progress_callback: object | None = None) -> None:
    direction = st.session_state.selected_direction_snapshot
    gap = st.session_state.selected_gap
    run = st.session_state.current_research_run
    existing = resolve_current_external_result()
    identity = (run.run_id, direction.direction_id, gap.gap_id)
    if (
        existing and existing.identity() == identity
        and existing.stage_diagnostics.get("search_policy") == run.search_policy
        and st.session_state.current_idea_portfolio
    ):
        existing.reused_from_session = True
        return
    policy = SearchPolicy.from_dict(run.search_policy or {
        "requested_mode": run.requested_search_mode,
        "sources": run.sources_attempted or ["openalex", "arxiv"],
        "allow_cache": run.cache_ttl_seconds > 0,
    })
    result = derive_ideas_for_direction(
        purpose=st.session_state.purpose, direction=direction, gap=gap,
        parent_run=run, search_policy=policy, seed=st.session_state.seed,
        memory_path=DEFAULT_DB,
        fixture_loader=lambda: load_fixture("external_papers.json"),
        progress_callback=progress_callback if callable(progress_callback) else None,
    )
    recovery_used = False
    if not result.portfolio and not st.session_state.automatic_recovery_attempted:
        st.session_state.automatic_recovery_attempted = True
        recovery_used = True
        recovery_policy = SearchPolicy(
            requested_mode=policy.requested_mode,
            sources=policy.sources,
            allow_cache=policy.allow_cache,
            force_fresh=policy.force_fresh or policy.requested_mode.upper() == "LIVE",
            allow_offline_fallback=False,
            maximum_per_query=min(12, policy.maximum_per_query + 2),
            maximum_total=min(100, policy.maximum_total + 20),
        )
        result = derive_ideas_for_direction(
            purpose=st.session_state.purpose, direction=direction, gap=gap,
            parent_run=run, search_policy=recovery_policy,
            seed=st.session_state.seed + 1, memory_path=DEFAULT_DB,
            fixture_loader=lambda: load_fixture("external_papers.json"),
            progress_callback=progress_callback if callable(progress_callback) else None,
        )
    st.session_state.current_external_result = result.external_result.to_dict()
    st.session_state.external_result_rebuild_required = False
    st.session_state.external_papers = result.external_result.papers
    st.session_state.current_external_run = result.external_result.retrieval_run
    st.session_state.mechanisms = result.external_result.mechanisms
    st.session_state.rejected_mechanisms = result.external_result.rejected_mechanisms
    st.session_state.alignments = result.external_result.alignments
    st.session_state.candidate_portfolio = result.portfolio
    st.session_state.direction_families = result.direction_families
    st.session_state.current_idea_portfolio = result.derivations
    selection = select_primary_idea(
        candidates=result.portfolio, derivations=result.derivations,
        direction=direction, gap=gap, parent_run=run,
        automatic_recovery_used=recovery_used,
    )
    st.session_state.primary_idea_selection_record = selection.to_dict()
    if selection.status == "SELECTED":
        commit_idea_selection(
            candidate=selection.selected_candidate,
            derivation=selection.selected_derivation,
            direction=direction, gap=gap, run=run,
        )
    st.session_state.candidate_run_diagnostics = {
        **result.diagnostics,
        "error": "; ".join(result.external_result.errors),
        "warnings": result.external_result.warnings,
        "automatic_recovery_attempted": recovery_used,
        "primary_selection_status": selection.status,
        "candidate_rejection_reasons": selection.rejection_reasons,
    }
    generate_quality_warnings(run)


def readable_items(values: object) -> str:
    """Format structured sequences without exposing Python repr syntax."""
    if values is None:
        return "Not recorded"
    if isinstance(values, (list, tuple, set)):
        cleaned = [str(item).strip() for item in values if str(item).strip()]
        return "; ".join(cleaned) if cleaned else "None recorded"
    return str(getattr(values, "value", values))


def render_bullets(values: object, empty: str = "None recorded") -> None:
    items = list(values) if isinstance(values, (list, tuple, set)) else [values]
    cleaned = [str(item).strip() for item in items if item and str(item).strip()]
    if not cleaned:
        st.write(empty)
        return
    for item in cleaned:
        st.markdown(f"- {item}")


def render_fields(values: dict[str, object]) -> None:
    """Render readable fields without exposing a Python/JSON representation."""
    for label, value in values.items():
        st.markdown(f"**{label}:** {readable_items(value)}")


def format_legacy_score(value: float | None) -> float | str:
    return round(value, 3) if value is not None else "Not recorded in this legacy result"


def analyze_gap_page() -> None:
    st.title("Analyze the gap / 分析 Gap")
    render_workflow_status()
    direction = st.session_state.selected_direction_snapshot
    if not direction:
        st.info("Select a research direction in Part 1.")
        st.button(
            "Back to directions / 返回研究方向",
            on_click=navigate_to, args=(PRIMARY_STEPS[0],),
        )
        return
    st.button(
        "Back to directions / 返回研究方向",
        on_click=navigate_to, args=(PRIMARY_STEPS[0],),
    )
    if (
        st.session_state.external_result_rebuild_required
        and st.session_state.current_research_run
        and st.session_state.selected_gap
    ):
        st.warning("Stored external evidence was incompatible and is being rebuilt safely.")
        build_current_idea_portfolio()
    st.header("Selected direction / 已选方向")
    render_fields({
        "Direction": direction.title,
        "Problem": direction.plain_language_summary,
        "Evidence papers": direction.evidence_bearing_paper_count,
        "Algorithm family": direction.affected_algorithm_family,
        "Primary metric": direction.primary_metric,
        "Known-solution status": direction.known_solution_status,
        "Confidence": round(direction.evidence_confidence, 2),
    })
    gap = st.session_state.selected_gap
    st.header("What existing research already covers")
    mitigations = gap.known_mitigations or list(direction.current_solution_families)
    render_bullets([
        *mitigations,
        "The retrieved corpus covers the task and observed failure condition.",
        "Coverage completeness depends on available paper metadata.",
    ])
    with st.expander("Technical evidence"):
        st.dataframe([
            asdict(item) for item in st.session_state.coverage_records
        ], use_container_width=True)
    st.header("Gap Analysis / Gap 分析")
    st.subheader("The gap in one sentence")
    st.write(direction.plain_language_summary)
    st.subheader("Paper-stated evidence / 论文直接证据")
    paper_evidence = [
        sentence for sentence, section in zip(
            gap.evidence_sentences, gap.evidence_sections
        ) if section != "purpose_contract"
    ]
    render_bullets(
        paper_evidence,
        "No direct paper-stated sentence; this gap is system-inferred.",
    )
    st.subheader("System inference / 系统推断")
    render_fields({
        "Detection": gap.structural_gap_subtype or gap.detection_method,
        "Inference": f"{gap.failure_type} affects {gap.affected_component}.",
        "Metric": gap.primary_metric,
    })
    st.subheader("Known solutions / 已有解法")
    render_bullets(
        mitigations,
        "No direct mitigation was confirmed in the searched corpus.",
    )
    st.subheader("Unresolved remainder / 尚未解决")
    st.write(gap.unresolved_remainder or direction.unresolved_remainder)
    st.subheader("Uncertainty / 不确定性")
    for uncertainty in direction.uncertainties:
        st.markdown(f"- {uncertainty}")
    if not st.session_state.current_idea_portfolio:
        if st.button(
            "Analyze the gap and derive the idea / 分析 Gap 并推导新想法",
            type="primary", key="_derive_ideas",
            help="Automatically searches external literature, extracts mechanisms, "
                 "tests structural alignment, and builds candidate ideas.",
        ):
            part_started = time.perf_counter()
            progress = st.progress(0, text="1/6 Translating the research gap")
            build_current_idea_portfolio(
                lambda value, label: progress.progress(value, text=label)
            )
            progress.progress(100, text="6/6 Building candidate ideas")
            progress.empty()
            st.session_state.ux_performance[
                "part_2_analysis_seconds"
            ] = round(time.perf_counter() - part_started, 4)
    external = resolve_current_external_result()
    if external:
        st.header("Normalized problem / 规范化问题")
        signature = external.cross_domain_problem_signature
        render_fields({
            "System condition": signature.system_condition,
            "Observed failure": signature.observed_failure,
            "Required capability": signature.desired_capability,
            "Memory requirement": signature.memory_requirement,
            "Resource constraint": signature.resource_constraint,
            "Affected ML slot": signature.affected_ml_slot,
        })
        st.header("Selected external domains / 已选外部领域")
        for selection in external.ranked_domain_selections:
            if selection.selected:
                render_fields({
                    "Domain": selection.domain,
                    "Why selected": readable_items(selection.reasons),
                    "Matched roles": readable_items(selection.matched_problem_roles),
                    "Unmatched required roles": readable_items(selection.unmatched_required_roles),
                    "Problem-topology compatibility": format_legacy_score(selection.problem_topology_compatibility),
                    "Likely mechanism value": format_legacy_score(selection.likely_mechanism_value),
                    "Query specificity": format_legacy_score(selection.query_specificity),
                    "Analogy risk": format_legacy_score(selection.analogy_risk),
                    "Selection score": round(selection.relevance_score, 3),
                    "Analogy limitations": readable_items(selection.missing_correspondence),
                })
        st.header("External search evidence / 外部检索证据")
        retrieval = external.retrieval_run
        if retrieval.actual_search_mode == "OFFLINE_FIXTURE":
            st.warning(
                "OFFLINE DEMONSTRATION — external evidence uses bundled papers "
                "and is not a current literature search."
            )
        render_openalex_status(retrieval)
        render_fields({
            "Actual search mode": retrieval.actual_search_mode,
            "Sources": readable_items(retrieval.sources_attempted),
            "Queries": sum(len(items) for items in external.accepted_queries_by_domain.values()),
            "Papers retrieved": retrieval.raw_paper_count,
            "Papers after deduplication": retrieval.deduplicated_paper_count,
            "External-problem relevant papers": retrieval.automatically_relevant_paper_count,
            "Papers with validated operational mechanisms": len(
                st.session_state.current_research_run.mechanism_bearing_paper_ids
            ),
            "Cache used": "Yes" if retrieval.cache_used else "No",
            "Result origin": "session state" if external.reused_from_session else "new direction-scoped run",
        })
        with st.expander("Technical diagnostics · queries and source status"):
            st.write(external.accepted_queries_by_domain)
            render_fields({
                "Source failures": retrieval.source_failures or "None",
                "Warnings": readable_items(external.warnings),
                "Build schema": "external-discovery-v2",
                "Session schema": st.session_state.session_state_schema_version,
                "Resolution": st.session_state.external_result_resolution,
                "Migration": st.session_state.external_result_migration_message or "None",
            })
    ideas = st.session_state.current_idea_portfolio
    if not ideas:
        diagnostics = st.session_state.candidate_run_diagnostics or {}
        selection = st.session_state.primary_idea_selection_record or {}
        if selection:
            st.error("No defensible primary idea was derived.")
            render_fields({
                "External papers": diagnostics.get("paper_count", 0),
                "Valid mechanisms": diagnostics.get("mechanism_count", 0),
                "Accepted alignments": diagnostics.get("accepted_alignment_count", 0),
                "Draft candidates": len(st.session_state.candidate_portfolio),
                "Selection status": selection.get("status", "FAILED"),
                "Rejection reasons": selection.get("rejection_reasons", {}),
                "Automatic recovery": "attempted" if diagnostics.get("automatic_recovery_attempted") else "not needed",
                "Recovery actions": "Rerun external evidence search; broaden the publication range; choose another direction; or inspect rejected candidates.",
            })
        if diagnostics.get("error"):
            st.error(diagnostics["error"])
            render_fields({
                "Completed stages": readable_items(diagnostics.get("completed_stages", [])),
                "Failed stage": diagnostics.get("failed_stage", "unknown"),
                "Papers obtained": diagnostics.get("paper_count", 0),
                "Mechanisms obtained": diagnostics.get("mechanism_count", 0),
                "Recovery actions": (
                    "Retry live external search; use matching cached evidence; "
                    "choose another direction; or open technical diagnostics."
                ),
            })
            if external and external.rejected_mechanisms:
                with st.expander("Plausible but rejected mechanism details"):
                    st.write(external.rejected_mechanisms)
            if external and external.mechanisms and not external.accepted_alignments:
                st.subheader("Structural alignment rejection matrix")
                st.dataframe([{
                    "Mechanism": item.mechanism_id,
                    "Matched slots": readable_items(item.matched_slots),
                    "Signal/response match": round(item.score, 2),
                    "Conflicts": readable_items(item.conflicts),
                    "Missing information": readable_items(item.missing_information),
                    "Rejection reason": readable_items(item.rejection_reasons),
                } for item in external.alignments], use_container_width=True)
            if external and external.retrieval_run.requested_search_mode == "CACHE":
                st.button(
                    "Run live external search / 实时检索外部证据",
                    key="_external_retry_live",
                    on_click=set_external_live_retry,
                )
        return
    st.header("How new ideas are generated / 新想法如何产生")
    first = ideas[0]
    st.write(
        f"Selected gap → {first.required_capability} → "
        f"{first.original_external_problem} → {first.mechanism_name} → "
        f"{'; '.join(first.structural_correspondences)} → "
        f"{first.modification_slot} → candidate idea"
    )
    st.header("External mechanism options / 外部机制")
    for mechanism in st.session_state.mechanisms[:5]:
        alignment = next((
            item for item in st.session_state.alignments
            if item.mechanism_id == mechanism.mechanism_id
        ), None)
        with st.expander(f"{mechanism.name} · {mechanism.source_domain}"):
            render_fields({
                "Original problem": mechanism.original_problem,
                "Signal": mechanism.observed_signal,
                "State": mechanism.internal_state,
                "Trigger": mechanism.trigger_condition,
                "Response": mechanism.response_rule,
                "Resource constraint": mechanism.resource_constraint,
                "Target": mechanism.equilibrium_or_target,
                "Failure boundary": mechanism.failure_boundary,
                "Structural match": round(alignment.score, 2) if alignment else "not aligned",
                "Analogy limitation": "Structural correspondence only; no literal domain equivalence is assumed.",
            })
    st.header("Structural alignments / 结构对齐")
    for alignment in external.accepted_alignments if external else []:
        render_fields({
            "Mechanism": alignment.mechanism_id,
            "Gap field": gap.failure_type,
            "Mechanism field": next((
                item.response_rule for item in st.session_state.mechanisms
                if item.mechanism_id == alignment.mechanism_id
            ), "not recorded"),
            "Matched structural role": readable_items(alignment.matched_slots),
            "Affected algorithm slot": gap.affected_component,
            "Match strength": round(alignment.score, 2),
            "Conflicts": readable_items(alignment.conflicts),
            "Analogy boundary": "Structural correspondence only; literal equivalence is not assumed.",
        })
    render_primary_idea_summary()


def render_diagram(spec: dict[str, object]) -> None:
    st.subheader(str(spec["title"]))
    try:
        st.graphviz_chart(str(spec["dot"]), use_container_width=True)
    except Exception as exc:
        st.warning(f"Diagram unavailable; text fallback shown. {exc}")
        st.write(spec["fallback"])
    with st.expander("Text fallback"):
        st.write(spec["fallback"])


def explanation_markdown(explanation: object) -> str:
    return "\n\n".join([
        f"# {explanation.title}",
        explanation.one_sentence_conclusion,
        f"## Problem\n{explanation.problem}",
        f"## Proposed change\n{explanation.proposed_change}",
        f"## Expected result\n{explanation.expected_result}",
        "## Supported\n" + "\n".join(f"- {x}" for x in explanation.supported_claims),
        "## Inferred\n" + "\n".join(f"- {x}" for x in explanation.inferred_claims),
        "## Unknown\n" + "\n".join(f"- {x}" for x in explanation.unknowns),
        "## Risks\n" + "\n".join(f"- {x}" for x in explanation.main_risks),
        f"## Minimal experiment\n```json\n{json.dumps(explanation.minimal_experiment, indent=2)}\n```",
    ])


def build_and_persist_current_audit(
    candidate: object, derivation: object,
) -> AuditBuildResult:
    """Build/persist optional auditing without invalidating the core result."""
    capability = load_result_audit_capability(strict=False)
    if not capability.available or not capability.audit_complete_result:
        return AuditBuildResult(
            "UNAVAILABLE", None,
            "Optional result audit unavailable. The main research result is still available.",
            {
                "error_type": capability.error_type,
                "error_message": capability.error_message,
                "module_path": capability.module_path,
                "schema_version": capability.schema_version,
            }, capability.schema_version,
        )
    run = st.session_state.current_research_run
    gap = st.session_state.selected_gap
    if not run or not gap:
        return AuditBuildResult(
            "INCOMPLETE_INPUT", None,
            "The result audit needs a complete run and selected gap.", {},
            capability.schema_version,
        )
    mechanism = next((
        item for item in st.session_state.mechanisms
        if item.mechanism_id == derivation.mechanism_id
    ), None)
    alignment = next((
        item for item in st.session_state.alignments
        if item.mechanism_id == derivation.mechanism_id
        and item.gap_id == gap.gap_id
    ), None)
    if not mechanism or not alignment:
        return AuditBuildResult(
            "INCOMPLETE_INPUT", None,
            "The result audit needs the selected mechanism and alignment.", {},
            capability.schema_version,
        )
    try:
        audit = capability.audit_complete_result(
            purpose=st.session_state.purpose, run=run,
            direction_id=derivation.direction_id,
            gap_family_id=derivation.gap_family_id, gap=gap,
            candidate=candidate, mechanism=mechanism, alignment=alignment,
            papers=[*st.session_state.ml_papers, *st.session_state.external_papers],
            pipeline_version=derivation.pipeline_version,
        )
    except Exception as exc:
        return AuditBuildResult(
            "FAILED", None,
            "Optional result audit failed. The main research result is still available.",
            {"error_type": type(exc).__name__,
             "error_message": " ".join(str(exc).split())[:500]},
            capability.schema_version,
        )
    try:
        memory = ResearchMemory(DEFAULT_DB)
        try:
            memory.save_result_audit(audit)
        finally:
            memory.close()
    except Exception as exc:
        return AuditBuildResult(
            "FAILED", audit,
            "The result audit was built but could not be saved to Research Memory.",
            {"error_type": type(exc).__name__,
             "error_message": " ".join(str(exc).split())[:500]},
            capability.schema_version,
        )
    return AuditBuildResult(
        "COMPLETE", audit, "Multi-angle result audit complete.", {},
        capability.schema_version,
    )


def render_audit_unavailable(build_result: AuditBuildResult) -> None:
    """One concise user message plus fingerprint-rich technical diagnostics."""
    if not st.session_state.audit_unavailable_notice_shown:
        if build_result.status == "UNAVAILABLE":
            st.warning(
                "Optional result audit unavailable. The main research result is still "
                "available. This deployment loaded an incompatible audit module version."
            )
        else:
            st.warning(
                "Optional result audit failed. The main research result is still available."
            )
        st.session_state.audit_unavailable_notice_shown = True
    with st.expander("Technical details · audit capability"):
        info = build_information(SETTINGS.gap_engine_mode)
        st.write({
            "Error type": build_result.technical_error.get("error_type", "unknown"),
            "Sanitized error": build_result.technical_error.get("error_message", "not reported"),
            "Expected audit schema version": build_result.capability_version,
            "Running commit": info["commit_sha"],
            "Source fingerprints": {
                key: value[:8] for key, value in info["source_fingerprints"].items()
            },
            "Recommended action": "Reboot or redeploy the current main commit.",
        })


def render_result_audit(
    audit: object, *, full: bool = False,
    build_result: AuditBuildResult | None = None,
) -> None:
    """Render decision first; keep the complete ten-pass record secondary."""
    capability = load_result_audit_capability(strict=False)
    if not capability.available:
        render_audit_unavailable(build_result or AuditBuildResult(
            "UNAVAILABLE", None, "Optional result audit unavailable.",
            {"error_type": capability.error_type,
             "error_message": capability.error_message},
            capability.schema_version,
        ))
        return
    if not audit:
        st.info("A complete candidate result is required before auditing.")
        return
    if capability.audit_summary:
        capability.audit_summary(audit)
    if str(audit.final_decision).startswith("PASS"):
        st.success(f"Audit decision: {audit.final_decision}")
    else:
        st.warning(f"Audit decision: {audit.final_decision}")
    if full and build_result and build_result.status == "FAILED":
        st.warning(build_result.user_message)
        with st.expander("Technical details · audit persistence"):
            st.write(build_result.technical_error)
    st.dataframe([{
        "Perspective": item.name.replace("_", " ").title(),
        "Score": f"{item.score}/5",
        "Gate": "PASS" if item.passed else "FAIL",
        "Observed evidence": "; ".join(item.observed_evidence),
        "Recommended action": item.recommended_action,
        "SOTA may help": "Yes" if item.state_of_art_might_help else "No",
    } for item in audit.audit_dimensions], use_container_width=True)
    if full:
        st.subheader("Adversarial and counterfactual robustness")
        st.dataframe([{
            "Test": key.replace("_", " ").title(), "Result": value,
        } for key, value in audit.robustness_results.items()],
            use_container_width=True)
        st.subheader("Recommended repairs")
        render_bullets(audit.recommended_repairs)
        with st.expander("Complete immutable audit record"):
            st.json(asdict(audit))


def explain_idea_page() -> None:
    st.title("Explain the idea / 解释新想法")
    render_workflow_status()
    status = validate_selected_idea_state()
    try:
        resolved = resolve_selected_idea() if status in {
            "COMPLETE", "LEGACY_CONTEXT", "RECOVERABLE_ID_ONLY",
        } else None
    except (KeyError, TypeError, ValueError):
        status = "SNAPSHOT_INVALID"
        resolved = None
    if not resolved:
        if status == "NOT_SELECTED_NO_PORTFOLIO":
            st.info(
                "No validated idea is available for explanation. Return to Part 2 "
                "to rerun external evidence search or choose another direction."
            )
        elif status == "SELECTION_COMMIT_FAILED":
            st.error(f"Could not select this idea. Reason: {st.session_state.selected_idea_selection_error}")
        elif status == "CANDIDATE_DERIVATION_MISMATCH":
            st.error(
                "The selected candidate no longer matches its derivation. "
                "Return to Part 2 and rerun automatic idea derivation."
            )
        elif status == "DIRECTION_MISMATCH":
            st.error(
                "The previous idea belongs to a different research direction "
                "and was cleared."
            )
        else:
            st.error(
                "The selected idea could not be restored after the page transition."
            )
            st.button(
                "Restore selected idea", key="restore_selected_idea",
                on_click=navigate_to, args=(PRIMARY_STEPS[1],),
            )
        with st.expander("Technical details · selected idea state"):
            render_fields({
                "Status": status,
                "Selected idea ID": st.session_state.selected_idea_id or "not set",
                "Selection error": st.session_state.selected_idea_selection_error or "none",
                "Run ID": getattr(st.session_state.current_research_run, "run_id", "not set"),
                "Direction ID": st.session_state.selected_direction_id or "not set",
                "Gap ID": st.session_state.selected_gap_id or "not set",
            })
        st.button(
            "Back to gap analysis / 返回 Gap 分析",
            on_click=navigate_to, args=(PRIMARY_STEPS[1],),
        )
        return
    candidate, derivation, direction, gap, selection_context = resolved
    st.button(
        "Back to gap analysis / 返回 Gap 分析",
        on_click=navigate_to, args=(PRIMARY_STEPS[1],),
    )
    if st.session_state.current_result_explanation is None:
        render_started = time.perf_counter()
        diagram_started = time.perf_counter()
        specs = [
            evidence_to_idea_spec(direction, derivation),
            before_after_spec(candidate),
            mechanism_transfer_spec(derivation),
            experiment_spec(asdict(candidate.minimal_experiment)),
        ]
        st.session_state.ux_performance["diagram_generation_seconds"] = round(
            time.perf_counter() - diagram_started, 4
        )
        st.session_state.current_diagram_specs = specs
        st.session_state.current_result_explanation = build_idea_explanation(
            st.session_state.purpose, direction, derivation, candidate, specs
        )
        audit_build = build_and_persist_current_audit(
            candidate, derivation
        )
        st.session_state.current_audit_build_result = audit_build
        st.session_state.current_result_audit = audit_build.audit
        st.session_state.ux_performance["part_3_render_seconds"] = round(
            time.perf_counter() - render_started, 4
        )
    explanation = st.session_state.current_result_explanation
    st.header(explanation.title)
    st.success(explanation.one_sentence_conclusion)
    st.header("Problem / 问题")
    st.write(explanation.problem)
    st.header("Current behavior / 当前做法")
    st.write(explanation.current_behavior)
    st.header("Proposed change / 修改内容")
    render_fields({
        "Exact modification slot": explanation.modification_slot,
        "New state": explanation.new_state_variables,
        "Trigger": explanation.new_trigger,
        "Rule": explanation.new_rule,
        "Information available at inference": explanation.inference_information,
    })
    st.header("Expected result / 预期结果")
    st.write(explanation.expected_result)
    st.header("BEFORE → CHANGE → EXPECTED RESULT")
    render_fields({
        "BEFORE": explanation.current_behavior,
        "CHANGE": explanation.proposed_change,
        "EXPECTED RESULT": explanation.expected_result,
    })
    st.info(
        f"Exact modification slot: **{explanation.modification_slot}**"
    )
    st.header("Why it might work / 为什么可能有效")
    st.write(explanation.causal_hypothesis)
    for spec in st.session_state.current_diagram_specs:
        render_diagram(spec)
    st.header("What could go wrong / 可能失败的地方")
    render_bullets(
        explanation.main_risks,
        "Failure modes remain insufficiently characterized.",
    )
    audit = st.session_state.current_result_audit
    audit_build = st.session_state.current_audit_build_result
    if audit:
        st.header("Critical review / 批判性审查")
        critique = audit.self_critique
        render_fields({
            "Audit decision": audit.final_decision,
            "Strongest reason to believe": critique.get("strongest_reason_to_believe"),
            "Strongest reason to reject": critique.get("strongest_reason_to_reject"),
            "Most likely duplicate": critique.get("most_likely_duplicate"),
            "Most fragile evidence": critique.get("most_fragile_evidence_link"),
            "Most uncertain mapping": critique.get("most_uncertain_mapping"),
            "Fastest invalidation experiment": critique.get("fastest_invalidation_experiment"),
        })
    elif audit_build and audit_build.status in {"UNAVAILABLE", "FAILED"}:
        render_audit_unavailable(audit_build)
    st.subheader("What is supported")
    render_bullets(explanation.supported_claims)
    st.subheader("What is inferred")
    render_bullets(explanation.inferred_claims)
    st.subheader("What is unknown")
    render_bullets(explanation.unknowns)
    st.subheader("What evidence would change the conclusion")
    render_bullets(explanation.falsification_tests)
    st.header("Potential novelty")
    render_fields({
        "Status": explanation.novelty_status,
        "Closest known methods": readable_items(explanation.closest_known_methods),
        "Qualification": "Novelty remains unverified until a targeted search and expert review.",
    })
    st.header("Closest known methods / 最接近的已有方法")
    render_bullets(
        explanation.closest_known_methods,
        "No close method was established by the searched evidence.",
    )
    experiment = explanation.minimal_experiment
    st.header("Fastest useful experiment / 最小可用实验")
    render_fields({
        "Hypothesis": experiment.get("hypothesis"),
        "Data": experiment.get("dataset"),
        "Stressor": experiment.get("stressor"),
        "Base algorithm": experiment.get("base_algorithm"),
        "Baselines": experiment.get("baselines"),
        "Ablations": experiment.get("ablations"),
        "Metrics": experiment.get("metrics"),
        "Seeds": experiment.get("seeds"),
        "Success rule": experiment.get("success_rule"),
        "Failure rule": experiment.get("failure_rule"),
        "Kill criterion": candidate.kill_criterion or experiment.get("failure_rule"),
    })
    st.header("Supporting papers / 支持论文")
    render_related_papers(direction)
    markdown = explanation_markdown(explanation)
    st.download_button(
        "Export research idea as Markdown", markdown,
        f"{candidate.candidate_id.replace(':', '-')}.md",
    )
    st.download_button(
        "Export structured result as JSON",
        json.dumps(asdict(explanation), indent=2),
        f"{candidate.candidate_id.replace(':', '-')}.json",
    )
    st.download_button(
        "Export diagrams as DOT",
        "\n\n".join(str(item["dot"]) for item in explanation.diagram_specs),
        f"{candidate.candidate_id.replace(':', '-')}-diagrams.dot",
    )
    st.download_button(
        "Export minimal experiment as Markdown",
        experiment_to_markdown(candidate.minimal_experiment),
        f"{candidate.candidate_id.replace(':', '-')}-experiment.md",
    )
    with st.expander("Technical details · Raw JSON"):
        st.json(asdict(explanation))
    with st.expander("Technical details · Selected idea state"):
        render_fields({
            "Selected idea ID": selection_context.candidate_id,
            "Candidate ID": selection_context.candidate_id,
            "Derivation ID": selection_context.derivation_id,
            "Parent run ID": selection_context.parent_run_id,
            "Direction ID": selection_context.direction_id,
            "Gap ID": selection_context.gap_id,
            "Selection timestamp": selection_context.selected_at_utc,
            "Selection schema": selection_context.schema_version,
            "Pipeline version": selection_context.pipeline_version,
            "Candidate fingerprint": selection_context.candidate_fingerprint,
            "Derivation fingerprint": selection_context.derivation_fingerprint,
            "Resolution source": selection_context.resolution_source,
            "Validation status": validate_selected_idea_state(),
        })


def research_tools_panel() -> None:
    tool = st.session_state.get("_research_tool", "None")
    if tool == "None":
        return
    st.divider()
    st.header(f"Research Tools / 研究工具 · {tool}")
    if tool == "Research run provenance":
        render_research_run(st.session_state.current_research_run, "ResearchRun")
        with st.expander("Raw ResearchRun JSON"):
            run = st.session_state.current_research_run
            st.json(run.to_dict() if run else {})
    elif tool == "Full retrieval diagnostics":
        render_search_diagnostics(st.session_state.ml_search_diagnostics)
    elif tool == "Coverage and evidence audit":
        gap_radar_page()
    elif tool == "Structural alignment audit":
        alignment_page()
    elif tool == "Multi-angle result audit":
        render_result_audit(
            st.session_state.current_result_audit, full=True,
            build_result=st.session_state.current_audit_build_result,
        )
        memory = ResearchMemory(DEFAULT_DB)
        try:
            previous = memory.result_audits(
                st.session_state.selected_idea_id
            )
        finally:
            memory.close()
        if len(previous) > 1:
            st.subheader("Pipeline-version history")
            st.dataframe([{
                "Audit": item["payload"].get("audit_id"),
                "Pipeline": item["payload"].get("pipeline_version"),
                "Commit": item["payload"].get("commit_sha"),
                "Decision": item["payload"].get("final_decision"),
                "Timestamp": item["payload"].get("audit_timestamp"),
            } for item in previous], use_container_width=True)
    elif tool == "Quality Evaluation":
        quality_evaluation_panel()
    elif tool == "Annotation tools":
        annotation_tool()
    elif tool == "Research memory":
        memory_page()
    elif tool == "Build information":
        import importlib.util
        info = build_information(SETTINGS.gap_engine_mode)
        capability = load_result_audit_capability(strict=False)
        st.subheader("Startup capability health")
        st.dataframe([
            {"Capability": "Core three-part workflow", "Status": "Available"},
            {"Capability": "Live paper retrieval", "Status": (
                "Available" if importlib.util.find_spec("retrieval_service") else "Unavailable"
            )},
            {"Capability": "External discovery", "Status": (
                "Available" if importlib.util.find_spec("external_discovery_pipeline") else "Unavailable"
            )},
            {"Capability": "Result explanation", "Status": "Available"},
            {"Capability": "Multi-angle result audit", "Status": (
                "Available" if capability.available else "Unavailable"
            )},
            {"Capability": "Quality evaluation", "Status": (
                "Available" if importlib.util.find_spec("evaluation.run_benchmark") else "Unavailable"
            )},
            {"Capability": "SPECTER2", "Status": (
                "Available" if SETTINGS.enable_specter2 else "Disabled"
            )},
            {"Capability": "SciBERT classifier", "Status": (
                "Experimental" if SETTINGS.enable_scibert else "Disabled"
            )},
        ], use_container_width=True)
        st.subheader("Build identity")
        st.write({
            "Application version": info["application_version"],
            "Running commit": info["commit_sha"],
            "Build timestamp": info["build_timestamp"],
            "Python": info["python_version"],
            "Pipeline version": info["pipeline_version"],
            "UX schema version": info["ux_schema_version"],
            "Run-model schema": info["run_model_schema_version"],
            "Evaluation schema": info["evaluation_schema_version"],
            "Engine mode": info["engine_mode"],
            "Measured workflow timings": st.session_state.ux_performance,
        })
        st.subheader("Source fingerprints")
        st.dataframe([{
            "Source": name, "SHA-256": fingerprint,
            "Short": fingerprint[:8],
        } for name, fingerprint in info["source_fingerprints"].items()],
            use_container_width=True)
        if not capability.available:
            with st.expander("Audit capability diagnostic"):
                st.write({
                    "Error type": capability.error_type,
                    "Sanitized error": capability.error_message,
                    "Module path": capability.module_path,
                    "Expected schema": capability.schema_version,
                    "Recommended action": "Reboot or redeploy the current main commit.",
                })


def main() -> None:
    st.set_page_config(page_title="Purpose-Driven Algorithm Discovery", layout="wide")
    initialize_state()
    pending = st.session_state.pending_primary_step
    if pending:
        st.session_state["_primary_step"] = pending
        st.session_state.active_primary_step = pending
        st.session_state.pending_primary_step = ""
    page = sidebar()
    if page == PRIMARY_STEPS[2] and validate_selected_idea_state() not in {
        "COMPLETE", "LEGACY_CONTEXT", "RECOVERABLE_ID_ONLY",
    }:
        fallback = PRIMARY_STEPS[1] if st.session_state.selected_direction_id else PRIMARY_STEPS[0]
        st.session_state.pending_primary_step = fallback
        st.session_state.workflow_guidance = (
            "No validated primary idea is available. Run Part 2 analysis first."
            if fallback == PRIMARY_STEPS[1]
            else "Select a research direction before opening Part 3."
        )
        st.rerun()
    handlers = [
        discover_directions_page, analyze_gap_page, explain_idea_page,
    ]
    if st.session_state.workflow_guidance:
        st.warning(st.session_state.workflow_guidance)
        st.session_state.workflow_guidance = ""
    handlers[PRIMARY_STEPS.index(page)]()
    info = build_information(SETTINGS.gap_engine_mode)
    st.caption(
        f"Running build: {info['commit_sha'][:8]} · "
        f"app.py {info['source_fingerprints'].get('app.py', 'missing')[:8]}"
    )
    research_tools_panel()
    if st.session_state.ml_papers:
        with st.sidebar.expander("Trend radar"):
            st.json(trend_indicators(st.session_state.ml_papers + st.session_state.external_papers))


if __name__ == "__main__":
    main()
