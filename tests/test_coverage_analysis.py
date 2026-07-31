from coverage_analysis import (
    UNKNOWN, coverage_gap_to_signature, detect_coverage_gaps,
    extract_coverage_records, sparse_coverage_cube,
)
from models import Paper


def missingness_papers():
    return [
        Paper(f"p{i}", f"Random Forest missing data {i}",
              f"Random Forest evaluated under {condition} with accuracy.",
              2022 + i % 3, "openalex" if i % 2 else "arxiv")
        for i, condition in enumerate(["MCAR", "MCAR", "MAR", "MCAR", "MAR"])
    ]


def test_coverage_record_and_sparse_cube(purpose):
    purpose.current_failure = "missing features and MNAR"
    records = extract_coverage_records(missingness_papers(), purpose)
    assert records[0].field_provenance["algorithm"] == "explicit_rule"
    cube = sparse_coverage_cube(
        records, ("algorithm_family", "missingness_conditions", "metric_categories")
    )
    assert cube[("ensemble", "MCAR", "accuracy")] == 3


def test_zero_cell_is_not_automatically_gap(purpose):
    purpose.current_failure = "ordinary classification"
    records = extract_coverage_records(missingness_papers(), purpose)
    assert detect_coverage_gaps(records, purpose) == []


def test_relevant_persistent_omission_becomes_gap(purpose):
    purpose.current_failure = "missing features and MNAR"
    records = extract_coverage_records(missingness_papers(), purpose)
    gaps = detect_coverage_gaps(records, purpose)
    assert any(gap.missing_combination == {"missingness_conditions": "MNAR"}
               for gap in gaps)
    signature = coverage_gap_to_signature(gaps[0], purpose)
    assert signature.structural_gap_subtype == "coverage"
    assert signature.coverage_gap_id


def test_unknown_metadata_rejects_gap(purpose):
    purpose.current_failure = "missing features"
    papers = [Paper(str(i), "Unknown study", "MCAR accuracy.", 2025, "fixture")
              for i in range(5)]
    records = extract_coverage_records(papers, purpose)
    assert all(record.algorithm_family == UNKNOWN for record in records)
    assert detect_coverage_gaps(records, purpose, max_unknown_ratio=.2) == []
