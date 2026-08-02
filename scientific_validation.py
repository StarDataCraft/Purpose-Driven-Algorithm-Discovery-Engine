"""Pre-promotion scientific validity, evidence-role, and implementation gates."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import Sequence

from models import (
    AlgorithmCandidate, AlgorithmModificationSpec, GapSignature, Paper,
    PaperEvidenceRole, PurposeContract,
)
from ux_models import DirectionSummary, IdeaDerivation, candidate_modification


DIRECT_FAILURE_EVIDENCE = "DIRECT_FAILURE_EVIDENCE"
CONTEXTUAL_BACKGROUND = "CONTEXTUAL_BACKGROUND"
EXTERNAL_MECHANISM_EVIDENCE = "EXTERNAL_MECHANISM_EVIDENCE"
IRRELEVANT = "IRRELEVANT"


def _tokens(value: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]+", value.casefold())
        if len(token) > 2 and token not in {"with", "from", "under", "using", "that", "this"}
    }


def classify_paper_roles(
    papers: Sequence[Paper], purpose: PurposeContract, gap: GapSignature,
    candidate: AlgorithmCandidate,
) -> list[PaperEvidenceRole]:
    """Assign one conservative role; canonical-family proximity is never direct."""
    task_terms = _tokens(f"{purpose.task} {purpose.data_type}")
    purpose_text = f"{purpose.task} {purpose.data_type}".casefold()
    if any(term in purpose_text for term in ("online", "stream")):
        task_terms.update({"online", "stream", "streaming", "ensemble", "forest", "drift"})
    if "classif" in purpose_text:
        task_terms.update({"classification", "classifier", "predictor", "tabular"})
    if "cluster" in purpose_text:
        task_terms.update({"cluster", "clustering", "centroid", "density"})
    failure_terms = _tokens(f"{purpose.current_failure} {gap.failure_type}")
    mechanism_terms = _tokens(" ".join(candidate.borrowed_mechanisms))
    direct_ids = set(gap.evidence_paper_ids)
    candidate_ids = set(candidate.evidence_paper_ids)
    records = []
    for paper in papers:
        text = _tokens(f"{paper.title} {paper.abstract}")
        task_match = bool(text & task_terms)
        failure_match = len(text & failure_terms) >= 2
        reviewed = paper.reviewed_relevance_label or "NOT_REVIEWED"
        estimated = (paper.estimated_relevance_label or "unknown").upper()
        estimated_irrelevant = estimated in {"IRRELEVANT", "ESTIMATED_IRRELEVANT"}
        if paper.paper_id in direct_ids and task_match and failure_match and not estimated_irrelevant:
            role = DIRECT_FAILURE_EVIDENCE
            claim = f"Directly states evidence about {gap.failure_type}."
            reason = "Gap provenance plus hard task/failure compatibility."
        elif paper.paper_id in candidate_ids and bool(text & mechanism_terms) and not estimated_irrelevant:
            role = EXTERNAL_MECHANISM_EVIDENCE
            claim = "Supports the external mechanism, not the ML failure claim."
            reason = "Candidate mechanism evidence with no direct-gap promotion."
        elif task_match and not estimated_irrelevant:
            role = CONTEXTUAL_BACKGROUND
            claim = "Provides task context only."
            reason = "Task overlap without a direct failure-evidence path."
        else:
            role = IRRELEVANT
            claim = "No candidate claim is supported."
            reason = "Fails hard task/failure relevance or is estimated irrelevant."
        records.append(PaperEvidenceRole(
            paper.paper_id, role, estimated, reviewed, claim,
            (paper.abstract or paper.title)[:400], reason,
        ))
    return records


def evidence_count_invariants(roles: Sequence[PaperEvidenceRole]) -> dict[str, int]:
    candidate_count = len(roles)
    automatically_relevant = sum(item.role != IRRELEVANT for item in roles)
    evidence_bearing = sum(item.role in {
        DIRECT_FAILURE_EVIDENCE, EXTERNAL_MECHANISM_EVIDENCE,
    } for item in roles)
    direct = sum(item.role == DIRECT_FAILURE_EVIDENCE for item in roles)
    assert direct <= evidence_bearing <= automatically_relevant <= candidate_count
    return {
        "direct_support_count": direct,
        "evidence_bearing_paper_count": evidence_bearing,
        "automatically_relevant_paper_count": automatically_relevant,
        "candidate_paper_count": candidate_count,
    }


def build_modification_spec(
    candidate: AlgorithmCandidate, derivation: IdeaDerivation,
) -> AlgorithmModificationSpec:
    rule = candidate_modification(candidate)
    definitions = {
        name: f"Candidate-defined state variable: {name.replace('_', ' ')}"
        for name in candidate.new_state_variables if name.strip()
    }
    symbols = set(re.findall(r"\b[A-Za-z][A-Za-z0-9_]*\b", rule))
    mathematical = bool(re.search(r"[=+\-*/]|\[[^]]+\]", rule))
    common = {"t", "if", "then", "and", "or", "using", "update", "rule"}
    unresolved = []
    if mathematical:
        unresolved.extend(
            f"undefined symbol: {symbol}" for symbol in sorted(symbols - set(definitions) - common)
        )
    action = next((value for value in (
        candidate.aggregation_delta, candidate.routing_delta,
        candidate.memory_delta, candidate.component_lifecycle_delta,
        candidate.inference_delta,
    ) if value.strip()), "")
    if not action and not re.search(r"[=\[\]]", rule) and len(rule.split()) >= 4:
        action = rule
    delayed = [item for item in candidate.required_inference_information
               if any(term in item.casefold() for term in ("label", "residual", "error feedback"))]
    return AlgorithmModificationSpec(
        candidate.base_algorithm_family, candidate.base_algorithm,
        derivation.modification_slot, [f"existing {derivation.modification_slot} state"],
        list(candidate.new_state_variables), definitions,
        derivation.mechanism_trigger, rule, action,
        candidate.initialization_delta, "retain the base algorithm update",
        list(candidate.required_training_information),
        [item for item in candidate.required_inference_information if item not in delayed],
        delayed, candidate.complexity_delta, candidate.memory_delta,
        list(candidate.must_not_degrade), unresolved,
    )


@dataclass(frozen=True)
class ScientificGateResult:
    candidate_id: str
    passed: bool
    failures: tuple[str, ...]
    paper_roles: tuple[PaperEvidenceRole, ...]
    paper_counts: dict[str, int]
    modification_spec: AlgorithmModificationSpec


def validate_candidate_for_promotion(
    *, candidate: AlgorithmCandidate, derivation: IdeaDerivation,
    direction: DirectionSummary, gap: GapSignature, purpose: PurposeContract,
    papers: Sequence[Paper], full_audit: object | None = None,
) -> ScientificGateResult:
    roles = classify_paper_roles(papers, purpose, gap, candidate)
    counts = evidence_count_invariants(roles)
    spec = build_modification_spec(candidate, derivation)
    failures = []
    combined = " ".join((candidate.gap_summary, candidate.expected_improvement,
                         candidate.primary_metric, direction.failure_condition)).casefold()
    if purpose.current_failure.casefold() not in combined and gap.failure_type.casefold() not in combined:
        failures.append("problem fit: exact failure condition is not addressed")
    if candidate.primary_metric.casefold() != purpose.primary_metric.casefold():
        failures.append("problem fit: target metric changed")
    if counts["direct_support_count"] < 1:
        failures.append("evidence validity: no directly relevant failure paper")
    novelty = candidate.novelty_status.upper().replace(" ", "_")
    if novelty in {"", "LIKELY_DUPLICATE", "KNOWN_METHOD_RENAMED", "INSUFFICIENT_SEARCH", "INSUFFICIENT_EVIDENCE"}:
        failures.append("known-solution validation: prior-art coverage is insufficient or duplicate risk is unresolved")
    if not all((derivation.mechanism_signal, derivation.mechanism_state,
                derivation.mechanism_trigger, derivation.mechanism_response)):
        failures.append("mechanism validation: signal, state, trigger, or response is missing")
    if candidate.alignment_acceptance not in {"HARD_VALIDATION_PASSED", "STRONG"}:
        failures.append("structural alignment: stronger than surface similarity is required")
    if full_audit is not None:
        failed_dimensions = [item.name for item in full_audit.audit_dimensions if not item.passed]
        if failed_dimensions or not str(full_audit.final_decision).startswith("PASS"):
            failures.append("full audit rejected mandatory dimensions: " + ", ".join(failed_dimensions))
    online_drift = "drift" in purpose.current_failure.casefold() and any(
        term in purpose.task.casefold() for term in ("online", "stream")
    )
    if online_drift and candidate.base_algorithm.casefold() == "random forest":
        failures.append("algorithm binding: generic Random Forest is not an online drift-capable variant")
    if spec.unresolved_implementation_choices:
        failures.append("implementation completeness: " + "; ".join(spec.unresolved_implementation_choices))
    if not spec.action_rule:
        failures.append("implementation completeness: update does not cause a concrete algorithm action")
    inference = " ".join(candidate.required_inference_information).casefold()
    available = " ".join(purpose.available_inference_information).casefold()
    if any(term in inference for term in ("true label", "prediction residual", "labeled error")) and not any(
        term in available for term in ("label", "delayed feedback")
    ):
        failures.append("information availability: true-label residual is unavailable at prediction time")
    if online_drift:
        causal = " ".join((candidate.expected_improvement, candidate.update_rule_delta,
                           candidate.memory_delta, candidate.routing_delta,
                           derivation.mechanism_response)).casefold()
        if "recurr" not in causal or not any(term in causal for term in (
            "prior", "histor", "archive", "regime", "reuse", "reactivat",
        )):
            failures.append("recurrence-specific causal path is absent")
    metrics = {item.casefold() for item in candidate.minimal_experiment.metrics}
    candidate_text = " ".join((candidate.candidate_name, candidate_modification(candidate),
                               *candidate.new_state_variables)).casefold()
    if "expert activation accuracy" in metrics and "expert" not in candidate_text:
        failures.append("experiment consistency: expert activation metric has no expert mechanism")
    if not candidate.kill_criterion and not candidate.minimal_experiment.failure_rule:
        failures.append("falsification validation: kill criterion is missing")
    return ScientificGateResult(
        candidate.candidate_id, not failures, tuple(dict.fromkeys(failures)),
        tuple(roles), counts, spec,
    )


def grouped_gate_failures(results: Sequence[ScientificGateResult]) -> dict[str, int]:
    return dict(Counter(reason.split(":", 1)[0] for result in results for reason in result.failures))
