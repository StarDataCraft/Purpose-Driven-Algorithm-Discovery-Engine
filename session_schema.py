"""Versioned, dependency-light normalization for persisted Streamlit state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from external_discovery_pipeline import ExternalDiscoveryResult

SESSION_SCHEMA_API_VERSION = "session-schema-api-v2"
SESSION_STATE_SCHEMA_VERSION = "session-state-v2"
RESOLUTION_STATUSES = {
    "CURRENT", "MIGRATED", "PARTIALLY_MIGRATED", "IDENTITY_MISMATCH",
    "INVALID_SCHEMA", "UNRECOVERABLE", "ABSENT",
}


def normalize_primary_selection_record(value: object) -> dict[str, object] | None:
    """Conservatively migrate old selection records without inventing maturity."""
    if not isinstance(value, dict):
        return None
    record = dict(value)
    status = str(record.get("status", "FAILED"))
    record.setdefault("scientific_assessments", record.get("scientific_gate_results", {}))
    record.setdefault("fatal_rejections", record.get("rejection_reasons", {}))
    record.setdefault("maturity_limiters", {})
    record.setdefault("maturity_distribution", {})
    if status == "SELECTED":
        record.setdefault("selected_maturity_level", "LEGACY_SELECTED_UNASSESSED")
    elif status == "NO_CANDIDATE_PASSED":
        record["status"] = "LEGACY_NO_CANDIDATE_PASSED"
        record.setdefault("selected_maturity_level", "LEGACY_UNASSESSED")
    return record


@dataclass
class ExternalResultResolution:
    status: str
    result: "ExternalDiscoveryResult | None" = None
    message: str = ""


def resolve_external_result(
    value: Any,
    expected_identity: tuple[str, str, str] | None = None,
) -> ExternalResultResolution:
    if value is None:
        return ExternalResultResolution("ABSENT")
    if isinstance(value, dict) and value.get("schema_version") not in {None, "external-discovery-v2"}:
        return ExternalResultResolution("INVALID_SCHEMA", message=f"Unsupported external schema: {value.get('schema_version')}")
    from external_discovery_pipeline import ExternalDiscoveryResult

    try:
        result = ExternalDiscoveryResult.from_dict(value)
    except (TypeError, ValueError, KeyError, AttributeError) as exc:
        return ExternalResultResolution("UNRECOVERABLE", message=str(exc))
    if expected_identity and result.identity() != expected_identity:
        return ExternalResultResolution("IDENTITY_MISMATCH", result, "Result belongs to another run, direction, or gap")
    if result.migration_warnings:
        return ExternalResultResolution("PARTIALLY_MIGRATED", result, "; ".join(result.migration_warnings))
    if result.migration_provenance != "current":
        return ExternalResultResolution("MIGRATED", result)
    return ExternalResultResolution("CURRENT", result)
