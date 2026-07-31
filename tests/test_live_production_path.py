"""Mocked, fixture-free production path across ML and external retrieval."""

from discovery_pipeline import discover_structural_gaps
from mechanism_mining import cross_domain_only, extract_mechanisms
from models import Paper
from paper_fetchers import deduplicate_papers
from query_generation import (
    detect_algorithm_bindings, generate_external_queries,
    generate_focused_algorithm_queries, generate_problem_queries,
)
from retrieval_service import retrieve_corpus


def test_mocked_live_two_stage_and_external_path_shares_run_id(
    tmp_path, purpose
):
    def ml_adapter(query, *args):
        suffix = str(abs(hash(query)) % 100000)
        return [Paper(
            f"live:{suffix}", f"Adaptive random forest {query}",
            "Random forest remains challenging under recurring concept drift. "
            "Recovery after concept recurrence has adaptation delay.",
            2025, "openalex",
        )]

    broad, _ = generate_problem_queries(purpose)
    broad_papers, run = retrieve_corpus(
        purpose, broad, sources=["openalex"],
        adapters={"openalex": ml_adapter},
        cache_directory=tmp_path / "ml",
    )
    bindings = detect_algorithm_bindings(broad_papers, purpose)
    focused, _ = generate_focused_algorithm_queries(purpose, bindings)
    focused_papers, focused_run = retrieve_corpus(
        purpose, focused, sources=["openalex"],
        adapters={"openalex": ml_adapter},
        cache_directory=tmp_path / "focused",
    )
    papers = deduplicate_papers([*broad_papers, *focused_papers])
    run.focused_algorithm_queries = focused
    run.source_results.extend(focused_run.source_results)
    run.finalize_from_papers(papers)
    discovery = discover_structural_gaps(
        papers, purpose, bindings[0].algorithm
    )
    run.structural_gap_count = len(discovery.gaps)
    recurring_gap = next(
        gap for gap in discovery.gaps if "recurring" in gap.failure_type
    )
    external_queries = generate_external_queries(recurring_gap)

    def external_adapter(query, *args):
        return [Paper(
            f"external:{abs(hash(query)) % 100000}",
            "Immune memory under repeated challenge",
            "Immune memory reactivation enables rapid secondary response "
            "after recurrent exposure.",
            2025, "openalex", domain="immunology",
        )]

    external_papers, external_run = retrieve_corpus(
        purpose,
        [query for values in external_queries.values() for query in values],
        sources=["openalex"], adapters={"openalex": external_adapter},
        cache_directory=tmp_path / "external",
    )
    for paper in external_papers:
        paper.domain = "immunology"
    mechanisms, _ = extract_mechanisms(external_papers)
    external_run.parent_run_id = run.run_id
    external_run.run_id = run.run_id
    run.external_queries_by_domain = external_queries
    run.mechanism_count = len(cross_domain_only(mechanisms))

    assert run.actual_search_mode == "LIVE"
    assert run.deduplicated_paper_count < run.raw_paper_count
    assert broad and focused and bindings
    assert discovery.gaps
    assert external_run.actual_search_mode == "LIVE"
    assert external_run.run_id == run.run_id
    assert external_run.parent_run_id == run.run_id
    assert run.external_queries_by_domain
    assert run.mechanism_count > 0
    assert all(paper.retrieval_origin == "live_openalex" for paper in papers)
