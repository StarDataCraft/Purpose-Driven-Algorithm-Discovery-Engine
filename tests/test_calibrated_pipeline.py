from __future__ import annotations

from active_learning import ActiveLearningItem, prioritize_review_queue
from citation_evidence import citation_evidence
from gap_consolidation import consolidate_gaps
from models import Paper
from pipeline_quality import apply_estimated_relevance, generate_quality_warnings
from query_generation import detect_algorithm_bindings, generate_focused_algorithm_queries
from research_runs import ResearchRun, SourceRetrievalResult
from result_explanation import research_result


def test_automatic_relevance_is_separate_from_human_review(purpose):
    papers = [
        Paper("a", "Unrelated geometry", "A theorem about manifolds.", 2025, "arxiv"),
        Paper("b", "Recurring drift recovery", "Online learning recovery after recurring drift.", 2025, "openalex"),
    ]
    apply_estimated_relevance(papers, purpose)
    run = ResearchRun.create("p1", "LIVE", "lightweight", (2022, 2026))
    run.finalize_from_papers(papers)
    assert run.candidate_paper_count == 2
    assert run.automatically_relevant_paper_count < 2
    assert run.human_reviewed_paper_count == 0
    assert all(not paper.reviewed_relevance_label for paper in papers)


def test_cache_only_status_and_quality_warning(purpose):
    run = ResearchRun.create("p1", "CACHE", "lightweight", (2022, 2026))
    run.source_results = [SourceRetrievalResult(
        "openalex", "scholarly_api", cache_hits=2,
        actual_origin="CACHE_ONLY", api_status="not_called_cache_hit",
    )]
    assert run.source_results[0].api_status == "not_called_cache_hit"
    run.candidate_paper_count = run.automatically_relevant_paper_count = 10
    assert any(
        warning.code == "ALL_CANDIDATES_AUTOMATICALLY_RELEVANT"
        for warning in generate_quality_warnings(run)
    )


def test_weak_transformer_binding_does_not_drive_focused_query(purpose):
    papers = [Paper(
        "x", "Tabular stream review",
        "A Transformer is mentioned as background. Recurring drift remains hard.",
        2025, "openalex",
    )]
    queries, _ = generate_focused_algorithm_queries(
        purpose, detect_algorithm_bindings(papers, purpose)
    )
    assert not any("transformer" in query.casefold() for query in queries)


def test_active_learning_queue_is_deterministic():
    items = [
        ActiveLearningItem(str(i), i / 10, .5, .2, .3, .1, .4, .2, .1)
        for i in range(5)
    ]
    first = prioritize_review_queue(items, seed=3)
    second = prioritize_review_queue(items, seed=3)
    assert first == second
    assert first[0].priority >= first[-1].priority


def test_citation_evidence_is_optional():
    result = citation_evidence("paper:1")
    assert not result.enabled
    assert result.status == "NOT_REQUESTED_OR_UNAVAILABLE"


def test_empty_human_result_is_plain_language():
    assert "No candidate" in research_result(None, None, None, None, None)["conclusion"]
