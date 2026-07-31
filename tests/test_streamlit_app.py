"""Regression tests for Streamlit widget/session-state ownership."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
CANDIDATE_PAGE = "7 · Candidate algorithms"
OFFLINE_MODE = "Offline demonstration fixtures"


def open_candidate_page(app: AppTest) -> AppTest:
    app.radio(key="_workflow_page").set_value(CANDIDATE_PAGE).run()
    return app


def select_offline_mode(app: AppTest) -> AppTest:
    app.radio(key="_purpose_search_mode").set_value(OFFLINE_MODE)
    return app


def test_goal_page_first_render_has_no_session_state_conflict():
    """The default route must render the purpose form without an exception."""
    app = AppTest.from_file(str(APP_PATH), default_timeout=30)

    app.run()

    assert not app.exception
    assert app.title[0].value == "Purpose contract"
    assert app.radio[0].value == "User-defined purpose"
    assert app.radio(key="_purpose_search_mode").value == "Live scholarly APIs"
    assert app.checkbox(key="_purpose_allow_cache").value is True
    assert app.checkbox(key="_purpose_allow_offline_fallback").value is False
    assert app.checkbox(key="_purpose_openalex").value is True
    assert app.checkbox(key="_purpose_arxiv").value is True
    assert app.text_input[0].value == "online learning"
    assert app.button[0].label == "Discover ML/DL gaps"
    assert app.session_state["engine_diagnostics"]["requested_mode"] == "lightweight"
    assert app.session_state["engine_diagnostics"]["active_mode"] == "lightweight"


def test_goal_form_submission_persists_domain_state_separately():
    """Submitting temporary form widgets may populate the persistent model key."""
    app = AppTest.from_file(str(APP_PATH), default_timeout=30)
    app.run()

    select_offline_mode(app)
    app.button[0].click().run()

    assert not app.exception
    assert app.session_state["purpose"] is not None
    assert app.session_state["purpose"].task == "online learning"
    assert app.session_state["_purpose_task"] == "online learning"
    assert app.session_state["current_research_run"].actual_search_mode == "OFFLINE_FIXTURE"
    assert app.session_state["current_research_run"].source_results[0].raw_returned_count == 5


def test_new_purpose_invalidates_downstream_state():
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    app.session_state["mechanisms"] = ["stale"]
    app.session_state["candidate_portfolio"] = ["stale"]
    select_offline_mode(app)
    app.button[0].click().run()

    assert not app.exception
    assert app.session_state["mechanisms"] == []
    assert app.session_state["candidate_portfolio"] == []
    assert app.session_state["current_research_run"].purpose_contract_id == (
        app.session_state["purpose"].purpose_id
    )


def test_mocked_live_run_displays_live_and_persists_across_rerun():
    wrapper = """
import app as target
from models import Paper
from research_runs import ResearchRun, SourceRetrievalResult, paper_provenance

def mocked_retrieve(purpose, queries, **kwargs):
    papers = [
        Paper(
            f"mock:{index}", f"Random Forest recurring drift study {index}",
            "Random forest remains challenging under recurring concept drift. "
            "Recovery after recurrence has adaptation delay.",
            2025, "openalex"
        )
        for index in range(5)
    ]
    for index, paper in enumerate(papers):
        paper_provenance(
            paper, "live_openalex", f"q:{index}", f"request:{index}",
            rank=index + 1,
        )
    run = ResearchRun.create(
        purpose.purpose_id, "LIVE", "lightweight",
        purpose.publication_window,
    )
    run.live_request_attempted = True
    run.raw_paper_count = len(papers)
    run.ml_queries = list(queries)
    run.source_results = [SourceRetrievalResult(
        source="openalex", source_type="scholarly_api",
        queries_attempted=list(queries), request_count=1, success_count=1,
        raw_returned_count=5, unique_returned_count=5,
    )]
    run.finalize_from_papers(papers)
    return papers, run

target.retrieve_corpus = mocked_retrieve
target.main()
"""
    app = AppTest.from_string(wrapper, default_timeout=30).run()
    app.button[0].click().run(timeout=30)

    assert not app.exception
    assert app.session_state["current_research_run"].actual_search_mode == "LIVE"
    run_id = app.session_state["current_research_run"].run_id
    assert any("LIVE LITERATURE RUN" in success.value for success in app.success)

    app.run()

    assert app.session_state["current_research_run"].run_id == run_id
    assert app.session_state["current_research_run"].actual_search_mode == "LIVE"

    app.radio(key="_workflow_page").set_value(CANDIDATE_PAGE).run()
    app.button(key="_candidate_generate_end_to_end").click().run()
    assert app.session_state["current_research_run"].actual_search_mode == "LIVE"
    assert app.session_state["current_external_run"] is None
    assert app.session_state["candidate_run_diagnostics"]["status"] == "failure"
    assert "Complete Step 4" in app.session_state["candidate_run_diagnostics"]["error"]


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
    select_offline_mode(app)
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
    select_offline_mode(app)
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
    assert any(
        "OFFLINE DEMONSTRATION" in warning.value for warning in app.warning
    )
    source_table = app.dataframe[0].value
    assert int(source_table.iloc[0]["raw returned"]) == 5
    assert int(source_table.iloc[0]["unique returned"]) == 5

    app.session_state["mechanisms"] = ["stale mechanism"]
    app.session_state["candidate_portfolio"] = ["stale candidate"]
    app.button(key="_gap_radar_submit").click().run()
    assert app.session_state["mechanisms"] == []
    assert app.session_state["candidate_portfolio"] == []
    app.radio(key="_workflow_page").set_value("3 · Gap evidence").run()

    assert not app.exception
    assert app.title[0].value == "Gap evidence"
    assert app.session_state["selected_gap"] is not None

    app.radio(key="_workflow_page").set_value(
        "4 · External mechanism search"
    ).run()
    assert not app.exception
    assert "Normalized cross-domain problem signature" in [
        item.value for item in app.subheader
    ]
    query_text = " ".join(item.value for item in app.code).casefold()
    assert "stationary distribution" not in query_text
    assert "online accuracy" not in query_text
