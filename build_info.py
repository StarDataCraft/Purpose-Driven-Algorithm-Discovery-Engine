"""Deployment-safe build identity and source fingerprints."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import subprocess
from typing import Any

from evaluation import EVALUATION_SCHEMA_VERSION


APPLICATION_VERSION = "three-part-ux-v1"
PIPELINE_VERSION = "three-part-ux-v1"
RUN_MODEL_SCHEMA_VERSION = "run-models-v1"
UX_SCHEMA_VERSION = "selected-idea-context-v1"
FINGERPRINT_FILES = (
    "app.py", "ux_models.py", "primary_idea_selection.py", "models.py", "gap_consolidation.py",
    "idea_pipeline.py", "external_discovery_pipeline.py",
    "evaluation/schemas.py", "evaluation/audit_models.py",
    "evaluation/result_audit.py", "evaluation/capabilities.py",
)
DEPLOYMENT_MANIFEST = "deployment_manifest.json"


def resolve_commit_sha() -> str:
    for name in (
        "APP_COMMIT_SHA", "STREAMLIT_COMMIT_SHA", "GIT_COMMIT_SHA",
        "COMMIT_SHA", "RENDER_GIT_COMMIT", "VERCEL_GIT_COMMIT_SHA",
    ):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            check=False, timeout=2,
        ).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def source_fingerprints(root: Path | None = None) -> dict[str, str]:
    base = root or Path(__file__).resolve().parent
    values: dict[str, str] = {}
    for relative in FINGERPRINT_FILES:
        path = base / relative
        try:
            values[relative] = sha256(path.read_bytes()).hexdigest()
        except OSError:
            values[relative] = "missing"
    return values


def load_deployment_manifest(root: Path | None = None) -> dict[str, Any] | None:
    path = (root or Path(__file__).resolve().parent) / DEPLOYMENT_MANIFEST
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


def deployment_consistency(root: Path | None = None) -> dict[str, Any]:
    """Compare runtime sources with the deterministic release manifest."""
    manifest = load_deployment_manifest(root)
    if manifest is None:
        return {"status": "MANIFEST_UNAVAILABLE", "mismatches": []}
    current = source_fingerprints(root)
    expected = {
        "app.py": manifest.get("app_source_fingerprint", ""),
        "ux_models.py": manifest.get("ux_models_source_fingerprint", ""),
        "primary_idea_selection.py": manifest.get(
            "primary_idea_selection_source_fingerprint", ""
        ),
    }
    mismatches = [
        name for name, fingerprint in expected.items()
        if not fingerprint or current.get(name) != fingerprint
    ]
    return {
        "status": "SOURCE_MISMATCH" if mismatches else "CONSISTENT",
        "mismatches": mismatches,
    }


def build_information(engine_mode: str = "lightweight") -> dict[str, Any]:
    return {
        "application_version": APPLICATION_VERSION,
        "commit_sha": resolve_commit_sha(),
        "build_timestamp": os.environ.get("APP_BUILD_TIMESTAMP")
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python_version": platform.python_version(),
        "pipeline_version": PIPELINE_VERSION,
        "ux_schema_version": UX_SCHEMA_VERSION,
        "run_model_schema_version": RUN_MODEL_SCHEMA_VERSION,
        "evaluation_schema_version": EVALUATION_SCHEMA_VERSION,
        "engine_mode": engine_mode,
        "source_fingerprints": source_fingerprints(),
        "deployment_consistency": deployment_consistency(),
    }
