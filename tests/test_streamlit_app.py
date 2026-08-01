"""AppTests for the three-part primary research workflow."""

from __future__ import annotations

from pathlib import Path
from dataclasses import replace

from streamlit.testing.v1 import AppTest

import app as app_module
from ux_models import (
    candidate_from_dict, candidate_to_dict, derivation_from_dict,
    derivation_to_dict, direction_from_dict, direction_to_dict,
)


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
PART_1 = "1 · Discover directions / 发现方向"
PART_2 = "2 · Analyze the gap / 分析 Gap"
PART_3 = "3 · Explain the idea / 解释新想法"
OFFLINE = "Offline demonstration fixtures"


def app_start() -> AppTest:
    return AppTest.from_file(str(APP_PATH), default_timeout=30).run()


def run_offline_part_1(app: AppTest) -> AppTest:
    app.radio(key="_purpose_search_mode").set_value(OFFLINE)
    app.button[0].click().run(timeout=30)
    return app


def run_to_part_3(app: AppTest) -> AppTest:
    run_offline_part_1(app)
    app.button(key="_select_direction_0").click().run(timeout=30)
    app.button(key="_derive_ideas").click().run(timeout=30)
    candidate_id = app.session_state["current_idea_portfolio"][0].candidate_id
    app.button(key=f"select_idea::{candidate_id}").click().run(timeout=30)
    return app


def test_primary_navigation_has_exactly_three_steps_and_tools():
    app = app_start()
    workflow = app.sidebar.radio(key="_primary_step")
    assert workflow.options == [PART_1, PART_2, PART_3]
    assert "_workflow_page" not in app.session_state
    assert app.sidebar.selectbox(key="_research_tool").value == "None"
    assert not app.exception


def test_part_1_simple_setup_and_direction_cards_with_papers():
    app = app_start()
    assert app.title[0].value == "Discover directions / 发现方向"
    assert app.button[0].label == "Find research directions / 寻找研究方向"
    run_offline_part_1(app)

    run = app.session_state["current_research_run"]
    assert run.actual_search_mode == "OFFLINE_FIXTURE"
    assert app.session_state["current_direction_portfolio"]
    assert run.candidate_paper_count != run.human_reviewed_paper_count
    assert run.automatically_relevant_paper_count <= run.candidate_paper_count
    assert run.evidence_bearing_paper_count <= run.candidate_paper_count
    assert any("View related papers" in item.label for item in app.expander)
    assert any("Promising research directions" in item.value for item in app.header)


def test_selecting_direction_moves_to_part_2_and_separates_evidence():
    app = run_offline_part_1(app_start())
    app.button(key="_select_direction_0").click().run(timeout=30)

    assert app.session_state["_primary_step"] == PART_2
    assert app.session_state["selected_direction_id"]
    assert app.session_state["selected_gap_family_id"]
    headings = " ".join(item.value for item in app.subheader)
    assert "Paper-stated evidence" in headings
    assert "System inference" in headings
    assert "Known solutions" in headings
    assert "Unresolved remainder" in headings
    assert not app.exception


def test_part_2_derives_operational_mechanisms_and_idea_portfolio():
    app = run_offline_part_1(app_start())
    app.button(key="_select_direction_0").click().run(timeout=30)
    app.button(key="_derive_ideas").click().run(timeout=30)

    assert app.session_state["current_idea_portfolio"]
    assert app.session_state["mechanisms"]
    headers = " ".join(item.value for item in app.header)
    assert "How new ideas are generated" in headers
    assert "External mechanism options" in headers
    assert "Candidate idea portfolio" in headers
    assert any(
        derivation.modification_slot
        for derivation in app.session_state["current_idea_portfolio"]
    )
    assert all(
        any((candidate.update_rule_delta, candidate.objective_delta,
             candidate.memory_delta, candidate.routing_delta,
             candidate.aggregation_delta, candidate.initialization_delta,
             candidate.stopping_delta, candidate.component_lifecycle_delta,
             candidate.inference_delta))
        for candidate in app.session_state["candidate_portfolio"]
    )
    assert not app.exception


def test_part_3_result_diagrams_experiment_and_secondary_json():
    app = run_to_part_3(app_start())

    explanation = app.session_state["current_result_explanation"]
    assert explanation.one_sentence_conclusion
    assert explanation.modification_slot
    assert explanation.proposed_change
    assert "No concrete modification" not in explanation.proposed_change
    assert explanation.supported_claims
    assert explanation.inferred_claims
    assert explanation.unknowns
    assert len(app.get("graphviz_chart")) >= 3
    assert len(app.session_state["current_diagram_specs"]) >= 3
    headers = " ".join(item.value for item in app.header)
    assert "Problem / 问题" in headers
    assert "Current behavior / 当前做法" in headers
    assert "Proposed change / 修改内容" in headers
    assert "Expected result / 预期结果" in headers
    assert "BEFORE → CHANGE → EXPECTED RESULT" in headers
    assert "Closest known methods" in headers
    assert "Fastest useful experiment" in headers
    assert "Supporting papers" in headers
    assert "Critical review / 批判性审查" in headers
    audit = app.session_state["current_result_audit"]
    assert len(audit.audit_dimensions) == 10
    assert {item.name for item in audit.audit_dimensions} == {
        "user_problem_fit", "literature_retrieval_quality",
        "evidence_gap_validity", "known_solution_novelty",
        "external_mechanism_quality", "structural_alignment_quality",
        "algorithm_specificity_executability",
        "falsifiability_experiment_quality", "readability_decision_value",
        "engineering_cost_deployment",
    }
    assert audit.final_decision.startswith("EXPLORATORY")
    assert len(audit.robustness_results) == 10
    assert any("Raw JSON" in item.label for item in app.expander)
    assert not app.exception


def test_actual_first_and_second_idea_buttons_commit_exact_snapshots():
    for index in (0, 1):
        app = run_offline_part_1(app_start())
        app.button(key="_select_direction_0").click().run(timeout=30)
        app.button(key="_derive_ideas").click().run(timeout=30)
        derivation = app.session_state["current_idea_portfolio"][index]
        expected = derivation.candidate_id
        app.button(key=f"select_idea::{expected}").click().run(timeout=30)

        context = app.session_state["selected_idea_context"]
        assert app.session_state["selected_idea_id"] == expected
        assert context.candidate_id == expected
        assert context.derivation_id == derivation.derivation_id
        assert context.candidate_snapshot["candidate_id"] == expected
        assert context.derivation_snapshot["candidate_id"] == expected
        assert app.session_state["current_result_explanation"].candidate_id == expected
        assert app.session_state["_primary_step"] == PART_3
        assert not any("Select an idea in Part 2." in x.value for x in app.info)
        assert not app.exception


def test_selected_snapshots_survive_both_portfolios_being_cleared_and_rerun():
    app = run_to_part_3(app_start())
    expected = app.session_state["selected_idea_id"]
    app.session_state["candidate_portfolio"] = []
    app.session_state["current_idea_portfolio"] = []
    app.session_state["current_result_explanation"] = None
    app.session_state["current_diagram_specs"] = []
    app.run(timeout=30)

    assert app.session_state["selected_idea_id"] == expected
    assert app.session_state["current_result_explanation"].candidate_id == expected
    assert len(app.session_state["current_diagram_specs"]) >= 3
    assert not any("Select an idea in Part 2." in x.value for x in app.info)
    assert not app.exception


def test_candidate_derivation_mismatch_is_rejected_before_navigation():
    app = run_offline_part_1(app_start())
    app.button(key="_select_direction_0").click().run(timeout=30)
    app.button(key="_derive_ideas").click().run(timeout=30)
    candidate = app.session_state["candidate_portfolio"][0]
    derivation = replace(
        app.session_state["current_idea_portfolio"][0],
        candidate_id="cand:conflicting",
    )
    state = {
        "selected_direction_id": app.session_state["selected_direction_id"],
        "selected_gap_id": app.session_state["selected_gap_id"],
        "selected_idea_id": "", "selected_idea_context": None,
        "_primary_step": PART_2,
    }
    before = dict(state)
    try:
        app_module.commit_idea_selection(
            candidate=candidate, derivation=derivation,
            direction=app.session_state["selected_direction_snapshot"],
            gap=app.session_state["selected_gap"],
            run=app.session_state["current_research_run"], state=state,
        )
    except ValueError as exc:
        assert "candidate and derivation IDs differ" in str(exc)
    else:
        raise AssertionError("mismatched selection unexpectedly committed")
    assert state == before


def test_selection_snapshot_round_trips_and_fingerprints_are_deterministic():
    app = run_offline_part_1(app_start())
    app.button(key="_select_direction_0").click().run(timeout=30)
    app.button(key="_derive_ideas").click().run(timeout=30)
    candidate = app.session_state["candidate_portfolio"][0]
    derivation = app.session_state["current_idea_portfolio"][0]
    direction = app.session_state["selected_direction_snapshot"]

    assert candidate_from_dict(candidate_to_dict(candidate)) == candidate
    assert derivation_from_dict(derivation_to_dict(derivation)) == derivation
    assert direction_from_dict(direction_to_dict(direction)) == direction
    state = {
        "selected_direction_id": direction.direction_id,
        "selected_gap_id": app.session_state["selected_gap_id"],
    }
    first = app_module.commit_idea_selection(
        candidate=candidate, derivation=derivation, direction=direction,
        gap=app.session_state["selected_gap"],
        run=app.session_state["current_research_run"], state=state,
    )
    second_state = dict(state)
    second = app_module.commit_idea_selection(
        candidate=candidate, derivation=derivation, direction=direction,
        gap=app.session_state["selected_gap"],
        run=app.session_state["current_research_run"], state=second_state,
    )
    assert first.candidate_fingerprint == second.candidate_fingerprint
    assert first.derivation_fingerprint == second.derivation_fingerprint


def test_purpose_change_invalidates_downstream_state():
    app = run_to_part_3(app_start())
    app.radio(key="_primary_step").set_value(PART_1).run()
    app.text_input(key="_purpose_task").set_value("dynamic clustering")
    app.radio(key="_purpose_search_mode").set_value(OFFLINE)
    app.button[0].click().run(timeout=30)

    assert app.session_state["selected_direction_id"] == ""
    assert app.session_state["current_idea_portfolio"] == []
    assert app.session_state["current_result_explanation"] is None


def test_empty_parts_are_actionable_not_blank():
    app = app_start()
    app.radio(key="_primary_step").set_value(PART_2).run()
    assert any("Select a research direction" in item.value for item in app.info)
    app.radio(key="_primary_step").set_value(PART_3).run()
    assert any("Select an idea" in item.value for item in app.info)


def test_same_direction_reuses_and_different_direction_rebuilds_external_state():
    app = run_offline_part_1(app_start())
    app.button(key="_select_direction_0").click().run(timeout=30)
    app.button(key="_derive_ideas").click().run(timeout=30)
    first = app.session_state["current_external_result"]
    first_identity = first.identity()

    app.radio(key="_primary_step").set_value(PART_1).run()
    app.button(key="_select_direction_0").click().run(timeout=30)
    assert app.session_state["current_external_result"].identity() == first_identity
    assert app.session_state["current_idea_portfolio"]

    app.radio(key="_primary_step").set_value(PART_1).run()
    app.button(key="_select_direction_1").click().run(timeout=30)
    assert app.session_state["current_external_result"] is None
    app.button(key="_derive_ideas").click().run(timeout=30)
    second = app.session_state["current_external_result"]
    assert second.identity() != first_identity
    assert second.papers
    visible = " ".join(
        str(item.value) for kind in (app.error, app.warning, app.info)
        for item in kind
    )
    assert "Complete Step 4" not in visible
    assert "('Novelty remains unverified.',)" not in visible


def test_two_distinct_directions_complete_all_three_parts():
    app = run_to_part_3(app_start())
    first_explanation = app.session_state["current_result_explanation"]
    first_direction = first_explanation.direction_id

    app.radio(key="_primary_step").set_value(PART_1).run()
    app.button(key="_select_direction_1").click().run(timeout=30)
    app.button(key="_derive_ideas").click().run(timeout=30)
    candidate_id = app.session_state["current_idea_portfolio"][0].candidate_id
    app.button(key=f"select_idea::{candidate_id}").click().run(timeout=30)

    second_explanation = app.session_state["current_result_explanation"]
    assert second_explanation.direction_id != first_direction
    assert second_explanation.proposed_change
    assert "argmin" in second_explanation.proposed_change
    assert second_explanation.modification_slot == "model_selection"
    assert len(app.get("graphviz_chart")) >= 3
    assert not app.exception
