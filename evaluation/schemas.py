"""Typed annotations, audits, funnels, and reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HumanReview:
    run_id: str
    item_id: str
    item_type: str
    task_id: str
    label: str
    score_components: dict[str, float]
    reviewer: str
    timestamp: str
    notes: str
    pipeline_version: str
    uncertain: bool = False


@dataclass
class ReferencePaper:
    title: str
    year: int
    doi: str
    arxiv_id: str
    task_id: str
    relevance_label: str
    relevance_reason: str
    expected_algorithm_family: str
    expected_failure_condition: str
    expected_metrics: list[str]
    notes: str
    annotator: str
    annotation_date: str


@dataclass
class QueryContribution:
    query: str
    accepted: bool
    query_family: str
    stage: str
    papers_returned: int
    unique_papers_contributed: int
    relevant_papers_contributed: int
    highly_relevant_papers_contributed: int
    duplicate_contribution: int
    average_rank_contribution: float
    source_failures: list[str]
    request_count: int
    elapsed_seconds: float
    quality_labels: list[str] = field(default_factory=list)


@dataclass
class AuditResult:
    item_id: str
    label: str
    reasons: list[str]
    errors: list[str]
    score_components: dict[str, float] = field(default_factory=dict)


@dataclass
class StageFunnel:
    retrieved_papers: int = 0
    relevant_papers: int = 0
    evidence_bearing_papers: int = 0
    valid_gaps: int = 0
    gaps_surviving_known_solution_checks: int = 0
    relevant_external_papers: int = 0
    valid_mechanisms: int = 0
    strong_structural_alignments: int = 0
    candidates_surviving_falsification: int = 0
    human_reviewed_papers: int = 0
    evidence_events: int = 0
    raw_gap_instances: int = 0
    canonical_gap_families: int = 0
    promoted_directions: int = 0
    mechanism_bearing_papers: int = 0
    plausible_structural_alignments: int = 0
    candidate_drafts: int = 0
    final_ideas: int = 0

    def rates(self) -> dict[str, float]:
        values = list(self.__dict__.items())
        return {
            name: round(value / max(1, values[index - 1][1]), 3)
            if index else 1.0
            for index, (name, value) in enumerate(values)
        }


@dataclass
class EvaluationReport:
    task_id: str
    benchmark_version: str
    run_provenance: dict[str, Any]
    retrieval_metrics: dict[str, float]
    reranking_metrics: dict[str, dict[str, float]]
    query_contributions: list[QueryContribution]
    gap_audits: list[AuditResult]
    coverage_audits: list[AuditResult]
    mismatch_audits: list[AuditResult]
    binding_audits: list[AuditResult]
    known_solution_audits: list[AuditResult]
    external_query_audits: list[AuditResult]
    mechanism_audits: list[AuditResult]
    alignment_audits: list[AuditResult]
    candidate_audits: list[AuditResult]
    funnel: StageFunnel
    error_counts: dict[str, int]
    dominant_bottleneck: str
    limitations: list[str]
    before_after: dict[str, Any] = field(default_factory=dict)
