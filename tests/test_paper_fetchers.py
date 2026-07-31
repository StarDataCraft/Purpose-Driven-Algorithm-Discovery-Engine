from models import Paper
from paper_fetchers import (
    FetchDiagnostics,
    deduplicate_papers,
    fetch_papers,
    fetch_papers_cached_detailed,
    fetch_papers_detailed,
)


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


def test_live_diagnostics_report_source_and_dedup_counts():
    def first(*args):
        return [Paper("1", "Same Paper", "abstract", 2025, "openalex",
                      provenance=["openalex"])]

    def second(*args):
        return [Paper("2", "Same Paper", "abstract", 2025, "arxiv",
                      provenance=["arxiv"])]

    papers, diagnostics = fetch_papers_detailed(
        "query", ["openalex", "arxiv"], adapters={
            "openalex": first, "arxiv": second
        }
    )

    assert diagnostics.search_mode == "LIVE"
    assert diagnostics.returned_by_source == {"openalex": 1, "arxiv": 1}
    assert diagnostics.number_before_deduplication == 2
    assert diagnostics.number_after_deduplication == 1
    assert len(papers) == 1


def test_cache_mode_and_force_fresh_bypass(monkeypatch, tmp_path):
    calls = []

    def live_fetch(query, sources, max_results, start_year, end_year):
        calls.append(query)
        papers = [Paper("1", "Paper", "abstract", 2025, "openalex",
                        provenance=["openalex"])]
        diagnostics = FetchDiagnostics(
            "LIVE", sources, [query], "2026-01-01T00:00:00+00:00",
            {"openalex": 1}, 1, 1, (start_year, end_year), {},
        )
        return papers, diagnostics

    monkeypatch.setattr("paper_fetchers.fetch_papers_detailed", live_fetch)
    first, first_diagnostics = fetch_papers_cached_detailed(
        "query", ["openalex"], cache_directory=tmp_path
    )
    cached, cached_diagnostics = fetch_papers_cached_detailed(
        "query", ["openalex"], cache_directory=tmp_path
    )
    fresh, fresh_diagnostics = fetch_papers_cached_detailed(
        "query", ["openalex"], cache_directory=tmp_path, force_fresh=True
    )

    assert first_diagnostics.search_mode == "LIVE"
    assert cached_diagnostics.search_mode == "CACHE"
    assert cached_diagnostics.cache_created_at
    assert fresh_diagnostics.search_mode == "LIVE"
    assert first == cached == fresh
    assert calls == ["query", "query"]
