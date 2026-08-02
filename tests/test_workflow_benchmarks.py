"""Actual-widget benchmarks for the three required scientific purposes."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "app.py"
OFFLINE = "Offline demonstration fixtures"


@pytest.mark.parametrize("task,data,failure,improvement,metric,expected_family", [
    ("online learning", "tabular streams",
     "recurring concept drift and slow recovery",
     "reduce post-drift recovery time", "recovery time", "ensemble"),
    ("classification", "tabular data",
     "training-inference missingness shift",
     "reduce missing-feature degradation", "missing-feature degradation",
     "neural_network"),
    ("dynamic clustering", "streaming vectors",
     "dynamic cluster birth/death under heterogeneous density",
     "detect cluster birth and death", "cluster birth detection delay",
     "clustering"),
])
def test_purpose_reaches_part_3_without_candidate_selection(
    task, data, failure, improvement, metric, expected_family,
):
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    for key, value in (
        ("_purpose_task", task), ("_purpose_data_type", data),
        ("_purpose_failure", failure),
        ("_purpose_improvement", improvement),
        ("_purpose_metric", metric),
    ):
        app.text_input(key=key).set_value(value)
    app.radio(key="_purpose_search_mode").set_value(OFFLINE)
    app.run(timeout=30)
    app.button[0].click().run(timeout=30)

    directions = app.session_state["current_direction_portfolio"]
    assert directions
    assert all(len(item.title.split()) >= 4 for item in directions)
    assert all(item.affected_algorithm_family.casefold() not in {
        "", "unknown", "unspecified",
    } for item in directions)
    assert directions[0].affected_algorithm_family == expected_family
    assert directions[0].primary_metric == metric

    app.button(key="_select_direction_0").click().run(timeout=30)
    app.button(key="_derive_ideas").click().run(timeout=30)
    selection = app.session_state["primary_idea_selection_record"]
    assert selection["status"] == "SELECTED"
    assert app.session_state["selected_idea_context"]
    assert app.session_state["selected_idea_id"] == selection["selected_candidate_id"]
    assert not any(item.key == "selected_idea_choice" for item in app.radio)
    assert app.button(key="_continue_to_explanation")

    app.button(key="_continue_to_explanation").click().run(timeout=30)
    explanation = app.session_state["current_result_explanation"]
    assert explanation.candidate_id == selection["selected_candidate_id"]
    assert not app.exception
