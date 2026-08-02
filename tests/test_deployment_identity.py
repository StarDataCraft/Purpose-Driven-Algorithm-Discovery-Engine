"""Regression coverage for visible and deterministic deployment identity."""

from __future__ import annotations

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

import build_info
from scripts.verify_deployed_build import verify_html


ROOT = Path(__file__).resolve().parents[1]


def test_manifest_matches_runtime_sources():
    manifest = json.loads(
        (ROOT / "deployment_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["expected_entrypoint"] == "app.py"
    assert manifest["expected_branch"] == "main"
    assert build_info.deployment_consistency(ROOT) == {
        "status": "CONSISTENT",
        "mismatches": [],
    }


def test_build_identity_is_visible_on_first_render():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception
    sidebar_text = " ".join(str(item.value) for item in app.sidebar.caption)
    assert "Build:" in sidebar_text
    assert "Pipeline: three-part-ux-v1" in sidebar_text
    assert "UX schema: selected-idea-context-v1" in sidebar_text
    assert "Source fingerprint: c1f35d26" in sidebar_text
    assert "Deployment consistency: CONSISTENT" in sidebar_text
    page_text = " ".join(str(item.value) for item in app.caption)
    assert "Running build:" in page_text
    assert "app.py c1f35d26" in page_text


def test_build_identity_survives_missing_git_metadata(monkeypatch):
    for name in (
        "APP_COMMIT_SHA", "STREAMLIT_COMMIT_SHA", "GIT_COMMIT_SHA",
        "COMMIT_SHA", "RENDER_GIT_COMMIT", "VERCEL_GIT_COMMIT_SHA",
    ):
        monkeypatch.delenv(name, raising=False)

    def unavailable(*args, **kwargs):
        raise OSError("git is unavailable")

    monkeypatch.setattr(build_info.subprocess, "run", unavailable)
    info = build_info.build_information()
    assert info["commit_sha"] == "unknown"
    assert info["source_fingerprints"]["app.py"].startswith("c1f35d26")
    assert info["deployment_consistency"]["status"] == "CONSISTENT"


def test_semantic_verifier_rejects_the_obsolete_instruction():
    current = verify_html(
        "Workflow status / 流程状态 Continue to explanation / 进入想法解释"
    )
    assert current["status"] == "MATCH"
    stale = verify_html(
        "Workflow status / 流程状态 Continue to explanation / 进入想法解释 "
        "Select an idea in Part 2."
    )
    assert stale["status"] == "SEMANTIC_MISMATCH"
    assert stale["forbidden_markers_found"] == ["Select an idea in Part 2."]
