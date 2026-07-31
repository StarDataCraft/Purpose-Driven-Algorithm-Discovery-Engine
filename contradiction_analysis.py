"""Conservative comparable-setting contradictory evidence detection."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from hashlib import sha1

from coverage_analysis import CoverageRecord
from models import GapSignature, Paper, PurposeContract


@dataclass
class ContradictoryEvidenceGap:
    contradiction_id: str
    gap_type: str
    title: str
    task: str
    algorithm_family: str
    failure_condition: str
    metric: str
    supporting_paper_ids: list[str]
    conflicting_paper_ids: list[str]
    supporting_claims: list[str]
    conflicting_claims: list[str]
    comparable_fields: dict[str, str]
    confidence: float
    rejection_flags: list[str] = field(default_factory=list)


POSITIVE = re.compile(r"\b(robust|maintains?|improves?|stable|recovers?)\b", re.I)
NEGATIVE = re.compile(r"\b(degrades?|fails?|unstable|poor|slow recovery)\b", re.I)


def detect_contradictory_evidence(
    papers: list[Paper], records: list[CoverageRecord], minimum_compatibility: int = 3
) -> list[ContradictoryEvidenceGap]:
    by_id = {record.paper_id: record for record in records}
    output = []
    for index, left in enumerate(papers):
        for right in papers[index + 1:]:
            a, b = by_id[left.paper_id], by_id[right.paper_id]
            fields = {
                "task": a.task if a.task == b.task else "",
                "algorithm_family": a.algorithm_family if a.algorithm_family == b.algorithm_family else "",
                "failure_condition": next(iter(set(a.failure_conditions) & set(b.failure_conditions)), ""),
                "metric": next(iter(set(a.metric_categories) & set(b.metric_categories)), ""),
                "protocol": next(iter(set(a.evaluation_protocols) & set(b.evaluation_protocols)), ""),
            }
            if sum(bool(value) for value in fields.values()) < minimum_compatibility:
                continue
            left_text = f"{left.abstract} {' '.join(left.sections.values())}"
            right_text = f"{right.abstract} {' '.join(right.sections.values())}"
            opposed = (POSITIVE.search(left_text) and NEGATIVE.search(right_text)) or (
                NEGATIVE.search(left_text) and POSITIVE.search(right_text)
            )
            if not opposed:
                continue
            support, conflict = (left, right) if POSITIVE.search(left_text) else (right, left)
            output.append(ContradictoryEvidenceGap(
                contradiction_id="contradiction:" + sha1(
                    f"{left.paper_id}:{right.paper_id}:{fields}".encode()
                ).hexdigest()[:12],
                gap_type="contradictory_evidence",
                title=f"Conflicting {fields['metric']} evidence under {fields['failure_condition']}",
                task=fields["task"], algorithm_family=fields["algorithm_family"],
                failure_condition=fields["failure_condition"], metric=fields["metric"],
                supporting_paper_ids=[support.paper_id],
                conflicting_paper_ids=[conflict.paper_id],
                supporting_claims=[support.abstract], conflicting_claims=[conflict.abstract],
                comparable_fields={key: value for key, value in fields.items() if value},
                confidence=round(.55 + .08 * sum(bool(v) for v in fields.values()), 2),
            ))
    return output


def contradiction_to_signature(gap: ContradictoryEvidenceGap,
                               purpose: PurposeContract) -> GapSignature:
    evidence_ids = gap.supporting_paper_ids + gap.conflicting_paper_ids
    evidence = gap.supporting_claims + gap.conflicting_claims
    return GapSignature(
        gap_id=gap.contradiction_id, title=gap.title, gap_type="structural",
        task=gap.task or purpose.task, application_context=purpose.use_case,
        data_type=purpose.data_type, affected_algorithm="Unspecified",
        affected_algorithm_family=gap.algorithm_family or "unspecified",
        failure_type=gap.failure_condition or "unresolved boundary condition",
        affected_component="model_selection",
        current_method_pattern="conflicting comparable claims",
        observable_failure_signal=f"disagreement in {gap.metric}",
        required_response="run a controlled boundary-condition comparison",
        unresolved_assumptions=["claim applicability boundary"], constraints=[],
        must_preserve=purpose.must_not_degrade, primary_metric=gap.metric or purpose.primary_metric,
        secondary_metrics=purpose.secondary_metrics,
        available_training_information=purpose.available_training_information,
        available_inference_information=purpose.available_inference_information,
        evidence_sentences=evidence, evidence_sections=["cross-paper comparison"] * len(evidence),
        evidence_paper_ids=evidence_ids, evidence_count=len(evidence_ids),
        source_diversity=len(evidence_ids), explicitness_score=.5,
        aggregation_score=.8, structural_gap_score=gap.confidence,
        trend_score=.5, practical_value_score=.8, testability_score=.9,
        confidence_score=gap.confidence, detection_method="comparable_claim_contradiction",
        structural_gap_subtype="contradictory_evidence",
        contradiction_evidence=[
            f"support: {claim}" for claim in gap.supporting_claims
        ] + [f"conflict: {claim}" for claim in gap.conflicting_claims],
        comparison_evidence=[str(gap.comparable_fields)],
        metadata_completeness=min(1.0, len(gap.comparable_fields) / 5),
    )
