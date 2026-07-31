"""Four-level gap consolidation and conservative promotion gates."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha1
import json
import re

from known_solution_analysis import KnownSolutionResult
from models import GapSignature, PurposeContract


@dataclass
class EvidenceEvent:
    event_id: str
    gap_instance_id: str
    paper_id: str
    sentence: str
    section: str
    evidence_type: str


@dataclass
class CanonicalGapFamily:
    family_id: str
    fingerprint: str
    representative_gap_id: str
    representative_title: str
    plain_language_statement: str
    member_instance_ids: list[str]
    supporting_paper_ids: list[str]
    independent_source_count: int
    algorithm_family_consensus: str
    binding_granularity: str
    field_consensus: dict[str, str]
    field_disagreements: dict[str, list[str]]
    evidence_types: list[str]
    empirical_support_count: int
    abstract_only_count: int
    metadata_completeness: float
    known_mitigations: list[str]
    unresolved_remainder: str
    testability: float
    promotion_status: str
    rejection_reasons: list[str]
    member_gaps: list[GapSignature] = field(default_factory=list, repr=False)


@dataclass
class GapConsolidationResult:
    evidence_events: list[EvidenceEvent]
    raw_instances: list[GapSignature]
    families: list[CanonicalGapFamily]
    promoted: list[CanonicalGapFamily]
    exploratory: list[CanonicalGapFamily]


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _scope(gap: GapSignature) -> str:
    text = " ".join([
        gap.failure_type, gap.required_response, *gap.evidence_sentences
    ]).casefold()
    if "inference" in text or "test time" in text:
        return "inference"
    if "training" in text or "train time" in text:
        return "training"
    return "unspecified"


def _failure_topology(gap: GapSignature) -> str:
    text = gap.failure_type.casefold()
    for label, terms in {
        "recurrence_recovery": ("recurr", "return", "reactivat"),
        "missingness_shift": ("missing", "feature availability", "mnar"),
        "component_lifecycle": ("birth", "death", "split", "merge", "component"),
        "distribution_shift": ("drift", "distribution shift", "regime"),
        "initialization": ("initialization",),
        "calibration": ("calibration",),
    }.items():
        if any(term in text for term in terms):
            return label
    return _normalized(gap.failure_type)


def structural_gap_fingerprint(gap: GapSignature, purpose: PurposeContract) -> str:
    binding = (
        "exact algorithm" if gap.affected_algorithm != "Unspecified"
        else "algorithm family" if gap.affected_algorithm_family != "unspecified"
        else "unspecified"
    )
    payload = {
        "task": _normalized(gap.task),
        "data_type": _normalized(gap.data_type),
        "algorithm_family": _normalized(gap.affected_algorithm_family),
        "binding_granularity": binding,
        "failure_topology": _failure_topology(gap),
        "affected_component": _normalized(gap.affected_component),
        "scope": _scope(gap),
        "assumption": _normalized(" ".join(gap.unresolved_assumptions)),
        "observed_condition": _normalized(gap.observable_failure_signal),
        "missing_evaluation": _normalized(gap.missing_dimension),
        "metric_family": _normalized(gap.primary_metric),
        "required_response": _normalized(gap.required_response),
        "deployment": _normalized(purpose.deployment_environment),
        "available_information": sorted(map(_normalized, gap.available_inference_information)),
        "constraints": sorted(map(_normalized, gap.constraints)),
    }
    return sha1(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _events(gaps: list[GapSignature]) -> list[EvidenceEvent]:
    output = []
    for gap in gaps:
        for index, sentence in enumerate(gap.evidence_sentences):
            paper_id = (
                gap.evidence_paper_ids[index]
                if index < len(gap.evidence_paper_ids) else "corpus"
            )
            section = (
                gap.evidence_sections[index]
                if index < len(gap.evidence_sections) else "unknown"
            )
            output.append(EvidenceEvent(
                "event:" + sha1(
                    f"{gap.gap_id}:{paper_id}:{sentence}".encode()
                ).hexdigest()[:12],
                gap.gap_id, paper_id, sentence, section,
                gap.structural_gap_subtype or gap.gap_type,
            ))
    return output


def consolidate_gaps(
    gaps: list[GapSignature],
    purpose: PurposeContract,
    known_solutions: dict[str, KnownSolutionResult],
    *,
    maximum_promoted: int = 12,
    maximum_exploratory: int = 8,
) -> GapConsolidationResult:
    grouped: dict[str, list[GapSignature]] = {}
    for gap in gaps:
        grouped.setdefault(structural_gap_fingerprint(gap, purpose), []).append(gap)
    families = []
    for fingerprint, members in grouped.items():
        representative = max(
            members,
            key=lambda gap: (
                gap.evidence_count, gap.confidence_score,
                gap.testability_score, gap.gap_id,
            ),
        )
        papers = sorted({
            paper_id for gap in members for paper_id in gap.evidence_paper_ids
        })
        known = [
            known_solutions[gap.gap_id] for gap in members
            if gap.gap_id in known_solutions
        ]
        mitigations = sorted({
            method for result in known for method in result.mitigating_methods
        })
        known_search_sufficient = bool(known)
        reasons = []
        status = "PROMOTED"
        if len(papers) < 2:
            status, reasons = "SINGLE_PAPER", ["fewer than two independent papers"]
        elif representative.metadata_completeness and representative.metadata_completeness < .55:
            status, reasons = "METADATA_ARTIFACT", ["metadata completeness below 0.55"]
        elif representative.testability_score < .5:
            status, reasons = "UNTESTABLE", ["testability below 0.50"]
        elif not known_search_sufficient:
            status, reasons = (
                "INSUFFICIENT_KNOWN_SOLUTION_SEARCH",
                ["no recorded known-solution assessment"],
            )
        elif mitigations and not representative.unresolved_remainder:
            status, reasons = "LIKELY_ADDRESSED", ["direct mitigation with no unresolved remainder"]
        elif representative.affected_algorithm == "Unspecified" and (
            representative.affected_algorithm_family == "unspecified"
        ):
            status, reasons = "WRONG_ALGORITHM_BINDING", ["algorithm binding unspecified"]
        family_id = f"gap-family:{fingerprint[:12]}"
        fields = {
            "failure_topology": _failure_topology(representative),
            "affected_component": representative.affected_component,
            "scope": _scope(representative),
            "metric": representative.primary_metric,
            "required_response": representative.required_response,
        }
        disagreements = {}
        for field_name, attribute in (
            ("algorithm_family", "affected_algorithm_family"),
            ("failure_type", "failure_type"),
            ("affected_component", "affected_component"),
            ("metric", "primary_metric"),
        ):
            values = sorted({str(getattr(gap, attribute)) for gap in members})
            if len(values) > 1:
                disagreements[field_name] = values
        families.append(CanonicalGapFamily(
            family_id, fingerprint, representative.gap_id,
            representative.title,
            (
                f"For {representative.task}, {representative.failure_type} "
                f"affects {representative.affected_component}; evidence calls for "
                f"{representative.required_response}."
            ),
            sorted(gap.gap_id for gap in members), papers,
            max((gap.source_diversity for gap in members), default=0),
            representative.affected_algorithm_family,
            (
                "exact algorithm" if representative.affected_algorithm != "Unspecified"
                else "algorithm family"
            ),
            fields, disagreements,
            sorted({gap.structural_gap_subtype or gap.gap_type for gap in members}),
            len(papers),
            sum(
                section == "abstract" for gap in members
                for section in gap.evidence_sections
            ),
            round(sum(gap.metadata_completeness for gap in members) / len(members), 3),
            mitigations,
            representative.unresolved_remainder
            or "Requires direct known-solution and boundary-condition review.",
            representative.testability_score, status, reasons, members,
        ))
    families.sort(
        key=lambda family: (
            family.promotion_status == "PROMOTED",
            family.empirical_support_count, family.testability,
            family.family_id,
        ),
        reverse=True,
    )
    promoted, exploratory = [], []
    diversity: set[tuple[str, str]] = set()
    for family in families:
        key = (
            family.field_consensus["failure_topology"],
            family.field_consensus["affected_component"],
        )
        if family.promotion_status == "PROMOTED" and len(promoted) < maximum_promoted:
            if key not in diversity or len(promoted) < maximum_promoted // 2:
                promoted.append(family)
                diversity.add(key)
        elif len(exploratory) < maximum_exploratory:
            exploratory.append(family)
    return GapConsolidationResult(_events(gaps), gaps, families, promoted, exploratory)
