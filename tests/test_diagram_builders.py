from __future__ import annotations

from diagram_builders import (
    before_after_spec, evidence_to_idea_spec, experiment_spec,
    mechanism_transfer_spec,
)


def test_diagram_builders_are_deterministic_and_have_fallbacks():
    from app import load_fixture
    from discovery_pipeline import discover_structural_gaps
    from ux_models import build_direction_portfolio

    # Unit-level determinism is also covered end-to-end in AppTest; experiment
    # specs need no Streamlit state or renderer.
    value = {
        "dataset": "recurring stream", "baselines": ["baseline"],
        "metrics": ["recovery time"], "failure_rule": "no improvement",
    }
    first = experiment_spec(value)
    second = experiment_spec(value)
    assert first == second
    assert first["dot"].startswith("digraph")
    assert first["fallback"]
