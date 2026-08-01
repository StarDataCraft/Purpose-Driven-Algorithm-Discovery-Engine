"""Constrained structured algorithm synthesis from signatures and operators."""

from __future__ import annotations

from hashlib import sha1

from experiment_planner import build_experiment
from falsification import falsification_tests
from models import (
    AlgorithmCandidate, AlgorithmRecord, AlignmentResult, GapSignature,
    MechanismSignature, Operator, PurposeContract, ScoreCard,
)
from novelty import assess_structural_novelty, fingerprint_candidate, novelty_queries


def synthesize_candidate(purpose: PurposeContract, gap: GapSignature,
                         algorithm: AlgorithmRecord, mechanisms: list[MechanismSignature],
                         operators: list[Operator], alignment: AlignmentResult,
                         scores: ScoreCard, trace: dict[str, object]) -> AlgorithmCandidate:
    operator_names = [operator.name for operator in operators]
    mechanism_names = [mechanism.name for mechanism in mechanisms]
    label = f"{mechanism_names[0].split()[0].title()} {algorithm.name}"
    cid = "cand:" + sha1(
        f"{purpose.purpose_id}:{gap.gap_id}:{algorithm.name}:{mechanism_names}:{operator_names}".encode()
    ).hexdigest()[:12]
    slot = gap.affected_component
    formulas = "; ".join(operator.formula_schema for operator in operators)
    states = [state for operator in operators for state in operator.produced_state]
    required = list(dict.fromkeys(
        signal for mechanism in mechanisms for signal in mechanism.required_signal
    ))
    equivalent = list(dict.fromkeys(
        pattern for operator in operators for pattern in operator.known_equivalent_ml_patterns
    ))
    candidate = AlgorithmCandidate(
        candidate_id=cid, candidate_name=label,
        direction_family="", purpose_contract_id=purpose.purpose_id,
        gap_id=gap.gap_id, gap_summary=f"{gap.failure_type} in {gap.task}",
        evidence_paper_ids=gap.evidence_paper_ids, base_algorithm=algorithm.name,
        base_algorithm_family=algorithm.family, affected_component=slot,
        borrowed_mechanisms=mechanism_names,
        source_domains=[mechanism.source_domain for mechanism in mechanisms],
        structural_alignment=alignment.field_scores,
        selected_operators=operator_names, new_state_variables=states,
        objective_delta=formulas if slot == "objective" else "",
        update_rule_delta=formulas if slot in (
            "update_rule", "feedback_control", "state_estimation",
            "model_selection",
        ) else "",
        inference_delta=f"consume only available signals: {', '.join(required)}",
        initialization_delta=formulas if slot == "initialization" else "",
        memory_delta=formulas if slot == "memory" else "",
        routing_delta=formulas if slot in ("routing", "expert_selection") else "",
        aggregation_delta=formulas if slot == "aggregation" else "",
        stopping_delta=formulas if slot == "stopping" else "",
        component_lifecycle_delta=formulas if slot == "component_birth_death" else "",
        complexity_delta="bounded additive state and operator evaluation",
        required_training_information=purpose.available_training_information,
        required_inference_information=required,
        expected_improvement=purpose.desired_improvement,
        primary_metric=purpose.primary_metric, secondary_metrics=purpose.secondary_metrics,
        must_not_degrade=purpose.must_not_degrade,
        applicability_conditions=[gap.failure_type, f"{slot} is modifiable", "required signals are observable"],
        expected_failure_modes=[m.failure_boundary for m in mechanisms],
        trade_offs=[operator.complexity_effect for operator in operators],
        falsification_tests=falsification_tests(algorithm.name, operators[0], mechanisms[0]),
        novelty_queries=[], nearest_known_method_patterns=equivalent,
        minimal_experiment=build_experiment(purpose, gap, algorithm, label),
        scores=scores, confidence=scores.confidence, stochastic_trace=trace,
        strongest_rejection_reason=f"A simpler {equivalent[0] if equivalent else 'adaptive baseline'} may explain the gain.",
        kill_criterion="Reject if shuffled signal, fixed mechanism, or matched-compute baseline matches the full candidate.",
    )
    candidate.novelty_queries = novelty_queries(candidate)
    candidate.structural_fingerprint = fingerprint_candidate(candidate)
    candidate.novelty_status, _ = assess_structural_novelty(candidate, [])
    return candidate
