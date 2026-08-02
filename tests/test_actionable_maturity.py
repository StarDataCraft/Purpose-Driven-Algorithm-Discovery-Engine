"""Canonical maturity, operator-plan, state, and evidence invariants."""

from __future__ import annotations

import pytest

from external_discovery_pipeline import external_evidence_count_invariants
from idea_maturity import (
    AssessmentSeverity, IdeaMaturityLevel, issue, maturity_value,
)
from session_schema import normalize_primary_selection_record
from ux_models import reconcile_direction_limitations


def test_canonical_maturity_order_and_typed_issue_contract():
    assert [maturity_value(level) for level in IdeaMaturityLevel] == [0, 1, 2, 3]
    record = issue(
        "prior_art_incomplete", AssessmentSeverity.MAJOR_LIMITER,
        "Targeted prior-art search remains incomplete.",
        evidence=("query:mechanism-slot",), consequence="Novelty is unverified.",
        repair_option="Complete the targeted search.",
    )
    assert record.severity == AssessmentSeverity.MAJOR_LIMITER
    assert record.evidence and record.repair_option


def test_external_mechanism_evidence_must_be_relevant_subset():
    assert external_evidence_count_invariants(10, 4, 3)[
        "operational_mechanism_evidence_paper_count"
    ] == 3
    with pytest.raises(ValueError, match="subset"):
        external_evidence_count_invariants(10, 0, 1)


def test_stale_unknown_family_limitation_is_removed_after_binding():
    result = reconcile_direction_limitations(
        "online ensemble",
        ("algorithm family is unknown", "prior-art search remains incomplete"),
    )
    assert "algorithm family is unknown" not in result
    assert result == ("prior-art search remains incomplete",)


def test_legacy_binary_selection_is_not_reinterpreted_as_maturity_assessment():
    migrated = normalize_primary_selection_record({
        "status": "NO_CANDIDATE_PASSED", "rejection_reasons": {"c1": ["legacy"]},
    })
    assert migrated["status"] == "LEGACY_NO_CANDIDATE_PASSED"
    assert migrated["selected_maturity_level"] == "LEGACY_UNASSESSED"
    assert migrated["scientific_assessments"] == {}
