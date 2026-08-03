"""Canonical post-repair hypothesis contracts and cross-view invariants."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from idea_maturity import ScientificAssessment
from models import AlgorithmCandidate, ExperimentPlan, PaperEvidenceRole
from ux_models import IdeaDerivation, candidate_to_dict, derivation_to_dict


RESOLVED_HYPOTHESIS_SCHEMA_VERSION = "resolved-hypothesis-v1"
SUPPORTING_ROLES = {
    "DIRECT_FAILURE_EVIDENCE", "CURRENT_SOLUTION_EVIDENCE",
    "EXTERNAL_MECHANISM_EVIDENCE", "TRANSFER_EVIDENCE",
    "IMPLEMENTATION_EVIDENCE",
}


@dataclass(frozen=True)
class EvidenceAssessment:
    direct_problem_evidence: tuple[dict[str, Any], ...] = ()
    contextual_problem_evidence: tuple[dict[str, Any], ...] = ()
    current_solution_evidence: tuple[dict[str, Any], ...] = ()
    external_mechanism_evidence: tuple[dict[str, Any], ...] = ()
    transfer_support: tuple[dict[str, Any], ...] = ()
    implementation_precedent: tuple[dict[str, Any], ...] = ()
    nearest_methods: tuple[str, ...] = ()
    irrelevant_or_rejected_papers: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class AlignmentAssessment:
    level: str
    mapped_roles: tuple[str, ...]
    missing_roles: tuple[str, ...]
    limiter: str = ""


@dataclass(frozen=True)
class CandidateRepairResult:
    original_candidate: dict[str, Any]
    original_derivation: dict[str, Any]
    repaired_candidate: AlgorithmCandidate
    repaired_derivation: IdeaDerivation
    repaired_operator_plan: dict[str, Any]
    repairs_applied: tuple[dict[str, Any], ...]
    unresolved_issues: tuple[str, ...]
    changed_fields: tuple[str, ...]
    requires_reassessment: bool


@dataclass(frozen=True)
class ResolvedHypothesis:
    schema_version: str
    source_candidate_id: str
    source_derivation_id: str
    resolved_hypothesis_id: str
    maturity_level: str
    title: str
    summary: str
    problem: str
    algorithm_family: str
    algorithm_variant: str
    capability: str
    required_roles: tuple[str, ...]
    operator_plan: dict[str, Any]
    selected_slot_bundle: tuple[str, ...]
    mechanism: str
    causal_path: str
    information_timing: str
    schematic_operator: str
    exact_operator: str
    expected_result: str
    evidence: EvidenceAssessment
    alignment: AlignmentAssessment
    strengths: tuple[str, ...]
    fatal_failures: tuple[dict[str, Any], ...]
    maturity_limiters: tuple[dict[str, Any], ...]
    open_design_choices: tuple[dict[str, Any], ...]
    experiment_spec: dict[str, Any]
    repairs_applied: tuple[dict[str, Any], ...]
    repair_provenance: tuple[str, ...]
    audit: dict[str, Any]
    confidence: dict[str, float]
    candidate_snapshot: dict[str, Any]
    derivation_snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResolvedHypothesis":
        values = dict(payload)
        evidence_values = dict(values["evidence"])
        for key, item in evidence_values.items():
            evidence_values[key] = tuple(item)
        values["evidence"] = EvidenceAssessment(**evidence_values)
        alignment_values = dict(values["alignment"])
        alignment_values["mapped_roles"] = tuple(alignment_values.get("mapped_roles", ()))
        alignment_values["missing_roles"] = tuple(alignment_values.get("missing_roles", ()))
        values["alignment"] = AlignmentAssessment(**alignment_values)
        for key in (
            "required_roles", "selected_slot_bundle", "strengths",
            "fatal_failures", "maturity_limiters", "open_design_choices",
            "repairs_applied", "repair_provenance",
        ):
            values[key] = tuple(values.get(key, ()))
        return cls(**values)


def _fingerprint(candidate_id: str, candidate: dict[str, Any], derivation: dict[str, Any]) -> str:
    payload = json.dumps([candidate, derivation], sort_keys=True, default=str)
    return f"resolved:{candidate_id}:{sha256(payload.encode()).hexdigest()[:16]}"


def _repair_experiment(plan: ExperimentPlan, *, delayed: bool, online: bool) -> ExperimentPlan:
    baselines = list(plan.baselines)
    if online:
        baselines = [
            "adaptive random forest", "established streaming ensemble",
            "memory-free matched-compute variant", "fixed-routing variant",
            "shuffled-history or shuffled-recurrence control",
        ]
    audit = {key: list(value) if isinstance(value, (list, tuple)) else value
             for key, value in plan.information_audit.items()}
    if delayed:
        audit["inference"] = [item for item in audit.get("inference", [])
                              if "residual" not in str(item).casefold()
                              and "label" not in str(item).casefold()]
        audit["delayed_feedback"] = ["labeled residual after prediction"]
    return replace(
        plan,
        base_algorithm="online tree ensemble" if online else plan.base_algorithm,
        baselines=baselines,
        stressor=(f"{plan.stressor}; delayed-label arrival" if delayed and "delay" not in plan.stressor.casefold()
                  else plan.stressor),
        information_audit=audit,
        metrics=[item for item in plan.metrics if "expert activation" not in item.casefold()],
    )


def apply_bounded_repairs(
    candidate: AlgorithmCandidate, derivation: IdeaDerivation,
    assessment: ScientificAssessment,
) -> CandidateRepairResult:
    """Materialize assessment repairs as new candidate and derivation snapshots."""
    repaired_candidate = replace(candidate)
    repaired_derivation = derivation
    changes: list[str] = []
    repair_text = " ".join(item.repair for item in assessment.repairs_applied).casefold()
    online = "online tree ensemble" in repair_text
    bundle = tuple(assessment.capability_slot_assessment.selected_slot_bundle)
    expanded = "slot bundle" in repair_text and len(bundle) > 1
    delayed = "delayed-feedback" in repair_text
    if online:
        repaired_candidate = replace(
            repaired_candidate,
            candidate_name="Delayed-feedback recurrence correction for an online tree ensemble",
            base_algorithm="online tree ensemble",
            base_algorithm_family="online tree ensemble",
        )
        repaired_derivation = replace(repaired_derivation, base_algorithm_family="online tree ensemble")
        changes.extend(("title", "algorithm_binding"))
    if expanded:
        operational = (
            "After delayed labels arrive, update a bounded reliability or regime state "
            "and temporarily adjust routing or ensemble weights during a recurrence "
            "verification window."
        )
        repaired_candidate = replace(
            repaired_candidate, affected_component="capability/operator slot bundle",
            selected_operators=list(bundle), update_rule_delta=operational,
            routing_delta=operational,
        )
        repaired_derivation = replace(
            repaired_derivation, modification_slot=" + ".join(bundle),
            selected_operators=bundle,
        )
        changes.extend(("modification_slot", "operator_plan", "causal_path"))
    if delayed:
        immediate = tuple(
            item for item in repaired_candidate.required_inference_information
            if not any(term in item.casefold() for term in ("residual", "true label", "labeled error"))
        )
        training = list(dict.fromkeys([
            *repaired_candidate.required_training_information,
            "delayed labeled residual after prediction",
        ]))
        repaired_candidate = replace(
            repaired_candidate,
            required_inference_information=list(immediate),
            required_training_information=training,
            inference_delta=("Predictions are immediate; labeled residual updates occur only "
                             "after delayed feedback."),
        )
        changes.append("information_timing")
    repaired_candidate = replace(
        repaired_candidate,
        minimal_experiment=_repair_experiment(
            repaired_candidate.minimal_experiment, delayed=delayed, online=online,
        ),
    )
    if online or delayed or expanded:
        changes.append("experiment")
    return CandidateRepairResult(
        candidate_to_dict(candidate), derivation_to_dict(derivation),
        repaired_candidate, repaired_derivation,
        asdict(assessment.capability_slot_assessment),
        tuple(asdict(item) for item in assessment.repairs_applied),
        tuple(item.issue for item in assessment.maturity_limiters),
        tuple(dict.fromkeys(changes)), bool(changes),
    )


def evidence_from_roles(
    roles: Sequence[PaperEvidenceRole], nearest_methods: Sequence[str],
) -> EvidenceAssessment:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for role in roles:
        grouped.setdefault(role.role, []).append(asdict(role))
    return EvidenceAssessment(
        direct_problem_evidence=tuple(grouped.get("DIRECT_FAILURE_EVIDENCE", ())),
        contextual_problem_evidence=tuple(grouped.get("CONTEXTUAL_BACKGROUND", ())),
        current_solution_evidence=tuple(grouped.get("CURRENT_SOLUTION_EVIDENCE", ())),
        external_mechanism_evidence=tuple(grouped.get("EXTERNAL_MECHANISM_EVIDENCE", ())),
        transfer_support=tuple(grouped.get("TRANSFER_EVIDENCE", ())),
        implementation_precedent=tuple(grouped.get("IMPLEMENTATION_EVIDENCE", ())),
        nearest_methods=tuple(nearest_methods),
        irrelevant_or_rejected_papers=tuple(grouped.get("IRRELEVANT", ())),
    )


def create_resolved_hypothesis(
    repair: CandidateRepairResult, assessment: ScientificAssessment,
    *, problem: str, summary: str, audit: Mapping[str, Any] | None = None,
) -> ResolvedHypothesis:
    candidate = repair.repaired_candidate
    derivation = repair.repaired_derivation
    plan = assessment.capability_slot_assessment
    evidence = evidence_from_roles(assessment.paper_roles, candidate.nearest_known_method_patterns)
    level = assessment.alignment_level
    structural_strengths = tuple(
        item for item in assessment.strengths
        if not (level in {"SURFACE_ONLY", "METAPHOR_ONLY", "INVALID"}
                and "structural roles map" in item.casefold())
        and not (not evidence.direct_problem_evidence
                 and "directly supports" in item.casefold())
    )
    alignment = AlignmentAssessment(
        level, tuple(plan.covered_mechanism_roles), tuple(plan.missing_roles),
        "Surface-only alignment remains unresolved." if level in {"SURFACE_ONLY", "METAPHOR_ONLY"} else "",
    )
    spec = assessment.modification_spec
    original_rule = str(repair.original_candidate.get("update_rule_delta", ""))
    original_mathematical = any(token in original_rule for token in ("=", "[", "]"))
    schematic = (
        f"Schematic operator — not yet specified: {original_rule}"
        if original_mathematical or spec.unresolved_implementation_choices else ""
    )
    exact = "" if schematic else spec.update_rule
    resolved = ResolvedHypothesis(
        RESOLVED_HYPOTHESIS_SCHEMA_VERSION, candidate.candidate_id,
        derivation.derivation_id,
        _fingerprint(candidate.candidate_id, candidate_to_dict(candidate), derivation_to_dict(derivation)),
        assessment.maturity_level.value, candidate.candidate_name,
        summary, problem, candidate.base_algorithm_family, candidate.base_algorithm,
        plan.required_capability, tuple(plan.required_roles), asdict(plan),
        tuple(plan.selected_slot_bundle), derivation.mechanism_name,
        candidate.update_rule_delta or candidate.routing_delta,
        ("DELAYED" if any("delayed-feedback" in item.get("repair", "").casefold()
                          for item in repair.repairs_applied)
         else assessment.information_feasibility_level),
        schematic, exact,
        candidate.expected_improvement, evidence, alignment, structural_strengths,
        tuple(asdict(item) for item in assessment.fatal_failures),
        tuple(asdict(item) for item in assessment.maturity_limiters),
        tuple(asdict(item) for item in assessment.open_design_choices),
        asdict(candidate.minimal_experiment), repair.repairs_applied,
        tuple(item.get("provenance", "") for item in repair.repairs_applied),
        dict(audit or {}), dict(assessment.confidence_by_dimension),
        candidate_to_dict(candidate), derivation_to_dict(derivation),
    )
    violations = validate_resolved_hypothesis(resolved)
    if violations:
        raise ValueError("Resolved hypothesis consistency error: " + "; ".join(violations))
    return resolved


def validate_resolved_hypothesis(value: ResolvedHypothesis) -> list[str]:
    violations: list[str] = []
    experiment_family = str(value.experiment_spec.get("base_algorithm", "")).casefold()
    if value.algorithm_variant.casefold() not in experiment_family and value.algorithm_family.casefold() not in experiment_family:
        violations.append("experiment algorithm differs from resolved algorithm")
    if not value.evidence.direct_problem_evidence and any(
        "directly supports" in item.casefold() for item in value.strengths
    ):
        violations.append("direct-evidence strength has an empty evidence list")
    if value.alignment.level in {"SURFACE_ONLY", "METAPHOR_ONLY", "INVALID"} and any(
        "structural roles map" in item.casefold() for item in value.strengths
    ):
        violations.append("alignment strength contradicts canonical alignment level")
    if value.information_timing == "DELAYED" and any(
        term in " ".join(value.candidate_snapshot.get("required_inference_information", ())).casefold()
        for term in ("residual", "true label", "labeled error")
    ):
        violations.append("delayed feedback is listed as immediate inference information")
    if len(value.selected_slot_bundle) > 1 and value.derivation_snapshot.get("modification_slot") == "update_rule":
        violations.append("multi-slot bundle collapsed to update_rule")
    if value.schematic_operator and value.exact_operator:
        violations.append("schematic operator is also labeled exact")
    supporting_ids = {
        item["paper_id"] for role in (
            value.evidence.direct_problem_evidence,
            value.evidence.current_solution_evidence,
            value.evidence.external_mechanism_evidence,
            value.evidence.transfer_support,
            value.evidence.implementation_precedent,
        ) for item in role
    }
    rejected_ids = {item["paper_id"] for item in value.evidence.irrelevant_or_rejected_papers}
    if supporting_ids & rejected_ids:
        violations.append("irrelevant paper appears in a supporting evidence group")
    return violations
