from contradiction_analysis import detect_contradictory_evidence
from coverage_analysis import extract_coverage_records
from models import Paper


def test_only_comparable_claims_form_contradiction(purpose):
    papers = [
        Paper("a", "Random Forest drift benchmark",
              "Random Forest remains robust under recurring concept drift with online accuracy benchmark.",
              2024, "openalex"),
        Paper("b", "Random Forest drift benchmark",
              "Random Forest degrades under recurring concept drift in online accuracy benchmark.",
              2025, "arxiv"),
    ]
    records = extract_coverage_records(papers, purpose)
    gaps = detect_contradictory_evidence(papers, records)
    assert len(gaps) == 1
    assert gaps[0].supporting_paper_ids == ["a"]


def test_materially_different_settings_do_not_merge(purpose):
    papers = [
        Paper("a", "Random Forest drift", "Random Forest robust under recurring drift with accuracy.", 2024, "x"),
        Paper("b", "K-means density", "K-means fails under heterogeneous density with ARI.", 2025, "y"),
    ]
    assert detect_contradictory_evidence(
        papers, extract_coverage_records(papers, purpose)
    ) == []
