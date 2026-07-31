from models import Paper
from paper_fetchers import deduplicate_papers, fetch_papers


def test_deduplication_prefers_identity_keys():
    papers = [
        Paper("1", "Same Study", "abstract", 2024, "openalex", doi="10/x", provenance=["openalex"]),
        Paper("2", "Same Study", "abstract", 2024, "arxiv", doi="10/x", provenance=["arxiv"]),
    ]
    unique = deduplicate_papers(papers)
    assert len(unique) == 1
    assert set(unique[0].provenance) == {"openalex", "arxiv"}


def test_partial_source_failure():
    def good(*args):
        return [Paper("1", "Paper", "However, a limitation remains unresolved.", 2025, "good")]

    def bad(*args):
        raise ValueError("offline")

    papers, failures = fetch_papers("q", ["good", "bad"], adapters={"good": good, "bad": bad})
    assert len(papers) == 1
    assert "bad" in failures
