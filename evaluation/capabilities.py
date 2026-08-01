"""Lazy, typed capability boundary for optional result auditing."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import importlib.util
import os
from pathlib import Path
from typing import Any, Callable, Literal

from evaluation import RESULT_AUDIT_VERSION


AuditBuildStatus = Literal["COMPLETE", "UNAVAILABLE", "INCOMPLETE_INPUT", "FAILED"]


@dataclass(frozen=True)
class ResultAuditCapability:
    available: bool
    audit_complete_result: Callable[..., Any] | None
    audit_summary: Callable[..., dict[str, object]] | None
    error_type: str = ""
    error_message: str = ""
    module_path: str = ""
    schema_version: str = RESULT_AUDIT_VERSION


@dataclass(frozen=True)
class AuditBuildResult:
    status: AuditBuildStatus
    audit: Any | None
    user_message: str
    technical_error: dict[str, str]
    capability_version: str = RESULT_AUDIT_VERSION


def _module_path() -> str:
    try:
        spec = importlib.util.find_spec("evaluation.result_audit")
        return str(spec.origin) if spec and spec.origin else "unknown"
    except (ImportError, AttributeError, ValueError):
        return "unknown"


def _sanitize(message: str) -> str:
    value = " ".join(str(message).split())
    cwd = str(Path.cwd())
    return value.replace(cwd, "<application>")[:500]


def load_result_audit_capability(*, strict: bool = False) -> ResultAuditCapability:
    """Load auditing lazily; strict CI fails while production stays usable."""
    module_path = _module_path()
    try:
        if os.environ.get("RESULT_AUDIT_FORCE_IMPORT_ERROR") == "1":
            raise ImportError("simulated incompatible result-audit module")
        module = importlib.import_module("evaluation.result_audit")
        audit_function = getattr(module, "audit_complete_result")
        summary_function = getattr(module, "audit_summary")
        if not callable(audit_function) or not callable(summary_function):
            raise TypeError("result-audit callables do not satisfy the capability contract")
        return ResultAuditCapability(
            True, audit_function, summary_function,
            module_path=str(getattr(module, "__file__", module_path)),
        )
    except Exception as exc:
        if strict:
            raise
        return ResultAuditCapability(
            False, None, None, type(exc).__name__, _sanitize(str(exc)),
            module_path, RESULT_AUDIT_VERSION,
        )
