"""Linux/cloud-equivalent startup contract for the lightweight application."""

from __future__ import annotations

import importlib.util
from pathlib import Path
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


def main() -> None:
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
    import app  # noqa: F401

    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    if at.exception:
        raise RuntimeError(f"Streamlit startup exceptions: {at.exception}")
    assert at.title and at.title[0].value == "Discover directions / 发现方向"
    assert len(at.sidebar.radio(key="_primary_step").options) == 3
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
    info = build_information("lightweight")
    assert info["commit_sha"]
    assert all(
        value != "missing" for value in info["source_fingerprints"].values()
    )
    print("deployment smoke test: OK")


if __name__ == "__main__":
    main()
