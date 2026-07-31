"""Regression tests for Streamlit widget/session-state ownership."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def test_goal_page_first_render_has_no_session_state_conflict():
    """The default route must render the purpose form without an exception."""
    app = AppTest.from_file(str(APP_PATH), default_timeout=30)

    app.run()

    assert not app.exception
    assert app.title[0].value == "Purpose contract"
    assert app.radio[0].value == "User-defined purpose"
    assert app.text_input[0].value == "online learning"
    assert app.button[0].label == "Discover ML/DL gaps"


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
