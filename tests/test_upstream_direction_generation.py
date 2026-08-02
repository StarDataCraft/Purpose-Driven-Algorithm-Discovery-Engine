from dataclasses import replace
import json
from pathlib import Path

from direction_generation import (
    axis_queries, bind_algorithm_family, generate_direction_candidates,
    generate_problem_axes,
)
from discovery_pipeline import discover_structural_gaps
from models import Paper, PurposeContract


def base_records(purpose, ml_papers):
    discovery = discover_structural_gaps(ml_papers, purpose)
    family = discovery.consolidation.families[0]
    gap = next(item for item in discovery.gaps if item.gap_id == family.representative_gap_id)
    return family, gap


def evidence_family(base_family, base_gap, index, paper, **changes):
    gap = replace(
        base_gap, gap_id=f"upstream-gap-{index}",
        title=changes.pop("title", f"Complete extracted research issue {index}"),
        evidence_paper_ids=[paper.paper_id],
        evidence_sentences=[paper.abstract], evidence_sections=["abstract"],
        evidence_count=1, source_diversity=1, **changes,
    )
    family = replace(
        base_family, family_id=f"upstream-family-{index}",
        fingerprint=f"upstream-fingerprint-{index}",
        representative_gap_id=gap.gap_id, representative_title=gap.title,
        supporting_paper_ids=[paper.paper_id], member_gaps=[gap],
        promotion_status="SINGLE_PAPER",
        rejection_reasons=["fewer than two independent papers"],
    )
    return family, gap


def test_exact_algorithm_absent_but_contextual_family_binding_is_supported(purpose, ml_papers):
    family, gap = base_records(purpose, ml_papers)
    paper = Paper("binding-1", "Random Forest recovery under recurring drift",
                  "An online ensemble fails under recurring concept drift and slow recovery.", 2025, "openalex")
    _, gap = evidence_family(
        family, gap, 1, paper, affected_algorithm="Unspecified",
        affected_algorithm_family="unspecified",
        failure_type="recurring concept drift", affected_component="aggregation",
    )
    binding = bind_algorithm_family(gap, [paper], purpose)
    assert binding.bound_family == "ensemble"
    assert binding.binding_granularity == "algorithm family"
    assert binding.supporting_paper_ids == (paper.paper_id,)


def test_no_evidence_supported_binding_remains_unbound(purpose, ml_papers):
    family, gap = base_records(purpose, ml_papers)
    paper = Paper("unrelated", "Visual token retrieval", "Image retrieval embeddings.", 2025, "arxiv")
    _, gap = evidence_family(
        family, gap, 2, paper, affected_algorithm="Unspecified",
        affected_algorithm_family="unspecified",
    )
    assert bind_algorithm_family(gap, [paper], purpose).binding_granularity == "unbound"


def test_incomplete_title_is_repaired_only_when_structured_fields_are_complete(purpose, ml_papers):
    family, gap = base_records(purpose, ml_papers)
    paper = Paper("title-1", "Random Forest recurring drift", "Online ensemble recovery fails under recurring drift.", 2025, "openalex")
    valid = evidence_family(family, gap, 3, paper, title="Conflicting evidence under")
    invalid = evidence_family(family, gap, 4, paper, title="Gap in", affected_component="")
    result = generate_direction_candidates(
        purpose, [valid[0], invalid[0]], [valid[1], invalid[1]], [paper],
    )
    repaired = next(item for item in result.candidates if item.original_title == "Conflicting evidence under")
    malformed = next(item for item in result.candidates if item.original_title == "Gap in")
    assert repaired.title.startswith("Reducing ") and not repaired.title.endswith("under")
    assert malformed.eligibility_status == "MALFORMED"


def test_purpose_axis_without_direct_paper_path_is_not_eligible(purpose, ml_papers):
    family, gap = base_records(purpose, ml_papers)
    purpose_gap = replace(
        gap, gap_id="purpose-only", evidence_paper_ids=["purpose"],
        evidence_sentences=[purpose.current_failure], evidence_sections=["purpose_contract"],
    )
    purpose_family = replace(
        family, family_id="purpose-family", representative_gap_id=purpose_gap.gap_id,
        supporting_paper_ids=["purpose"], member_gaps=[purpose_gap],
    )
    result = generate_direction_candidates(purpose, [purpose_family], [purpose_gap], [])
    assert result.candidates[0].eligibility_status == "INSUFFICIENT_EVIDENCE"
    assert not result.recommended_families and not result.exploratory_families


def test_axis_specific_evidence_can_create_a_new_validated_direction(purpose, ml_papers):
    family, gap = base_records(purpose, ml_papers)
    paper = Paper("axis-1", "Random Forest historical expert selection",
                  "Online ensemble selection fails when a recurring concept returns.", 2025, "openalex")
    record = evidence_family(
        family, gap, 5, paper, affected_algorithm="Unspecified",
        affected_algorithm_family="unspecified", failure_type="incorrect historical expert selection",
        affected_component="expert_selection", primary_metric="expert reactivation accuracy",
    )
    before = generate_direction_candidates(purpose, [record[0]], [record[1]], [])
    after = generate_direction_candidates(purpose, [record[0]], [record[1]], [paper])
    assert not before.exploratory_families
    assert after.exploratory_families
    axes = generate_problem_axes(purpose)
    assert any("historical expert selection" in query for axis in axes for query in axis_queries(axis))


def test_unrelated_papers_cannot_form_a_connected_direction(purpose, ml_papers):
    family, gap = base_records(purpose, ml_papers)
    unrelated = Paper("vision-1", "Visual token retrieval", "Image encoder retrieval quality.", 2025, "arxiv")
    record = evidence_family(family, gap, 6, unrelated)
    result = generate_direction_candidates(purpose, [record[0]], [record[1]], [unrelated])
    assert result.candidates[0].eligibility_status in {"UNBOUND", "INSUFFICIENT_EVIDENCE"}


def test_unsupported_metric_is_not_promoted(purpose, ml_papers):
    family, gap = base_records(purpose, ml_papers)
    paper = Paper("metric-1", "Random Forest recurring drift", "Online ensemble failure under recurring drift.", 2025, "openalex")
    record = evidence_family(family, gap, 7, paper, primary_metric="performance")
    result = generate_direction_candidates(purpose, [record[0]], [record[1]], [paper])
    assert result.candidates[0].eligibility_status == "UNSUPPORTED_METRIC"


def test_rejection_reasons_are_grouped_and_counted(purpose, ml_papers):
    family, gap = base_records(purpose, ml_papers)
    paper = Paper("bad-1", "Unrelated retrieval", "Visual image tokens.", 2025, "arxiv")
    first = evidence_family(family, gap, 8, paper, affected_algorithm="Unspecified", affected_algorithm_family="unspecified")
    second = evidence_family(family, gap, 9, paper, affected_component="")
    result = generate_direction_candidates(purpose, [first[0], second[0]], [first[1], second[1]], [paper])
    assert sum(result.grouped_rejections.values()) == 2
    assert "UNBOUND" in result.grouped_rejections
    assert "MALFORMED" in result.grouped_rejections


def test_reviewed_binding_dataset_controls_false_binding(purpose, ml_papers):
    family, gap = base_records(purpose, ml_papers)
    records = json.loads((Path(__file__).parents[1] / "data/algorithm_binding_review.json").read_text())
    correct = unbound_correct = false_bindings = 0
    for index, item in enumerate(records):
        reviewed_purpose = PurposeContract(
            f"review-{index}", "user", "review", item["task"], "tabular",
            item["failure_condition"], "reduce failure", "recovery time", [], [],
        )
        paper = Paper(
            f"review-paper-{index}", item["paper_title"], item["evidence"],
            2025, "review",
        )
        reviewed_gap = replace(
            gap, gap_id=f"review-gap-{index}", task=item["task"],
            failure_type=item["failure_condition"], affected_algorithm="Unspecified",
            affected_algorithm_family="unspecified", evidence_paper_ids=[paper.paper_id],
            evidence_sentences=[item["evidence"]], evidence_sections=["abstract"],
        )
        binding = bind_algorithm_family(reviewed_gap, [paper], reviewed_purpose)
        expected = item["correct_family"]
        accepted = {expected, item["acceptable_method_class"]}
        if binding.bound_family in accepted:
            correct += 1
        if expected == "UNBOUND" and binding.bound_family == "UNBOUND":
            unbound_correct += 1
        if binding.bound_family in item["incompatible_families"]:
            false_bindings += 1
    assert correct >= 8
    assert unbound_correct == 3
    assert false_bindings == 0


def test_one_promoted_eight_exploratory_diagnostic_fixture_is_repaired_safely(purpose, ml_papers):
    family, gap = base_records(purpose, ml_papers)
    fixture = json.loads((
        Path(__file__).parents[1] / "data/offline_fixtures/one_direction_diagnostic.json"
    ).read_text())
    by_paper = {paper.paper_id: paper for paper in ml_papers}
    families, gaps = [], []
    for index, item in enumerate(fixture):
        paper = by_paper.get(item["paper"])
        evidence_ids = [paper.paper_id] if paper else ["purpose"]
        evidence = [paper.abstract] if paper else [purpose.current_failure]
        sections = ["abstract"] if paper else ["purpose_contract"]
        record_gap = replace(
            gap, gap_id=f"diagnostic-gap-{index}", title=item["title"],
            affected_algorithm=item["algorithm"],
            affected_algorithm_family=item["family"],
            affected_component=item["component"],
            evidence_paper_ids=evidence_ids, evidence_sentences=evidence,
            evidence_sections=sections, evidence_count=len(evidence_ids),
            detection_method=item["origin"],
        )
        record_family = replace(
            family, family_id=f"diagnostic-family-{index}",
            representative_gap_id=record_gap.gap_id,
            representative_title=record_gap.title,
            supporting_paper_ids=evidence_ids, member_gaps=[record_gap],
            promotion_status=item["promotion_status"],
            rejection_reasons=[] if index == 0 else ["legacy diagnostic rejection"],
        )
        gaps.append(record_gap)
        families.append(record_family)
    assert sum(item.promotion_status == "PROMOTED" for item in families) == 1
    assert sum(item.promotion_status != "PROMOTED" for item in families) == 8
    result = generate_direction_candidates(purpose, families, gaps, ml_papers)
    assert result.diagnostics["repaired_titles"] >= 1
    assert result.diagnostics["repaired_family_bindings"] >= 1
    assert result.exploratory_families
    assert result.grouped_rejections.get("UNBOUND", 0) >= 1
    assert result.grouped_rejections.get("MALFORMED", 0) >= 1
    assert all(item.evidence_paths for item in result.candidates if item.eligibility_status.endswith("ELIGIBLE"))
