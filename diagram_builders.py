"""Deterministic DOT diagram specifications with readable text fallbacks."""

from __future__ import annotations

from typing import Any

from ux_models import DirectionSummary, IdeaDerivation
from models import AlgorithmCandidate


def _dot(nodes: list[tuple[str, str]], edges: list[tuple[str, str, str]]) -> str:
    lines = ["digraph G {", 'rankdir="LR";', 'node [shape="box"];']
    for node_id, label in nodes:
        safe = label.replace('"', "'").replace("\n", " ")
        lines.append(f'{node_id} [label="{safe}"];')
    for left, right, label in edges:
        safe = label.replace('"', "'")
        lines.append(f'{left} -> {right} [label="{safe}"];')
    lines.append("}")
    return "\n".join(lines)


def evidence_to_idea_spec(
    direction: DirectionSummary, derivation: IdeaDerivation,
) -> dict[str, Any]:
    labels = [
        direction.failure_condition, derivation.required_capability,
        derivation.mechanism_name, derivation.modification_slot,
    ]
    return {
        "diagram_id": "evidence_to_idea", "title": "Evidence → gap → mechanism → idea",
        "dot": _dot(
            [(f"n{i}", label) for i, label in enumerate(labels)],
            [(f"n{i}", f"n{i+1}", "") for i in range(len(labels) - 1)],
        ),
        "fallback": " → ".join(labels),
    }


def before_after_spec(candidate: AlgorithmCandidate) -> dict[str, Any]:
    before = f"BEFORE: {candidate.base_algorithm}"
    change = f"CHANGE: {candidate.affected_component} · {', '.join(candidate.selected_operators)}"
    expected = f"EXPECTED: {candidate.expected_improvement}"
    return {
        "diagram_id": "before_after", "title": "Before → change → expected result",
        "dot": _dot(
            [("before", before), ("change", change), ("expected", expected)],
            [("before", "change", "modify"), ("change", "expected", "test")],
        ),
        "fallback": f"{before} → {change} → {expected}",
    }


def mechanism_transfer_spec(derivation: IdeaDerivation) -> dict[str, Any]:
    external = (
        f"{derivation.external_domain}: {derivation.mechanism_signal} → "
        f"{derivation.mechanism_state} → {derivation.mechanism_response}"
    )
    ml = (
        f"ML: {derivation.modification_slot} → "
        f"{', '.join(derivation.selected_operators)}"
    )
    return {
        "diagram_id": "mechanism_transfer", "title": "Mechanism transfer map",
        "dot": _dot(
            [("external", external), ("boundary", "Structural analogy only"),
             ("ml", ml)],
            [("external", "boundary", "abstract"), ("boundary", "ml", "translate")],
        ),
        "fallback": f"{external} ↔ {ml}. Boundary: "
                    f"{'; '.join(derivation.analogy_boundaries)}",
    }


def experiment_spec(experiment: dict[str, Any]) -> dict[str, Any]:
    labels = [
        f"Data: {experiment.get('dataset', 'unspecified')}",
        f"Baselines: {', '.join(experiment.get('baselines', []))}",
        f"Metric: {', '.join(experiment.get('metrics', []))}",
        f"Decision: {experiment.get('failure_rule', 'predefine rejection')}",
    ]
    return {
        "diagram_id": "experiment", "title": "Fastest useful experiment",
        "dot": _dot(
            [(f"e{i}", label) for i, label in enumerate(labels)],
            [(f"e{i}", f"e{i+1}", "") for i in range(len(labels) - 1)],
        ),
        "fallback": " → ".join(labels),
    }
