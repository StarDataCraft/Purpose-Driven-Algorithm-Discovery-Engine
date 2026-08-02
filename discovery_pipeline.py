"""Canonical production orchestration for structural gap discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import Counter
import time
from typing import Callable

from app_settings import SETTINGS, Settings
from assumption_analysis import (
    AssumptionMismatch, detect_assumption_mismatches, purpose_condition_types,
)
from assumption_analysis import extract_observed_conditions, load_assumption_registry
from assumption_analysis import mismatch_to_signature
from contradiction_analysis import ContradictoryEvidenceGap
from contradiction_analysis import contradiction_to_signature, detect_contradictory_evidence
from coverage_analysis import CoverageGap, CoverageRecord, coverage_gap_to_signature
from coverage_analysis import detect_coverage_gaps
from coverage_analysis import extract_coverage_records
from gap_mining import aggregate_gaps, mine_explicit_gaps
from gap_consolidation import GapConsolidationResult, consolidate_gaps
from hybrid_retrieval import RetrievalScore, hybrid_rerank, scientific_query_text
from known_solution_analysis import KnownSolutionResult, assess_known_solutions
from models import GapSignature, Paper, PurposeContract
from paper_clustering import ResearchCluster, cluster_papers
from query_generation import generate_ml_queries
from scientific_embeddings import ScientificEmbeddingBackend
from scientific_embeddings import select_embedding_backend
from semantic_gap_aggregation import CanonicalGapFamily, aggregate_semantic_gaps
from text_processing import split_sentences


@dataclass
class StructuralDiscoveryResult:
    """All auditable products of one production discovery run."""

    papers: list[Paper]
    gaps: list[GapSignature]
    retrieval_scores: list[RetrievalScore]
    coverage_records: list[CoverageRecord]
    coverage_gaps: list[CoverageGap]
    assumption_mismatches: list[AssumptionMismatch]
    contradictions: list[ContradictoryEvidenceGap]
    research_clusters: list[ResearchCluster]
    semantic_gap_families: list[CanonicalGapFamily]
    known_solution_results: dict[str, KnownSolutionResult]
    consolidation: GapConsolidationResult
    diagnostics: dict[str, object] = field(default_factory=dict)


BackendSelector = Callable[..., ScientificEmbeddingBackend]


def discover_structural_gaps(
    papers: list[Paper],
    purpose: PurposeContract,
    algorithm: str = "purpose-selected algorithm",
    *,
    settings: Settings = SETTINGS,
    backend_selector: BackendSelector = select_embedding_backend,
) -> StructuralDiscoveryResult:
    """Run the complete retrieval-to-ranking structural discovery call graph."""
    started = time.perf_counter()
    failures: list[str] = []
    backend = backend_selector(
        settings.gap_engine_mode, settings.enable_specter2, failures
    )
    backend_info = backend.model_info()
    dense = backend if backend_info.backend == "specter2" else None
    lexical_queries = generate_ml_queries(purpose, algorithm)
    semantic_query = scientific_query_text(
        purpose.task, purpose.current_failure, algorithm, purpose.data_type,
        purpose.desired_improvement, purpose.primary_metric,
        purpose.deployment_environment,
    )

    rerank_started = time.perf_counter()
    try:
        ranked_papers, retrieval_scores = hybrid_rerank(
            papers, " ".join(lexical_queries), semantic_query, dense
        ) if papers else ([], [])
    except Exception as exc:
        failures.append(
            f"hybrid retrieval fallback: {type(exc).__name__}: {exc}"
        )
        ranked_papers, retrieval_scores = hybrid_rerank(
            papers, " ".join(lexical_queries), semantic_query, None
        ) if papers else ([], [])
        dense = None
    scores_by_paper = {score.paper_id: score for score in retrieval_scores}
    for paper in ranked_papers:
        score = scores_by_paper.get(paper.paper_id)
        if score:
            paper.sparse_score = score.sparse_score
            paper.dense_score = score.dense_score
            paper.hybrid_score = score.fusion_score
    rerank_seconds = time.perf_counter() - rerank_started

    limited_papers = ranked_papers[:settings.transformer_max_papers]
    extraction_started = time.perf_counter()
    records = extract_coverage_records(limited_papers, purpose)
    coverage_gaps = detect_coverage_gaps(
        records, purpose, settings.minimum_coverage_support,
        settings.maximum_unknown_ratio,
    )
    conditions = extract_observed_conditions(limited_papers, purpose)
    used_algorithms = {
        item for record in records
        for item in (record.algorithm, record.algorithm_family)
        if item != "UNKNOWN"
    }
    active_conditions = purpose_condition_types(purpose)
    mismatches = detect_assumption_mismatches(
        load_assumption_registry(), [
            item for item in conditions
            if item.condition_type in active_conditions
        ], used_algorithms, purpose,
    )

    explicit = mine_explicit_gaps(limited_papers, purpose)
    repeated = aggregate_gaps(explicit)
    for gap in explicit:
        gap.detection_method = "section_aware_cue_rules"
        gap.model_mode = settings.gap_engine_mode
    for gap in repeated:
        gap.structural_gap_subtype = "repeated"
        gap.detection_method = "structured_repetition"
        gap.model_mode = settings.gap_engine_mode
    contradictions = detect_contradictory_evidence(limited_papers, records)
    gaps = [
        *explicit,
        *repeated,
        *(coverage_gap_to_signature(item, purpose) for item in coverage_gaps),
        *(mismatch_to_signature(item, purpose) for item in mismatches),
        *(contradiction_to_signature(item, purpose) for item in contradictions),
    ]
    extraction_seconds = time.perf_counter() - extraction_started

    clusters: list[ResearchCluster] = []
    semantic_families: list[CanonicalGapFamily] = []
    clustering_started = time.perf_counter()
    try:
        paper_embeddings = backend.embed_documents(limited_papers) if limited_papers else []
        clusters = cluster_papers(
            limited_papers, paper_embeddings, records, settings.clustering_threshold
        ) if limited_papers else []
        if gaps:
            from sklearn.feature_extraction.text import TfidfVectorizer

            gap_embeddings = TfidfVectorizer(
                stop_words="english", ngram_range=(1, 2)
            ).fit_transform([
                " ".join([
                    gap.title, gap.failure_type, gap.affected_component,
                    *gap.evidence_sentences,
                ])
                for gap in gaps
            ]).toarray()
            semantic_families = aggregate_semantic_gaps(
                gaps, gap_embeddings, settings.semantic_deduplication_threshold
            )
    except Exception as exc:
        failures.append(f"clustering fallback: {type(exc).__name__}: {exc}")
    clustering_seconds = time.perf_counter() - clustering_started

    known_started = time.perf_counter()
    known_solutions = {
        gap.gap_id: assess_known_solutions(gap, limited_papers)
        for gap in gaps
    }
    for gap in gaps:
        result = known_solutions.get(gap.gap_id)
        if result:
            gap.known_mitigations = result.mitigating_methods
            gap.unresolved_remainder = result.unresolved_remainder
    known_seconds = time.perf_counter() - known_started

    # The final production ranking is deterministic and evidence-first.
    gaps.sort(
        key=lambda gap: (
            gap.confidence_score, gap.structural_gap_score,
            gap.evidence_count, gap.testability_score,
        ),
        reverse=True,
    )
    consolidation_started = time.perf_counter()
    consolidation = consolidate_gaps(gaps, purpose, known_solutions)
    consolidation_seconds = time.perf_counter() - consolidation_started
    active_mode = (
        settings.gap_engine_mode
        if dense is not None and backend_info.backend == "specter2"
        else "lightweight"
    )
    diagnostics: dict[str, object] = {
        "requested_mode": settings.gap_engine_mode,
        "active_mode": active_mode,
        "retrieval_method": (
            "HYBRID SPECTER2" if dense is not None
            else "HYBRID FALLBACK" if failures else "SPARSE ONLY"
        ),
        "sparse_query": lexical_queries,
        "semantic_query": semantic_query,
        "sparse_reranking": bool(papers),
        "dense_reranking": dense is not None,
        "embedding_model": backend_info.model_name,
        "embedding_version": backend_info.model_version,
        "model_failures": failures,
        "fallback_occurred": bool(failures),
        "papers_processed": len(limited_papers),
        "papers_truncated": len(ranked_papers) > len(limited_papers),
        "sentences_processed": min(
            settings.transformer_max_sentences,
            sum(len(split_sentences(
                " ".join([paper.abstract, *paper.sections.values()])
            )) for paper in limited_papers),
        ),
        "paper_processing_seconds": round(time.perf_counter() - started, 4),
        "estimated_memory_tier": "high" if dense is not None else "low",
        "evidence_event_count": len(consolidation.evidence_events),
        "raw_gap_instance_count": len(gaps),
        "canonical_gap_family_count": len(consolidation.families),
        "promoted_gap_count": len(consolidation.promoted),
        "exploratory_gap_count": len(consolidation.exploratory),
        "gap_type_counts": dict(Counter(
            gap.structural_gap_subtype or gap.gap_type for gap in gaps
        )),
        "stage_durations": {
            "paper_reranking": round(rerank_seconds, 4),
            "gap_extraction": round(extraction_seconds, 4),
            "paper_clustering": round(clustering_seconds, 4),
            "known_solution_search": round(known_seconds, 4),
            "gap_consolidation": round(consolidation_seconds, 4),
        },
    }
    return StructuralDiscoveryResult(
        ranked_papers, gaps, retrieval_scores, records, coverage_gaps,
        mismatches, contradictions, clusters, semantic_families,
        known_solutions, consolidation, diagnostics,
    )
