"""Regression tests for Streamlit widget/session-state ownership."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
CANDIDATE_PAGE = "7 · Candidate algorithms"


def open_candidate_page(app: AppTest) -> AppTest:
    app.radio(key="_workflow_page").set_value(CANDIDATE_PAGE).run()
    return app


def test_goal_page_first_render_has_no_session_state_conflict():
    """The default route must render the purpose form without an exception."""
    app = AppTest.from_file(str(APP_PATH), default_timeout=30)

    app.run()

    assert not app.exception
    assert app.title[0].value == "Purpose contract"
    assert app.radio[0].value == "User-defined purpose"
    assert app.text_input[0].value == "online learning"
    assert app.button[0].label == "Discover ML/DL gaps"
    assert app.session_state["engine_diagnostics"]["requested_mode"] == "lightweight"
    assert app.session_state["engine_diagnostics"]["active_mode"] == "lightweight"


def test_goal_form_submission_persists_domain_state_separately():
    """Submitting temporary form widgets may populate the persistent model key."""
    app = AppTest.from_file(str(APP_PATH), default_timeout=30)
    app.run()

    app.button[0].click().run()

    assert not app.exception
    assert app.session_state["purpose"] is not None
    assert app.session_state["purpose"].task == "online learning"
    assert app.session_state["_purpose_task"] == "online learning"
    assert app.session_state["ml_search_diagnostics"].search_mode == "OFFLINE FIXTURE"
    assert app.session_state["ml_search_diagnostics"].returned_by_source


def test_candidate_page_without_prerequisites_is_actionable():
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    open_candidate_page(app)

    assert not app.exception
    checklist = " ".join(item.value for item in app.markdown)
    assert "Candidate generation prerequisites" in " ".join(
        item.value for item in app.subheader
    )
    assert "✗ **Purpose contract**" in checklist
    assert any(
        button.label == "Complete Step 1: Goal setup" for button in app.button
    )


def test_candidate_end_to_end_offline_renders_and_persists():
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    app.button[0].click().run()
    open_candidate_page(app)

    app.button(key="_candidate_generate_end_to_end").click().run(timeout=30)

    assert not app.exception
    assert app.session_state["candidate_portfolio"]
    expected_ids = [
        candidate.candidate_id
        for candidate in app.session_state["candidate_portfolio"]
    ]
    assert app.session_state["candidate_run_diagnostics"]["status"] == "success"
    assert app.session_state["candidate_run_diagnostics"]["retrieval_mode"] == "OFFLINE FIXTURE"
    assert any(
        candidate.candidate_name in expander.label
        for candidate in app.session_state["candidate_portfolio"]
        for expander in app.expander
    )

    app.button(key="_candidate_regenerate").click().run(timeout=30)

    assert not app.exception
    assert app.session_state["candidate_portfolio"]
    assert [
        candidate.candidate_id
        for candidate in app.session_state["candidate_portfolio"]
    ] == expected_ids

    app.run()

    assert [
        candidate.candidate_id
        for candidate in app.session_state["candidate_portfolio"]
    ] == expected_ids


def test_candidate_empty_portfolio_displays_rejections():
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    app.session_state["candidate_run_diagnostics"] = {
        "status": "empty", "sampled_paths": 4, "surviving_candidates": 0,
        "algorithm_families": 0,
        "rejections": {"mechanism-slot incompatibility": 4},
        "rejected_paths": [{"reasons": ["mechanism-slot incompatibility"]}],
        "failed_stage": "", "error": "",
    }
    open_candidate_page(app)

    assert any(
        warning.value == "No candidates survived validation."
        for warning in app.warning
    )
    assert any("mechanism-slot incompatibility" in str(frame.value)
               for frame in app.dataframe)


def test_candidate_failure_displays_stage_and_error():
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    app.session_state["candidate_run_diagnostics"] = {
        "status": "failure", "sampled_paths": 0, "surviving_candidates": 0,
        "algorithm_families": 0, "rejections": {}, "rejected_paths": [],
        "failed_stage": "candidate synthesis", "error": "controlled failure",
    }
    open_candidate_page(app)

    assert any(
        "candidate synthesis" in error.value
        and "controlled failure" in error.value
        for error in app.error
    )


def test_gap_radar_renders_structural_views_from_fixture():
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    app.button[0].click().run()
    app.radio(key="_workflow_page").set_value(
        "2 · Latest ML/DL gap radar"
    ).run(timeout=30)

    assert not app.exception
    labels = [expander.label for expander in app.expander]
    assert any("Gap engine mode: LIGHTWEIGHT" in info.value for info in app.info)
    assert app.multiselect(key="_gap_type_filters")
    assert "Coverage Matrix" in labels
    assert "Assumption Mismatch view" in labels
    assert "Contradictory evidence view" in labels
    assert "Research Clusters" in labels
    assert app.session_state["coverage_records"]
    assert app.session_state["assumption_mismatches"]
    assert any(
        gap.structural_gap_subtype == "assumption_mismatch"
        for gap in app.session_state["gaps"]
    )

    app.button(key="_gap_radar_submit").click().run()
    app.radio(key="_workflow_page").set_value("3 · Gap evidence").run()

    assert not app.exception
    assert app.title[0].value == "Gap evidence"
    assert app.session_state["selected_gap"] is not None
