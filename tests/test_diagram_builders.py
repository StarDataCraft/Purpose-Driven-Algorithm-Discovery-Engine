from __future__ import annotations

from types import SimpleNamespace

from diagram_builders import (
    before_after_spec, evidence_to_idea_spec, experiment_spec,
    mechanism_transfer_spec,
)
from ux_models import candidate_modification


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


def test_required_diagram_fallbacks_name_complete_evidence_and_mapping_roles(
    purpose, ml_papers, external_papers, tmp_path,
):
    from discovery_pipeline import discover_structural_gaps
    from external_discovery_pipeline import SearchPolicy
    from idea_pipeline import derive_ideas_for_direction
    from run_models import ResearchRun
    from ux_models import build_direction_portfolio

    discovery = discover_structural_gaps(ml_papers, purpose)
    run = ResearchRun.create(
        purpose.purpose_id, "OFFLINE_FIXTURE", "lightweight",
        purpose.publication_window,
    )
    direction = build_direction_portfolio(
        run.run_id, purpose, discovery.consolidation.promoted,
        discovery.gaps, discovery.papers,
    )[0]
    gap = next(item for item in discovery.gaps
               if item.gap_id == direction.selected_gap_id)
    result = derive_ideas_for_direction(
        purpose=purpose, direction=direction, gap=gap, parent_run=run,
        search_policy=SearchPolicy("OFFLINE_FIXTURE"), seed=42,
        memory_path=tmp_path / "memory.db",
        fixture_loader=lambda: external_papers,
        cache_directory=tmp_path / "cache",
    )
    derivation = result.derivations[0]
    evidence = evidence_to_idea_spec(direction, derivation)["fallback"]
    mapping = mechanism_transfer_spec(derivation)["fallback"]
    assert all(label in evidence for label in (
        "Gap family", "Unresolved", "Capability", "Mechanism",
        "Modification", "Expected metric",
    ))
    assert all(f"External {role}" in mapping for role in (
        "signal", "state", "trigger", "response", "risk",
    ))


def test_candidate_change_uses_the_delta_for_its_actual_slot():
    candidate = SimpleNamespace(
        affected_component="aggregation", update_rule_delta="",
        inference_delta="consume observable signals", objective_delta="",
        memory_delta="", routing_delta="",
        aggregation_delta="weights follow bounded feedback",
        initialization_delta="", stopping_delta="",
        component_lifecycle_delta="",
    )
    assert candidate_modification(candidate) == (
        "weights follow bounded feedback"
    )


def test_diagram_renderer_falls_back_when_graphviz_fails(monkeypatch):
    import app

    rendered = []
    monkeypatch.setattr(
        app.st, "graphviz_chart",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("renderer")),
    )
    monkeypatch.setattr(app.st, "subheader", lambda value: rendered.append(value))
    monkeypatch.setattr(app.st, "warning", lambda value: rendered.append(value))
    monkeypatch.setattr(app.st, "write", lambda value: rendered.append(value))

    class Expander:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    monkeypatch.setattr(app.st, "expander", lambda *args, **kwargs: Expander())
    app.render_diagram({
        "title": "Test diagram", "dot": "digraph G {}",
        "fallback": "paper → gap → idea",
    })
    assert rendered.count("paper → gap → idea") == 2
    assert any("Diagram unavailable" in str(value) for value in rendered)
