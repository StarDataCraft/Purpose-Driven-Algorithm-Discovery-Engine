"""Deployment-safe build identity and source fingerprints."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import os
from pathlib import Path
import platform
import subprocess
from typing import Any

from evaluation import EVALUATION_SCHEMA_VERSION


APPLICATION_VERSION = "three-part-ux-v1"
PIPELINE_VERSION = "three-part-ux-v1"
RUN_MODEL_SCHEMA_VERSION = "run-models-v1"
FINGERPRINT_FILES = (
    "app.py", "evaluation/schemas.py", "evaluation/audit_models.py",
    "evaluation/result_audit.py", "evaluation/capabilities.py",
)


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


def build_information(engine_mode: str = "lightweight") -> dict[str, Any]:
    return {
        "application_version": APPLICATION_VERSION,
        "commit_sha": resolve_commit_sha(),
        "build_timestamp": os.environ.get("APP_BUILD_TIMESTAMP")
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python_version": platform.python_version(),
        "pipeline_version": PIPELINE_VERSION,
        "run_model_schema_version": RUN_MODEL_SCHEMA_VERSION,
        "evaluation_schema_version": EVALUATION_SCHEMA_VERSION,
        "engine_mode": engine_mode,
        "source_fingerprints": source_fingerprints(),
    }
