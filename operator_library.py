"""Typed modification operators used for constrained synthesis."""

from __future__ import annotations

from models import Operator


def _op(identifier: str, name: str, slots: list[str], inputs: list[str], state: list[str],
        formula: str, equivalents: list[str]) -> Operator:
    return Operator(
        identifier, name, inputs, state, slots, [], formula,
        f"update {', '.join(state) or 'parameters'} when {', '.join(inputs)} is observed",
        inputs, ["training examples"], "bounded additive cost", "bounded state",
        "state and trigger can be inspected", equivalents,
        ["noisy trigger", "delayed response", "misspecified gain"],
    )


OPERATORS = [
    _op("dynamic_weighting", "dynamic weighting", ["aggregation", "objective"],
        ["performance signal"], ["weights"], "w[t+1] ∝ w[t] exp(-η loss[t])", ["online weighting"]),
    _op("threshold_switching", "threshold switching", ["regime_detection", "update_rule", "stopping"],
        ["observable statistic"], ["regime", "hysteresis"], "r[t+1] = switch(r[t]) if s[t] crosses τ", ["change detection"]),
    _op("state_augmentation", "state augmentation", ["state_representation", "state_estimation"],
        ["observable outputs"], ["estimated state"], "z[t+1] = F(z[t], y[t])", ["latent state filtering"]),
    _op("memory_retrieval", "memory retrieval", ["memory", "routing", "expert_selection"],
        ["query signature"], ["memory archive"], "i* = argmax sim(q, m[i])", ["episodic retrieval"]),
    _op("diversity_penalty", "diversity penalty", ["regularization", "assignment"],
        ["component overlap"], [], "L' = L + λ Σ overlap(i,j)", ["diversity regularization"]),
    _op("adaptive_regularization", "adaptive regularization", ["regularization", "feedback_control"],
        ["deviation signal"], ["regularization gain"], "λ[t+1] = clip(λ[t] + η e[t])", ["adaptive regularization"]),
    _op("reliability_update", "reliability update", ["aggregation", "uncertainty_estimate"],
        ["outcome feedback"], ["agent reliability"], "r[i,t+1] = (1-η)r[i,t] + η score[i,t]", ["dynamic ensemble weighting"]),
    _op("component_creation", "component creation", ["component_birth_death"],
        ["unexplained residual"], ["component population"], "create component if residual > τ and budget allows", ["split-merge models"]),
    _op("component_removal", "component removal", ["component_birth_death"],
        ["component utility"], ["component population"], "remove component if utility < τ for k steps", ["ensemble pruning"]),
    _op("posterior_correction", "posterior correction", ["objective", "uncertainty_estimate"],
        ["calibration residual"], ["calibration state"], "p' = normalize(p · c)", ["post-hoc calibration"]),
    _op("multi_timescale_update", "multi-timescale update", ["update_rule", "memory"],
        ["fast error", "slow trend"], ["fast state", "slow state"], "z = α z_fast + (1-α) z_slow", ["dual-memory learning"]),
    _op("specialist_routing", "specialist routing", ["routing", "expert_selection"],
        ["context signature"], ["routing scores"], "expert = argmax compatibility(context, niche)", ["mixture-of-experts routing"]),
    _op("resource_allocation", "resource allocation", ["expert_selection", "sampling", "feature_acquisition"],
        ["utility", "cost"], ["resource budget"], "allocate argmax Σ utility subject to Σ cost ≤ B", ["budgeted learning"]),
    _op("observation_correction", "observation correction", ["state_estimation", "update_rule"],
        ["observation innovation"], ["state estimate"], "z[t+1] = Fz[t] + K(y[t]-Hz[t])", ["observer updates"]),
    _op("selective_forgetting", "selective forgetting", ["memory"],
        ["age", "utility"], ["memory archive"], "retain items maximizing utility under capacity", ["replay-buffer selection"]),
    _op("adaptive_stopping", "adaptive stopping", ["stopping"],
        ["convergence signal", "budget"], ["stopping state"], "stop if gain < ε or cost > B", ["early stopping"]),
    _op("missing_feature_routing", "missing-feature routing", ["routing", "feature_acquisition"],
        ["feature availability mask"], ["availability state"], "route by observed feature subset", ["missingness-aware experts"]),
]
OPERATOR_BY_ID = {operator.operator_id: operator for operator in OPERATORS}


def compatible_operators(slot: str) -> list[Operator]:
    return [operator for operator in OPERATORS if slot in operator.compatible_slots]


def operator_is_compatible(operator: Operator, slot: str) -> bool:
    return slot in operator.compatible_slots and slot not in operator.incompatible_slots
