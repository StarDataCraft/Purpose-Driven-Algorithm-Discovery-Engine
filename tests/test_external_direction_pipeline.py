from __future__ import annotations

from dataclasses import replace

from discovery_pipeline import discover_structural_gaps
from external_discovery_pipeline import (
    SearchPolicy, discover_external_mechanisms_for_direction,
)
from idea_pipeline import derive_ideas_for_direction
from models import AlignmentResult, Paper
from run_models import ResearchRun
from ux_models import build_direction_portfolio


def context(purpose, ml_papers):
    discovery = discover_structural_gaps(ml_papers, purpose)
    run = ResearchRun.create(purpose.purpose_id, "LIVE", "lightweight",
                             purpose.publication_window)
    directions = build_direction_portfolio(
        run.run_id, purpose, discovery.consolidation.promoted,
        discovery.gaps, discovery.papers,
    )
    gap_by_id = {item.gap_id: item for item in discovery.gaps}
    return run, directions, gap_by_id


def adapters(external_papers, fail_arxiv=False):
    def records(source):
        return [replace(item, source=source) for item in external_papers]

    def failure(*args):
        raise ValueError("arXiv unavailable")

    return {
        "openalex": lambda *args: records("openalex"),
        "arxiv": failure if fail_arxiv else lambda *args: records("arxiv"),
    }


def test_live_direction_automatically_retrieves_and_derives_ideas(
    tmp_path, purpose, ml_papers, external_papers,
):
    run, directions, gaps = context(purpose, ml_papers)
    direction = directions[0]
    gap = gaps[direction.selected_gap_id]
    run.selected_gap_snapshot = {"gap_id": gap.gap_id}
    policy = SearchPolicy("LIVE")
    result = derive_ideas_for_direction(
        purpose=purpose, direction=direction, gap=gap, parent_run=run,
        search_policy=policy, seed=42, memory_path=tmp_path / "memory.db",
        adapters=adapters(external_papers), cache_directory=tmp_path / "cache",
    )
    assert result.external_result.papers
    assert result.external_result.mechanisms
    assert result.external_result.accepted_alignments
    assert result.portfolio
    assert result.derivations
    assert run.stage_records["external_discovery"]["selected_direction_id"] == direction.direction_id
    assert not any("Step 4" in item for item in result.external_result.errors)


def test_mixed_parent_inherits_requested_live_policy(
    tmp_path, purpose, ml_papers, external_papers,
):
    run, directions, gaps = context(purpose, ml_papers)
    run.actual_search_mode = "MIXED"
    direction = directions[0]
    result = discover_external_mechanisms_for_direction(
        purpose=purpose, direction=direction,
        gap=gaps[direction.selected_gap_id], parent_run=run,
        search_policy=SearchPolicy("LIVE", allow_cache=True),
        adapters=adapters(external_papers), cache_directory=tmp_path,
    )
    assert result.retrieval_run.requested_search_mode == "LIVE"
    assert result.stage_diagnostics["search_policy"]["allow_cache"] is True
    assert result.papers


def test_cache_hit_and_cache_miss_are_explicit(
    tmp_path, purpose, ml_papers, external_papers,
):
    run, directions, gaps = context(purpose, ml_papers)
    direction = directions[0]
    gap = gaps[direction.selected_gap_id]
    discover_external_mechanisms_for_direction(
        purpose=purpose, direction=direction, gap=gap, parent_run=run,
        search_policy=SearchPolicy(
            "LIVE", sources=("openalex",), maximum_per_query=12,
        ),
        adapters=adapters(external_papers), cache_directory=tmp_path / "hit",
    )
    cached = discover_external_mechanisms_for_direction(
        purpose=purpose, direction=direction, gap=gap, parent_run=run,
        search_policy=SearchPolicy(
            "CACHE", sources=("openalex",), maximum_per_query=12,
        ),
        cache_directory=tmp_path / "hit",
    )
    assert cached.retrieval_run.actual_search_mode == "CACHE"
    assert cached.papers
    missed = discover_external_mechanisms_for_direction(
        purpose=purpose, direction=direction, gap=gap, parent_run=run,
        search_policy=SearchPolicy("CACHE", sources=("openalex",)),
        cache_directory=tmp_path / "miss",
    )
    assert not missed.papers
    assert "No matching cached external evidence" in " ".join(missed.errors)
    assert "Step 4" not in " ".join(missed.errors)


def test_partial_live_source_failure_retains_successful_evidence(
    tmp_path, purpose, ml_papers, external_papers,
):
    run, directions, gaps = context(purpose, ml_papers)
    direction = directions[0]
    result = discover_external_mechanisms_for_direction(
        purpose=purpose, direction=direction,
        gap=gaps[direction.selected_gap_id], parent_run=run,
        search_policy=SearchPolicy("LIVE"),
        adapters=adapters(external_papers, fail_arxiv=True),
        cache_directory=tmp_path,
    )
    assert result.papers
    assert "arxiv" in result.retrieval_run.source_failures
    assert result.retrieval_run.actual_search_mode == "LIVE"


def test_direction_queries_are_distinct_and_identity_is_preserved(
    tmp_path, purpose, ml_papers, external_papers,
):
    run, directions, gaps = context(purpose, ml_papers)
    first, second = directions[:2]
    results = [discover_external_mechanisms_for_direction(
        purpose=purpose, direction=item, gap=gaps[item.selected_gap_id],
        parent_run=run, search_policy=SearchPolicy("LIVE"),
        adapters=adapters(external_papers), cache_directory=tmp_path / item.direction_id,
    ) for item in (first, second)]
    assert results[0].identity() != results[1].identity()
    # Native external queries may be shared when two directions have the same
    # cross-domain problem. Direction specificity belongs in typed alignment,
    # not by contaminating source-domain queries with an ML component name.
    assert (
        results[0].cross_domain_problem_signature.affected_ml_slot
        != results[1].cross_domain_problem_signature.affected_ml_slot
    )


def test_external_queries_do_not_append_ml_modification_slots(
    tmp_path, purpose, ml_papers, external_papers,
):
    run, directions, gaps = context(purpose, ml_papers)
    direction = directions[0]
    gap = gaps[direction.selected_gap_id]
    result = discover_external_mechanisms_for_direction(
        purpose=purpose, direction=direction, gap=gap, parent_run=run,
        search_policy=SearchPolicy("LIVE"), adapters=adapters(external_papers),
        cache_directory=tmp_path,
    )
    slot = gap.affected_component.replace("_", " ")
    assert all(
        not query.casefold().endswith(slot.casefold())
        for queries in result.accepted_queries_by_domain.values()
        for query in queries
    )
    assert len(result.accepted_queries_by_domain) <= 4
    assert result.stage_diagnostics["stage_one_query_count"] <= 6
    assert result.stage_diagnostics["stage_two_query_count"] <= 4
    assert sum(map(len, result.accepted_queries_by_domain.values())) <= 10


def test_adaptive_external_search_stops_after_sufficient_stage_one_evidence(
    tmp_path, purpose, ml_papers, external_papers,
):
    run, directions, gaps = context(purpose, ml_papers)
    direction = directions[0]
    gap = gaps[direction.selected_gap_id]
    extra = [
        Paper(f"extra:{index}", f"External evidence {index}",
              f"Operational process context number {index} with distinct evidence.",
              2025, "openalex")
        for index in range(3)
    ]
    sufficient = [*external_papers, *extra]
    result = discover_external_mechanisms_for_direction(
        purpose=purpose, direction=direction, gap=gap, parent_run=run,
        search_policy=SearchPolicy(
            "LIVE", sources=("openalex",), maximum_per_query=12,
        ), adapters={"openalex": lambda *args: sufficient},
        cache_directory=tmp_path,
    )
    assert len(result.papers) >= 8
    assert len(result.mechanisms) >= 3
    assert result.stage_diagnostics["adaptive_stage_two_used"] is False
    assert result.stage_diagnostics["stage_two_query_count"] == 0


def test_no_mechanism_and_no_alignment_have_stage_specific_errors(
    tmp_path, purpose, ml_papers, monkeypatch,
):
    run, directions, gaps = context(purpose, ml_papers)
    direction = directions[0]
    gap = gaps[direction.selected_gap_id]
    irrelevant = [Paper("x", "Unrelated", "No operational process.", 2025, "openalex")]
    no_mechanism = discover_external_mechanisms_for_direction(
        purpose=purpose, direction=direction, gap=gap, parent_run=run,
        search_policy=SearchPolicy("LIVE", sources=("openalex",)),
        adapters={"openalex": lambda *args: irrelevant}, cache_directory=tmp_path / "m",
    )
    assert "no operational mechanism" in " ".join(no_mechanism.errors).lower()

    import external_discovery_pipeline as target
    monkeypatch.setattr(target, "align", lambda gap, mechanism, purpose: AlignmentResult(
        gap.gap_id, mechanism.mechanism_id, {}, [], [], ["signal unavailable"],
        0.0, True, ["hard information check failed"],
    ))
    from app import load_fixture
    no_alignment = discover_external_mechanisms_for_direction(
        purpose=purpose, direction=direction, gap=gap, parent_run=run,
        search_policy=SearchPolicy("OFFLINE_FIXTURE"),
        fixture_loader=lambda: load_fixture("external_papers.json"),
        cache_directory=tmp_path / "a",
    )
    assert "no structural alignment" in " ".join(no_alignment.errors).lower()
