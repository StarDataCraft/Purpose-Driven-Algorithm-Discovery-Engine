from pathlib import Path

from models import Paper
from retrieval_service import retrieve_corpus


def paper(identifier, source):
    return Paper(
        identifier, f"Study {identifier}",
        f"recurring concept drift recovery evidence from {source}",
        2025, source,
    )


def test_both_sources_succeed_is_live(tmp_path, purpose):
    adapters = {
        "openalex": lambda *args: [paper("oa", "openalex")],
        "arxiv": lambda *args: [paper("ax", "arxiv")],
    }
    papers, run = retrieve_corpus(
        purpose, ["recurring drift"], adapters=adapters,
        cache_directory=tmp_path,
    )
    assert run.actual_search_mode == "LIVE"
    assert run.live_request_attempted and run.live_request_succeeded
    assert len(papers) == 2
    assert {item.raw_returned_count for item in run.source_results} == {1}


def test_one_source_failure_remains_live(tmp_path, purpose):
    def fail(*args):
        raise ValueError("arXiv unavailable")

    papers, run = retrieve_corpus(
        purpose, ["recurring drift"], adapters={
            "openalex": lambda *args: [paper("oa", "openalex")],
            "arxiv": fail,
        }, cache_directory=tmp_path,
    )
    assert papers
    assert run.actual_search_mode == "LIVE"
    assert "arxiv" in run.source_failures


def test_failures_use_valid_live_cache(tmp_path, purpose):
    retrieve_corpus(
        purpose, ["recurring drift"], sources=["openalex"],
        adapters={"openalex": lambda *args: [paper("oa", "openalex")]},
        cache_directory=tmp_path,
    )

    papers, run = retrieve_corpus(
        purpose, ["recurring drift"], requested_mode="CACHE",
        sources=["openalex"], cache_directory=tmp_path,
    )
    assert papers
    assert run.actual_search_mode == "CACHE"
    assert run.cache_used


def test_failures_without_cache_are_failed(tmp_path, purpose):
    papers, run = retrieve_corpus(
        purpose, ["recurring drift"], sources=["openalex"],
        adapters={"openalex": lambda *args: (_ for _ in ()).throw(
            ValueError("offline")
        )}, cache_directory=tmp_path, allow_offline_fallback=False,
    )
    assert papers == []
    assert run.actual_search_mode == "FAILED"
    assert not run.fallback_occurred


def test_authorized_fallback_is_explicit_fixture(tmp_path, purpose, ml_papers):
    papers, run = retrieve_corpus(
        purpose, ["recurring drift"], sources=["openalex"],
        adapters={"openalex": lambda *args: (_ for _ in ()).throw(
            ValueError("offline")
        )}, cache_directory=tmp_path, allow_offline_fallback=True,
        fixture_loader=lambda: ml_papers,
        fixture_path="data/offline_fixtures/ml_papers.json",
    )
    assert papers
    assert run.actual_search_mode == "OFFLINE_FIXTURE"
    assert run.fallback_occurred
    assert "DEMONSTRATION ONLY" in run.warnings[0]


def test_explicit_fixture_is_not_fallback(tmp_path, purpose, ml_papers):
    papers, run = retrieve_corpus(
        purpose, ["recurring drift"], requested_mode="OFFLINE_FIXTURE",
        cache_directory=tmp_path, fixture_loader=lambda: ml_papers,
        fixture_path="data/offline_fixtures/ml_papers.json",
    )
    assert papers
    assert run.actual_search_mode == "OFFLINE_FIXTURE"
    assert not run.fallback_occurred
    assert run.source_results[0].raw_returned_count == len(ml_papers)


def test_dedup_preserves_all_provenance(tmp_path, purpose):
    adapters = {
        "openalex": lambda *args: [Paper(
            "oa", "Same study", "same abstract", 2025, "openalex", doi="10/x"
        )],
        "arxiv": lambda *args: [Paper(
            "ax", "Same study", "same abstract", 2025, "arxiv", doi="10/x"
        )],
    }
    papers, run = retrieve_corpus(
        purpose, ["recurring drift"], adapters=adapters,
        cache_directory=tmp_path,
    )
    assert len(papers) == 1
    origins = {
        item["retrieval_origin"] for item in papers[0].provenance_history
    }
    assert origins == {"live_openalex", "live_arxiv"}
