"""Deployment and compatibility contract for optional final-result auditing."""

from __future__ import annotations

import ast
from dataclasses import asdict
import importlib
import os
from pathlib import Path
import subprocess
import sys

import pytest
from streamlit.testing.v1 import AppTest

from evaluation import EVALUATION_SCHEMA_VERSION, RESULT_AUDIT_VERSION
from evaluation.audit_models import AuditDimension, ResultAudit
from evaluation.capabilities import load_result_audit_capability
from evaluation.schemas import (
    AuditDimension as ExportedDimension,
    EvaluationReport,
    ResultAudit as ExportedAudit,
    StageFunnel,
)


ROOT = Path(__file__).resolve().parents[1]


def sample_audit() -> ResultAudit:
    dimension = AuditDimension(
        "user_problem_fit", 4, True, ["task preserved"], [], "none",
    )
    return ResultAudit(
        "audit:test", "run", "direction", "family", "candidate",
        "pipeline", "commit", "2026-08-01T00:00:00+00:00", "task",
        "LIVE", "lightweight", [dimension], [], {}, [], [], [], [], [],
        [], {}, {}, "PASS",
    )


def test_canonical_models_compatibility_identity_and_serialization():
    assert AuditDimension is ExportedDimension
    assert ResultAudit is ExportedAudit
    assert EVALUATION_SCHEMA_VERSION == "4"
    assert RESULT_AUDIT_VERSION == "1.0"
    audit = sample_audit()
    restored = ResultAudit.from_dict(audit.to_dict())
    assert restored == audit
    assert isinstance(restored.audit_dimensions[0], AuditDimension)


def test_result_audit_import_and_strict_capability():
    from evaluation.result_audit import audit_complete_result, audit_summary

    capability = load_result_audit_capability(strict=True)
    assert capability.available
    assert capability.audit_complete_result is audit_complete_result
    assert capability.audit_summary is audit_summary


def test_graceful_and_strict_capability_modes(monkeypatch):
    monkeypatch.setenv("RESULT_AUDIT_FORCE_IMPORT_ERROR", "1")
    capability = load_result_audit_capability(strict=False)
    assert not capability.available
    assert capability.error_type == "ImportError"
    assert "simulated incompatible" in capability.error_message
    with pytest.raises(ImportError):
        load_result_audit_capability(strict=True)


def test_app_has_no_top_level_result_audit_or_benchmark_import():
    tree = ast.parse((ROOT / "app.py").read_text())
    top_level = {
        node.module for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "evaluation.result_audit" not in top_level
    assert "evaluation.run_benchmark" not in top_level


def test_evaluation_report_accepts_canonical_result_audit():
    report = EvaluationReport(
        "task", "version", {}, {}, {}, [], [], [], [], [], [], [], [], [],
        [], StageFunnel(), {}, "none", [], [sample_audit()],
    )
    assert isinstance(report.result_audits[0], ResultAudit)


def test_result_audit_survives_legacy_general_schema_reload(monkeypatch):
    import evaluation.result_audit as result_module
    import evaluation.schemas as schemas

    monkeypatch.delattr(schemas, "AuditDimension")
    monkeypatch.delattr(schemas, "ResultAudit")
    reloaded = importlib.reload(result_module)
    assert reloaded.AuditDimension is AuditDimension
    assert reloaded.ResultAudit is ResultAudit


def test_hot_reload_order_preserves_startup_contract():
    import app
    import evaluation.result_audit as result_module
    import evaluation.schemas as schemas

    importlib.reload(schemas)
    importlib.reload(result_module)
    reloaded_app = importlib.reload(app)
    assert reloaded_app is app
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not at.exception
    assert at.title[0].value == "Discover directions / 发现方向"


def test_subprocess_degraded_startup_and_complete_workflow():
    code = r'''
from pathlib import Path
from streamlit.testing.v1 import AppTest

root = Path.cwd()
app = AppTest.from_file(str(root / "app.py"), default_timeout=30).run()
assert not app.exception
assert app.title[0].value == "Discover directions / 发现方向"
app.radio(key="_purpose_search_mode").set_value("Offline demonstration fixtures")
app.button[0].click().run(timeout=30)
assert app.session_state["current_direction_portfolio"]
app.button(key="_select_direction_0").click().run(timeout=30)
assert app.session_state["selected_direction_id"]
app.button(key="_derive_ideas").click().run(timeout=30)
assert app.session_state["current_idea_portfolio"]
candidate_id = app.session_state["current_idea_portfolio"][0].candidate_id
app.button(key=f"select_idea::{candidate_id}").click().run(timeout=30)
assert app.session_state["current_result_explanation"] is not None
assert app.session_state["current_result_audit"] is None
assert app.session_state["current_audit_build_result"].status == "UNAVAILABLE"
assert len(app.get("graphviz_chart")) >= 3
visible = " ".join(str(item.value) for group in (app.warning, app.info, app.error) for item in group)
assert "Optional result audit unavailable" in visible
assert "Traceback" not in visible
assert not app.exception
print("degraded three-part workflow: OK")
'''
    environment = dict(os.environ)
    environment["RESULT_AUDIT_FORCE_IMPORT_ERROR"] = "1"
    completed = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, env=environment,
        capture_output=True, text=True, timeout=90,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "degraded three-part workflow: OK" in completed.stdout
