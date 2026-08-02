"""Versioned, dependency-light normalization for persisted Streamlit state."""

from __future__ import annotations

from dataclasses import dataclass

from external_discovery_pipeline import ExternalDiscoveryResult

SESSION_STATE_SCHEMA_VERSION = "session-state-v2"
RESOLUTION_STATUSES = {
    "CURRENT", "MIGRATED", "PARTIALLY_MIGRATED", "IDENTITY_MISMATCH",
    "INVALID_SCHEMA", "UNRECOVERABLE", "ABSENT",
}


@dataclass
class ExternalResultResolution:
    status: str
    result: ExternalDiscoveryResult | None = None
    message: str = ""


def resolve_external_result(value: object, expected_identity: tuple[str, str, str] | None = None) -> ExternalResultResolution:
    if value is None:
        return ExternalResultResolution("ABSENT")
    if isinstance(value, dict) and value.get("schema_version") not in {None, "external-discovery-v2"}:
        return ExternalResultResolution("INVALID_SCHEMA", message=f"Unsupported external schema: {value.get('schema_version')}")
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
