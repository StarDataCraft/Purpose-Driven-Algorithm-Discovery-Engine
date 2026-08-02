from types import SimpleNamespace

from query_generation import DOMAIN_SELECTION_SCHEMA_VERSION, normalize_domain_selection
from session_schema import resolve_external_result


def legacy_selection(**overrides):
    values = dict(
        domain="control theory", matched_problem_roles=["feedback"],
        relevance_score=0.8, reasons=["structural match"],
        missing_correspondence=["labels"], selected=True,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_exact_legacy_domain_object_migrates_missing_scores_to_none():
    result = normalize_domain_selection(legacy_selection())
    assert result.schema_version == DOMAIN_SELECTION_SCHEMA_VERSION
    assert result.unmatched_required_roles == []
    assert result.problem_topology_compatibility is None
    assert result.analogy_risk is None
    assert result.migration_warnings


def test_current_domain_dict_round_trips():
    first = normalize_domain_selection(legacy_selection())
    second = normalize_domain_selection(first.to_dict())
    assert second.to_dict() == first.to_dict()


def test_absent_and_invalid_external_schema_are_explicit():
    assert resolve_external_result(None).status == "ABSENT"
    assert resolve_external_result({"schema_version": "future-v99"}).status == "INVALID_SCHEMA"


def test_malformed_domain_record_is_rejected_without_attribute_error():
    try:
        normalize_domain_selection({"selected": True})
    except ValueError as exc:
        assert "no domain" in str(exc)
    else:
        raise AssertionError("malformed record must not be accepted")
