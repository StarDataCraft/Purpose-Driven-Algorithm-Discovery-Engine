from dataclasses import replace

from discovery_pipeline import discover_structural_gaps
from gap_consolidation import structural_gap_fingerprint
from ux_models import build_tiered_direction_portfolio


def portfolio_inputs(purpose, ml_papers):
    discovery = discover_structural_gaps(ml_papers, purpose)
    base_family = discovery.consolidation.promoted[0]
    base_gap = next(
        gap for gap in discovery.gaps
        if gap.gap_id == base_family.representative_gap_id
    )
    return discovery, base_family, base_gap


def clone_family(base_family, base_gap, index, **gap_changes):
    gap = replace(
        base_gap, gap_id=f"portfolio-gap-{index}",
        title=gap_changes.pop("title", f"Complete supported direction number {index}"),
        **gap_changes,
    )
    consensus = dict(base_family.field_consensus)
    consensus.update({
        "failure_topology": gap.failure_type,
        "affected_component": gap.affected_component,
        "metric": gap.primary_metric,
    })
    family = replace(
        base_family, family_id=f"portfolio-family-{index}",
        fingerprint=f"fingerprint-{index}", representative_gap_id=gap.gap_id,
        representative_title=gap.title,
        plain_language_statement=f"For {gap.task}, {gap.failure_type} affects {gap.affected_component}.",
        field_consensus=consensus, member_instance_ids=[gap.gap_id],
        member_gaps=[gap, *base_family.member_gaps],
    )
    return family, gap


def build(purpose, ml_papers, recommended, exploratory, gaps):
    return build_tiered_direction_portfolio(
        run_id="run-1", purpose=purpose, promoted_families=recommended,
        exploratory_families=exploratory, gaps=gaps, papers=ml_papers,
    )


def test_four_strong_distinct_promoted_families_are_recommended(purpose, ml_papers):
    _, family, gap = portfolio_inputs(purpose, ml_papers)
    pairs = [
        clone_family(family, gap, 1, failure_type="recurrence detection delay", affected_component="detection", primary_metric="detection delay"),
        clone_family(family, gap, 2, failure_type="false recurrence match", affected_component="routing", primary_metric="false match rate"),
        clone_family(family, gap, 3, failure_type="archive saturation", affected_component="memory", primary_metric="memory use"),
        clone_family(family, gap, 4, failure_type="slow regime re-entry", affected_component="aggregation", primary_metric="recovery time"),
    ]
    result = build(purpose, ml_papers, [item[0] for item in pairs], [], [item[1] for item in pairs])
    assert len(result.recommended) == 4
    assert not result.exploratory
    assert result.diversity_summary["level"] == "high"


def test_two_promoted_and_three_exploratory_reach_target_only(purpose, ml_papers):
    _, family, gap = portfolio_inputs(purpose, ml_papers)
    pairs = [
        clone_family(family, gap, i, failure_type=f"failure topology {i}", affected_component=f"component_{i}", primary_metric=f"metric_{i}")
        for i in range(5)
    ]
    exploratory = [replace(item[0], promotion_status="SINGLE_PAPER", rejection_reasons=["fewer than two independent papers"]) for item in pairs[2:]]
    result = build(purpose, ml_papers, [item[0] for item in pairs[:2]], exploratory, [item[1] for item in pairs])
    assert len(result.recommended) == 2
    assert len(result.exploratory) == 2
    assert result.actual_count == result.target_count == 4
    assert result.expansion_attempted


def test_near_duplicates_are_suppressed_and_order_is_stable(purpose, ml_papers):
    _, family, gap = portfolio_inputs(purpose, ml_papers)
    pairs = [clone_family(family, gap, i) for i in range(6)]
    first = build(purpose, ml_papers, [item[0] for item in reversed(pairs)], [], [item[1] for item in pairs])
    second = build(purpose, ml_papers, [item[0] for item in pairs], [], [item[1] for item in reversed(pairs)])
    assert len(first.all_directions) == 1
    assert [item.direction_id for item in first.all_directions] == [item.direction_id for item in second.all_directions]
    assert any(item["tier"] == "DUPLICATE" for item in first.rejected)


def test_one_valid_family_is_shown_with_honest_limited_reason(purpose, ml_papers):
    _, family, gap = portfolio_inputs(purpose, ml_papers)
    result = build(purpose, ml_papers, [family], [], [gap])
    assert len(result.all_directions) == 1
    assert "Only 1 defensible" in result.insufficient_choice_reason
    assert result.expansion_attempted


def test_unknown_family_incomplete_title_and_incoherent_papers_are_rejected(purpose, ml_papers):
    _, family, gap = portfolio_inputs(purpose, ml_papers)
    unknown = clone_family(family, gap, 1, affected_algorithm_family="UNKNOWN")
    incomplete = clone_family(family, gap, 2, title="Broken under")
    coherent = clone_family(family, gap, 3)
    incoherent = (replace(coherent[0], supporting_paper_ids=["missing-paper"]), coherent[1])
    pairs = [unknown, incomplete, incoherent]
    result = build(purpose, ml_papers, [item[0] for item in pairs], [], [item[1] for item in pairs])
    assert not result.all_directions
    reasons = " ".join(reason for item in result.rejected for reason in item["reasons"])
    assert "unknown" in reasons
    assert "incomplete title" in reasons
    assert "no supporting paper" in reasons


def test_distinct_components_and_metrics_remain_separate(purpose, ml_papers):
    _, family, gap = portfolio_inputs(purpose, ml_papers)
    component_pair = [
        clone_family(family, gap, 1, affected_component="routing"),
        clone_family(family, gap, 2, affected_component="memory"),
    ]
    metric_pair = [
        clone_family(family, gap, 3, primary_metric="recovery latency"),
        clone_family(family, gap, 4, primary_metric="false recurrence rate"),
    ]
    pairs = component_pair + metric_pair
    result = build(purpose, ml_papers, [item[0] for item in pairs], [], [item[1] for item in pairs])
    assert len(result.all_directions) == 4
    assert result.diversity_summary["dimensions"]["affected_component"] >= 2
    assert result.diversity_summary["dimensions"]["primary_metric"] >= 2


def test_consolidation_fingerprint_does_not_overmerge_components_or_metrics(purpose, ml_papers):
    _, _, gap = portfolio_inputs(purpose, ml_papers)
    routing = replace(gap, affected_component="routing")
    memory = replace(gap, affected_component="memory")
    latency = replace(gap, primary_metric="recovery latency")
    false_match = replace(gap, primary_metric="false recurrence rate")
    assert structural_gap_fingerprint(routing, purpose) != structural_gap_fingerprint(memory, purpose)
    assert structural_gap_fingerprint(latency, purpose) != structural_gap_fingerprint(false_match, purpose)
