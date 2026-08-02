"""Linux/cloud-equivalent startup contract for the lightweight application."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import platform
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from run_models import ResearchRun, SelectedGapSnapshot, StageRun
from search_runs import ResearchRun as SearchExportedResearchRun
from research_runs import ResearchRun as LegacyExportedResearchRun
from streamlit.testing.v1 import AppTest
from build_info import build_information
from evaluation.audit_models import AuditDimension, ResultAudit
from evaluation.capabilities import load_result_audit_capability
from evaluation.schemas import (
    AuditDimension as ExportedDimension,
    ResultAudit as ExportedAudit,
)
import gap_consolidation
import models
import ux_models
from ux_models import (
    PIPELINE_VERSION, SELECTED_IDEA_SCHEMA_VERSION, SelectedIdeaContext,
    build_direction_portfolio, build_idea_derivation, build_idea_explanation,
    candidate_from_dict, candidate_modification, candidate_to_dict,
    derivation_from_dict, derivation_to_dict, direction_from_dict,
    direction_to_dict, gap_from_dict, gap_to_dict, selected_idea_fingerprints,
)


def main() -> None:
    required_ux_symbols = (
        PIPELINE_VERSION, SELECTED_IDEA_SCHEMA_VERSION, SelectedIdeaContext,
        build_direction_portfolio, build_idea_derivation,
        build_idea_explanation, candidate_from_dict, candidate_modification,
        candidate_to_dict, derivation_from_dict, derivation_to_dict,
        direction_from_dict, direction_to_dict, gap_from_dict, gap_to_dict,
        selected_idea_fingerprints,
    )
    assert all(symbol is not None for symbol in required_ux_symbols)
    assert SearchExportedResearchRun is ResearchRun
    assert LegacyExportedResearchRun is ResearchRun
    assert AuditDimension is ExportedDimension
    assert ResultAudit is ExportedAudit
    from evaluation.result_audit import audit_complete_result, audit_summary
    assert callable(audit_complete_result) and callable(audit_summary)
    capability = load_result_audit_capability(strict=True)
    assert capability.available
    app_spec = importlib.util.find_spec("app")
    evaluation_spec = importlib.util.find_spec("evaluation")
    schemas_spec = importlib.util.find_spec("evaluation.schemas")
    models_spec = importlib.util.find_spec("evaluation.audit_models")
    audit_spec = importlib.util.find_spec("evaluation.result_audit")
    run_spec = importlib.util.find_spec("run_models")
    search_spec = importlib.util.find_spec("search_runs")
    print("app module:", app_spec.origin if app_spec else None)
    print("evaluation package:", evaluation_spec.origin if evaluation_spec else None)
    print("schemas module:", schemas_spec.origin if schemas_spec else None)
    print("audit_models module:", models_spec.origin if models_spec else None)
    print("result_audit module:", audit_spec.origin if audit_spec else None)
    print("canonical run models:", run_spec.origin if run_spec else None)
    print("search_runs compatibility module:", search_spec.origin if search_spec else None)
    import app
    info = build_information("lightweight")
    print("python version:", platform.python_version())
    print("working directory:", Path.cwd())
    print("ux_models module:", ux_models.__file__)
    print("models module:", models.__file__)
    print("gap_consolidation module:", gap_consolidation.__file__)
    print("app module file:", app.__file__)
    print("commit SHA:", info["commit_sha"])
    print("source fingerprints:", {
        name: value[:8] for name, value in info["source_fingerprints"].items()
    })

    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    if at.exception:
        raise RuntimeError(f"Streamlit startup exceptions: {at.exception}")
    assert at.title and at.title[0].value == "Discover directions / 发现方向"
    assert len(at.sidebar.radio(key="_primary_step").options) == 3
    sidebar_text = " ".join(str(item.value) for item in at.sidebar.caption)
    assert "Build:" in sidebar_text
    assert "Pipeline: three-part-ux-v1" in sidebar_text
    assert "UX schema: selected-idea-context-v1" in sidebar_text
    assert "Source fingerprint: c1f35d26" in sidebar_text
    assert "Deployment consistency: CONSISTENT" in sidebar_text
    page_captions = " ".join(str(item.value) for item in at.caption)
    assert "Running build:" in page_captions
    assert "app.py c1f35d26" in page_captions
    at.sidebar.selectbox(key="_research_tool").set_value("Build information")
    at.run(timeout=30)
    assert not at.exception
    visible = " ".join(
        str(item.value) for group in (at.header, at.subheader, at.markdown)
        for item in group
    )
    assert "Startup capability health" in visible
    assert "Build identity" in visible
    assert "Source fingerprints" in visible
    assert info["commit_sha"]
    assert all(
        value != "missing" for value in info["source_fingerprints"].values()
    )
    at.sidebar.selectbox(key="_research_tool").set_value("None")
    at.run(timeout=30)
    at.radio(key="_purpose_search_mode").set_value(
        "Offline demonstration fixtures"
    )
    at.button[0].click().run(timeout=30)
    assert at.session_state["current_direction_portfolio"]
    at.button(key="_select_direction_0").click().run(timeout=30)
    assert at.session_state["selected_direction_id"]
    at.button(key="_derive_ideas").click().run(timeout=30)
    assert len(at.session_state["current_idea_portfolio"]) >= 2
    first_id = at.session_state["current_idea_portfolio"][0].candidate_id
    selector = at.radio(key="selected_idea_choice")
    assert len(selector.options) >= 2
    at.button(key="_commit_selected_idea").click().run(timeout=30)
    context = at.session_state["selected_idea_context"]
    assert isinstance(context, dict) and context["candidate_id"] == first_id
    assert context["candidate_snapshot"]["candidate_id"] == first_id
    assert context["derivation_snapshot"]["candidate_id"] == first_id
    assert at.session_state["current_result_explanation"].candidate_id == first_id
    headings = " ".join(item.value for item in at.header)
    assert at.session_state["current_result_explanation"].title in headings
    assert "BEFORE → CHANGE → EXPECTED RESULT" in headings
    rendered = " ".join(str(item.value) for item in at.markdown)
    assert all(label in rendered for label in ("BEFORE", "CHANGE", "EXPECTED RESULT"))
    assert not any("Select an idea in Part 2." in item.value for item in at.info)
    assert at.session_state["active_primary_step"] == "3 · Explain the idea / 解释新想法"
    assert not at.exception

    part_2 = "2 · Analyze the gap / 分析 Gap"
    at.radio(key="_primary_step").set_value(part_2).run(timeout=30)
    assert at.session_state["current_idea_portfolio"]
    second_id = at.session_state["current_idea_portfolio"][1].candidate_id
    selector = at.radio(key="selected_idea_choice")
    selector.set_value(selector.options[1]).run(timeout=30)
    at.button(key="_commit_selected_idea").click().run(timeout=30)
    assert at.session_state["selected_idea_context"]["candidate_id"] == second_id
    assert at.session_state["current_result_explanation"].candidate_id == second_id
    assert first_id != second_id
    assert not at.exception
    print("deployment smoke test: OK")


if __name__ == "__main__":
    main()
