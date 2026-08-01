"""Dependency-neutral canonical data contracts for final-result audits."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from evaluation import EVALUATION_SCHEMA_VERSION, RESULT_AUDIT_VERSION


@dataclass
class AuditDimension:
    """One independent, evidence-bearing review of a final result."""

    name: str
    score: int
    passed: bool
    observed_evidence: list[str]
    specific_problems: list[str]
    recommended_action: str
    state_of_art_might_help: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AuditDimension":
        return cls(**value)


@dataclass
class ResultAudit:
    """Canonical versioned audit for one user-visible candidate result."""

    audit_id: str
    run_id: str
    direction_id: str
    gap_family_id: str
    candidate_id: str
    pipeline_version: str
    commit_sha: str
    audit_timestamp: str
    task_name: str
    search_mode: str
    engine_mode: str
    audit_dimensions: list[AuditDimension]
    detected_errors: list[str]
    severity_by_error: dict[str, str]
    supporting_evidence: list[str]
    recommended_repairs: list[str]
    state_of_art_candidates: list[str]
    experiments_run: list[dict[str, Any]]
    adopted_changes: list[str]
    rejected_changes: list[str]
    before_metrics: dict[str, float]
    after_metrics: dict[str, float]
    final_decision: str
    robustness_results: dict[str, str] = field(default_factory=dict)
    self_critique: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ResultAudit":
        payload = dict(value)
        payload["audit_dimensions"] = [
            item if isinstance(item, AuditDimension)
            else AuditDimension.from_dict(item)
            for item in payload.get("audit_dimensions", [])
        ]
        return cls(**payload)
