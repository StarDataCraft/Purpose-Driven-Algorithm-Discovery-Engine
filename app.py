"""Thin Streamlit UI for the no-LLM purpose-driven discovery pipeline."""

from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

import streamlit as st

from algorithm_library import load_algorithm_library
from annotation_schema import (
    SentenceAnnotation, annotations_csv, annotations_jsonl, load_annotations,
)
from alignment import align
from assumption_analysis import (
    detect_assumption_mismatches, extract_observed_conditions,
    load_assumption_registry,
)
from config import DEFAULT_DB, FIXTURE_DIR
from config import SETTINGS
from contradiction_analysis import detect_contradictory_evidence
from coverage_analysis import (
    coverage_matrix, detect_coverage_gaps, extract_coverage_records,
)
from direction_families import create_direction_families
from gap_mining import corpus_summary, mine_gaps
from io_utils import experiment_to_markdown, records_to_csv, to_json
from mechanism_mining import cross_domain_only, extract_mechanisms
from known_solution_analysis import assess_known_solutions
from models import Paper, PurposeContract
from paper_fetchers import (
    FetchDiagnostics,
    deduplicate_papers,
    fetch_papers_cached_detailed,
)
from hybrid_retrieval import hybrid_rerank, scientific_query_text
from paper_clustering import cluster_papers
from portfolio import quality_diversity_portfolio
from query_generation import generate_external_queries, generate_ml_queries
from research_memory import ResearchMemory
from scientific_embeddings import select_embedding_backend
from search_engine import search_candidates
from signatures import load_mechanism_seeds
from trend_analysis import trend_indicators
from text_processing import split_sentences
from weak_supervision import GapLabel, label_sentence

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
        "engine_diagnostics": {
            "requested_mode": SETTINGS.gap_engine_mode,
            "active_mode": "lightweight",
            "model_failures": [],
        },
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def analyze_structural_evidence(papers: list[Paper], purpose: PurposeContract) -> None:
    """Populate Phase 1 records used by the radar without changing downstream gaps."""
    started = time.perf_counter()
    records = extract_coverage_records(papers, purpose)
    st.session_state.coverage_records = records
    st.session_state.coverage_gaps = detect_coverage_gaps(
        records, purpose, SETTINGS.minimum_coverage_support,
        SETTINGS.maximum_unknown_ratio,
    )
    conditions = extract_observed_conditions(papers, purpose)
    used = {
        item for record in records
        for item in (record.algorithm, record.algorithm_family)
        if item != "UNKNOWN"
    }
    st.session_state.assumption_mismatches = detect_assumption_mismatches(
        load_assumption_registry(), conditions, used, purpose
    )
    st.session_state.contradictory_gaps = detect_contradictory_evidence(
        papers, records
    )
    st.session_state.known_solution_results = {
        gap.gap_id: assess_known_solutions(gap, papers)
        for gap in st.session_state.gaps
        if gap.structural_gap_subtype
    }
    for gap in st.session_state.gaps:
        result = st.session_state.known_solution_results.get(gap.gap_id)
        if result:
            gap.known_mitigations = result.mitigating_methods
            gap.unresolved_remainder = result.unresolved_remainder
    if not papers:
        st.session_state.research_clusters = []
        return
    failures = st.session_state.engine_diagnostics["model_failures"]
    backend = select_embedding_backend(
        SETTINGS.gap_engine_mode, SETTINGS.enable_specter2, failures
    )
    try:
        embeddings = backend.embed_documents(
            papers[:SETTINGS.transformer_max_papers]
        )
        st.session_state.research_clusters = cluster_papers(
            papers[:len(embeddings)], embeddings, records[:len(embeddings)],
            SETTINGS.clustering_threshold,
        )
        info = backend.model_info()
        active = (
            SETTINGS.gap_engine_mode if info.backend == "specter2"
            else "lightweight"
        )
        st.session_state.engine_diagnostics.update({
            "active_mode": active,
            "embedding_model": info.model_name,
            "embedding_version": info.model_version,
            "dense_reranking": info.backend == "specter2",
            "sparse_reranking": True,
            "papers_processed": len(embeddings),
            "papers_truncated": len(papers) > SETTINGS.transformer_max_papers,
            "sentences_processed": min(
                SETTINGS.transformer_max_sentences,
                sum(len(split_sentences(
                    " ".join([paper.abstract, *paper.sections.values()])
                )) for paper in papers),
            ),
            "paper_processing_seconds": round(time.perf_counter() - started, 4),
            "estimated_memory_tier": (
                "high" if info.backend == "specter2" else "low"
            ),
        })
    except Exception as exc:
        failures.append(f"clustering fallback: {type(exc).__name__}: {exc}")
        st.session_state.research_clusters = []


def rerank_retrieved_papers(
    papers: list[Paper], purpose: PurposeContract, algorithm: str
) -> list[Paper]:
    """Apply sparse-only or hybrid local reranking and preserve components."""
    if not papers:
        st.session_state.retrieval_scores = []
        st.session_state.engine_diagnostics.update({
            "active_mode": "lightweight", "retrieval_method": "SPARSE ONLY",
            "sparse_reranking": False, "dense_reranking": False,
        })
        return []
    failures = st.session_state.engine_diagnostics["model_failures"]
    backend = select_embedding_backend(
        SETTINGS.gap_engine_mode, SETTINGS.enable_specter2, failures
    )
    dense = backend if backend.model_info().backend == "specter2" else None
    lexical_queries = generate_ml_queries(purpose, algorithm)
    semantic_query = scientific_query_text(
        purpose.task, purpose.current_failure, algorithm, purpose.data_type,
        purpose.desired_improvement, purpose.primary_metric,
        purpose.deployment_environment,
    )
    try:
        ranked, scores = hybrid_rerank(
            papers, " ".join(lexical_queries), semantic_query, dense
        )
    except Exception as exc:
        failures.append(f"hybrid retrieval fallback: {type(exc).__name__}: {exc}")
        ranked, scores = hybrid_rerank(
            papers, " ".join(lexical_queries), semantic_query, None
        )
        dense = None
    st.session_state.retrieval_scores = scores
    st.session_state.engine_diagnostics.update({
        "active_mode": SETTINGS.gap_engine_mode if dense else "lightweight",
        "retrieval_method": "HYBRID SPECTER2" if dense else (
            "HYBRID FALLBACK" if failures else "SPARSE ONLY"
        ),
        "sparse_query": lexical_queries,
        "semantic_query": semantic_query,
        "sparse_reranking": True,
        "dense_reranking": bool(dense),
    })
    return ranked


def navigate_to(page: str) -> None:
    """Update the sidebar widget through a pre-rerun button callback."""
    st.session_state["_workflow_page"] = page


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
    return st.sidebar.radio("Workflow", PAGES, key="_workflow_page")


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
            "Affected algorithm",
            sorted(load_algorithm_library()),
            key="_purpose_algorithm",
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
        offline = st.checkbox(
            "Use bundled offline evidence (reproducible demo)",
            value=True,
            key="_purpose_offline",
        )
        force_fresh = st.checkbox(
            "Force fresh search (bypass local cache)",
            value=False,
            key="_purpose_force_fresh",
            help="Applies only to live mode. API rate limits and retry delays remain active.",
        )
        submitted = st.form_submit_button(
            "Discover ML/DL gaps", type="primary"
        )
    if submitted:
        record = load_algorithm_library()[algorithm]
        purpose = PurposeContract(
            purpose_id=f"purpose:{uuid4().hex[:10]}",
            mode="user" if mode.startswith("User") else "gap_radar",
            use_case=use_case, task=task, data_type=data_type, current_failure=failure,
            desired_improvement=improvement, primary_metric=metric,
            secondary_metrics=[x.strip() for x in secondary.split(",") if x.strip()],
            must_not_degrade=[x.strip() for x in preserve.split(",") if x.strip()],
            available_training_information=[x.strip() for x in training.split(",") if x.strip()],
            available_inference_information=[x.strip() for x in inference.split(",") if x.strip()],
            allowed_algorithm_families=[record.family], risk_tolerance=risk,
            preferred_candidate_scale=scale, publication_window=years,
        )
        st.session_state.purpose = purpose
        queries = generate_ml_queries(purpose, record.name)
        if offline:
            papers, failures = load_fixture("ml_papers.json"), {}
            diagnostics = offline_diagnostics(
                "data/offline_fixtures/ml_papers.json", papers, queries, years
            )
        else:
            papers, diagnostics = fetch_papers_cached_detailed(
                " OR ".join(queries[:3]),
                ["openalex", "arxiv"],
                30,
                *years,
                force_fresh=force_fresh,
            )
            failures = diagnostics.source_failures
        papers = rerank_retrieved_papers(papers, purpose, record.name)
        st.session_state.ml_papers = papers
        st.session_state.ml_search_diagnostics = diagnostics
        st.session_state.fetch_failures = failures
        st.session_state.gaps = mine_gaps(papers, purpose)
        analyze_structural_evidence(papers, purpose)
        st.success(f"Mined {len(st.session_state.gaps)} gap records from {len(papers)} papers.")
    render_search_diagnostics(
        st.session_state.ml_search_diagnostics, "Latest ML/DL paper search"
    )


def gap_radar_page() -> None:
    st.title("Latest ML/DL gap radar")
    st.info(
        f"Gap engine mode: {st.session_state.engine_diagnostics['active_mode'].upper()} · "
        f"requested: {st.session_state.engine_diagnostics['requested_mode'].upper()}"
    )
    gaps = st.session_state.gaps
    if not gaps:
        st.info("Create a purpose contract and discover gaps first.")
        return
    render_search_diagnostics(
        st.session_state.ml_search_diagnostics, "ML/DL paper search provenance"
    )
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
        st.session_state.selected_gap = labels[chosen]
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
    queries = generate_external_queries(gap)
    st.session_state.external_queries = queries
    st.json(queries)
    offline = st.checkbox(
        "Use bundled external evidence", value=True, key="_mechanism_offline"
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
        papers = load_fixture("external_papers.json") if offline else []
        failures = {}
        diagnostic_runs: list[FetchDiagnostics] = []
        if not offline:
            for domain, domain_queries in queries.items():
                fetched, run_diagnostics = fetch_papers_cached_detailed(
                    domain_queries[0],
                    ["openalex", "arxiv"],
                    6,
                    *st.session_state.purpose.publication_window,
                    force_fresh=force_fresh,
                )
                for paper in fetched:
                    paper.domain = domain
                papers.extend(fetched)
                run_diagnostics.source_failures = {
                    f"{domain}:{key}": value
                    for key, value in run_diagnostics.source_failures.items()
                }
                diagnostic_runs.append(run_diagnostics)
                failures.update(run_diagnostics.source_failures)
            papers = deduplicate_papers(papers)
        mechanisms, rejected = extract_mechanisms(papers)
        mechanism_fallback = not mechanisms
        if not mechanisms:
            mechanisms = load_mechanism_seeds()
        if offline:
            diagnostics = offline_diagnostics(
                "data/offline_fixtures/external_papers.json",
                papers,
                [query for domain_queries in queries.values() for query in domain_queries],
                st.session_state.purpose.publication_window,
            )
            diagnostics.fallback_occurred = mechanism_fallback
            diagnostics.fallback_reason = (
                "No mechanism was extracted; curated mechanism seeds were used."
                if mechanism_fallback else ""
            )
        else:
            diagnostics = combine_diagnostics(
                diagnostic_runs,
                len(papers),
                mechanism_fallback,
                "No mechanism was extracted; curated mechanism seeds were used."
                if mechanism_fallback else "",
            )
        st.session_state.external_papers = papers
        st.session_state.external_search_diagnostics = diagnostics
        st.session_state.mechanisms = cross_domain_only(mechanisms)
        st.session_state.rejected_mechanisms = rejected
        st.session_state.fetch_failures.update(failures)
    render_search_diagnostics(
        st.session_state.external_search_diagnostics,
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
    families = create_direction_families(portfolio)
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
        papers = load_fixture("ml_papers.json")
        papers = rerank_retrieved_papers(papers, purpose, "purpose-selected algorithm")
        st.session_state.ml_papers = papers
        queries = generate_ml_queries(purpose)
        st.session_state.ml_search_diagnostics = offline_diagnostics(
            "data/offline_fixtures/ml_papers.json",
            papers,
            queries,
            purpose.publication_window,
        )
        st.session_state.gaps = mine_gaps(papers, purpose)
        analyze_structural_evidence(papers, purpose)
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
        st.success("Saved gaps, mechanisms, families, candidates, and failures.")
    tabs = st.tabs(["Gaps", "Mechanisms", "Families", "Candidates", "Failures"])
    for tab, kind in zip(tabs[:4], ["gap", "mechanism", "direction_family", "candidate"]):
        tab.json(memory.list(kind))
    tabs[4].json(memory.failures())
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
    if st.session_state.ml_papers:
        with st.sidebar.expander("Trend radar"):
            st.json(trend_indicators(st.session_state.ml_papers + st.session_state.external_papers))
    if st.session_state.fetch_failures:
        st.sidebar.warning("Partial source failures occurred; available results remain usable.")
        st.sidebar.json(st.session_state.fetch_failures)


if __name__ == "__main__":
    main()
