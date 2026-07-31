"""Deterministic DOT diagram specifications with readable text fallbacks."""

from __future__ import annotations

from typing import Any

from ux_models import DirectionSummary, IdeaDerivation, candidate_modification
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
        f"Relevant/context papers: {direction.evidence_bearing_paper_count}",
        f"Gap family: {direction.title}",
        f"Unresolved: {direction.unresolved_remainder}",
        f"Capability: {derivation.required_capability}",
        f"Mechanism: {derivation.mechanism_name}",
        f"Modification: {derivation.modification_slot}",
        f"Expected metric: {direction.primary_metric}",
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
    change = (
        f"CHANGE: {candidate.affected_component} · "
        f"{candidate_modification(candidate)}"
    )
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
    mappings = [
        ("signal", derivation.mechanism_signal, "ML observable signal"),
        ("state", derivation.mechanism_state,
         f"state supporting {derivation.modification_slot}"),
        ("trigger", derivation.mechanism_trigger, "ML update trigger"),
        ("response", derivation.mechanism_response,
         ", ".join(derivation.selected_operators)),
        ("risk", "; ".join(derivation.analogy_boundaries),
         "ML transfer failure risk"),
    ]
    nodes = []
    edges = []
    fallback_rows = []
    for index, (role, external, ml) in enumerate(mappings):
        left, right = f"external_{index}", f"ml_{index}"
        nodes.extend([(left, f"External {role}: {external}"),
                      (right, f"ML {role}: {ml}")])
        edges.append((left, right, "maps to"))
        fallback_rows.append(f"External {role}: {external} → ML {role}: {ml}")
    return {
        "diagram_id": "mechanism_transfer", "title": "Mechanism transfer map",
        "dot": _dot(nodes, edges),
        "fallback": "\n".join(fallback_rows),
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
