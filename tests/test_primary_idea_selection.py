"""Scientific gates and automatic primary-idea promotion regressions."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from discovery_pipeline import discover_structural_gaps
from external_discovery_pipeline import SearchPolicy
from gap_consolidation import (
    promoted_gap_validation_reasons, structural_gap_fingerprint,
)
from idea_pipeline import derive_ideas_for_direction
from primary_idea_selection import (
    select_primary_idea, select_primary_idea_with_recovery,
)
from models import Paper
from scientific_validation import (
    DIRECT_FAILURE_EVIDENCE, IRRELEVANT, build_modification_spec,
    classify_paper_roles, evidence_count_invariants,
    validate_candidate_for_promotion,
)
from run_models import ResearchRun
from ux_models import build_direction_portfolio


@pytest.fixture
def selection_case(tmp_path_factory, purpose, ml_papers, external_papers):
    discovery = discover_structural_gaps(ml_papers, purpose)
    run = ResearchRun.create(
        purpose.purpose_id, "LIVE", "lightweight", purpose.publication_window,
    )
    run.evidence_bearing_paper_count = len(ml_papers)
    directions = build_direction_portfolio(
        run.run_id, purpose, discovery.consolidation.promoted,
        discovery.gaps, discovery.papers,
    )
    direction = directions[0]
    gap = next(item for item in discovery.gaps if item.gap_id == direction.selected_gap_id)
    run.selected_gap_snapshot = {"gap_id": gap.gap_id}
    adapters = {
        source: (lambda *args, source=source: [replace(item, source=source) for item in external_papers])
        for source in ("openalex", "arxiv")
    }
    result = derive_ideas_for_direction(
        purpose=purpose, direction=direction, gap=gap, parent_run=run,
        search_policy=SearchPolicy("LIVE"), seed=42,
        memory_path=tmp_path_factory.mktemp("selection") / "memory.db",
        adapters=adapters,
        cache_directory=tmp_path_factory.mktemp("selection-cache"),
    )
    if len(result.portfolio) == 1:
        second = deepcopy(result.portfolio[0])
        second.candidate_id = "cand:valid-alternative"
        second.candidate_name = "Bounded alternative"
        second.scores.total = max(0.0, second.scores.total - .05)
        second_derivation = replace(
            result.derivations[0], candidate_id=second.candidate_id,
            derivation_id="derivation:valid-alternative",
        )
        result.portfolio.append(second)
        result.derivations.append(second_derivation)
    assert len(result.portfolio) >= 2
    return run, direction, gap, result.portfolio, result.derivations


def choose(case, candidates=None, derivations=None):
    run, direction, gap, original_candidates, original_derivations = case
    return select_primary_idea(
        candidates=candidates or original_candidates,
        derivations=derivations or original_derivations,
        direction=direction, gap=gap, parent_run=run,
    )


def test_highest_valid_candidate_is_selected_deterministically(selection_case):
    first = choose(selection_case)
    second = choose(selection_case)
    assert first.status == "SELECTED"
    assert first.selected_candidate_id == second.selected_candidate_id
    assert first.ranking_records == second.ranking_records


def test_high_raw_score_cannot_override_unknown_family_gate(selection_case):
    candidates = deepcopy(selection_case[3])
    valid_id = choose(selection_case).selected_candidate_id
    target = next(item for item in candidates if item.candidate_id != valid_id)
    target.base_algorithm_family = "UNKNOWN"
    target.scores.total = 99.0
    result = choose(selection_case, candidates=candidates)
    assert result.status == "SELECTED"
    assert result.selected_candidate_id == valid_id
    assert "algorithm family is unknown" in result.rejection_reasons[target.candidate_id]


def test_one_valid_candidate_is_selected(selection_case):
    original = choose(selection_case)
    candidate = next(item for item in selection_case[3]
                     if item.candidate_id == original.selected_candidate_id)
    derivation = next(item for item in selection_case[4]
                      if item.candidate_id == candidate.candidate_id)
    result = choose(selection_case, [candidate], [derivation])
    assert result.status == "SELECTED"
    assert result.selected_candidate_id == candidate.candidate_id


def test_zero_candidates_runs_one_bounded_recovery(selection_case):
    calls = []
    run, direction, gap, candidates, derivations = selection_case

    def recover():
        calls.append(True)
        return candidates, derivations

    result = select_primary_idea_with_recovery(
        candidates=[], derivations=[], direction=direction, gap=gap,
        parent_run=run, recover=recover,
    )
    assert len(calls) == 1
    assert result.status == "SELECTED"
    assert result.automatic_recovery_used


def test_failed_recovery_is_honest(selection_case):
    run, direction, gap, _, _ = selection_case
    result = select_primary_idea_with_recovery(
        candidates=[], derivations=[], direction=direction, gap=gap,
        parent_run=run, recover=lambda: ([], []),
    )
    assert result.status == "NO_CANDIDATES"
    assert result.automatic_recovery_used
    assert "exhausted" in result.warnings[-1]


def test_malformed_and_unknown_directions_fail_promotion(selection_case):
    gap = selection_case[2]
    malformed = replace(
        gap, title="Conflicting evidence under",
        failure_type="disagreement in", affected_algorithm_family="UNKNOWN",
    )
    reasons = promoted_gap_validation_reasons(malformed)
    assert "incomplete title" in reasons
    assert "incomplete failure condition" in reasons
    assert "algorithm family is unknown" in reasons


def test_tableshift_and_retoken_like_records_are_not_consolidation_compatible(
    selection_case, purpose,
):
    gap = selection_case[2]
    tableshift = replace(
        gap, gap_id="tableshift", task="tabular classification",
        data_type="tabular datasets", affected_algorithm_family="tabular predictor",
        failure_type="distribution shift across tabular domains",
    )
    retoken = replace(
        gap, gap_id="retoken", task="vision-language retrieval",
        data_type="visual token sequences", affected_algorithm_family="token retriever",
        failure_type="long-context visual token retrieval latency",
    )
    assert structural_gap_fingerprint(tableshift, purpose) != structural_gap_fingerprint(retoken, purpose)


def _invalid_predictive_case(selection_case, purpose):
    payload = json.loads((
        Path(__file__).parents[1]
        / "data/offline_fixtures/predictive_random_forest_invalid.json"
    ).read_text())
    candidate = deepcopy(selection_case[3][0])
    candidate.candidate_name = payload["candidate_name"]
    candidate.base_algorithm = payload["base_algorithm"]
    candidate.base_algorithm_family = payload["base_algorithm_family"]
    candidate.affected_component = "update_rule"
    candidate.update_rule_delta = payload["update_rule"]
    candidate.new_state_variables = ["z"]
    candidate.required_inference_information = payload["required_information"]
    candidate.novelty_status = payload["novelty_status"]
    candidate.minimal_experiment.metrics.append("expert activation accuracy")
    derivation = replace(
        selection_case[4][0], candidate_id=candidate.candidate_id,
        mechanism_name=payload["mechanism"], modification_slot="update_rule",
        structural_correspondences=("surface similarity",),
    )
    papers = [Paper(**item) for item in payload["papers"]]
    gap = replace(selection_case[2], evidence_paper_ids=[papers[0].paper_id])
    audit = SimpleNamespace(
        final_decision="EXPLORATORY — evidence_gap_validity, known_solution_novelty, structural_alignment_quality",
        audit_dimensions=[
            SimpleNamespace(name="evidence_gap_validity", passed=False),
            SimpleNamespace(name="known_solution_novelty", passed=False),
            SimpleNamespace(name="structural_alignment_quality", passed=False),
        ],
    )
    return candidate, derivation, gap, papers, audit


def test_predictive_random_forest_regression_cannot_be_primary(selection_case, purpose):
    candidate, derivation, gap, papers, audit = _invalid_predictive_case(selection_case, purpose)
    run, direction, _, _, _ = selection_case
    run.selected_gap_snapshot = {"gap_id": gap.gap_id}
    candidate.selected_gap_snapshot = {"gap_id": gap.gap_id}
    result = select_primary_idea(
        candidates=[candidate], derivations=[derivation], direction=direction,
        gap=gap, parent_run=run, purpose=purpose, papers=papers,
        full_audits={candidate.candidate_id: audit},
    )
    assert result.status == "NO_CANDIDATE_PASSED"
    assert not result.selected_candidate_id
    reasons = result.rejection_reasons[candidate.candidate_id]
    assert any("full audit rejected" in item for item in reasons)
    assert any("generic Random Forest" in item for item in reasons)
    assert any("undefined symbol" in item for item in reasons)
    assert any("true-label residual" in item for item in reasons)
    assert any("expert activation" in item for item in reasons)


def test_regression_paper_roles_and_counts_are_conservative(selection_case, purpose):
    candidate, _, gap, papers, _ = _invalid_predictive_case(selection_case, purpose)
    roles = classify_paper_roles(papers, purpose, gap, candidate)
    by_id = {item.paper_id: item for item in roles}
    counts = evidence_count_invariants(roles)
    assert by_id["regression:hardware"].role == IRRELEVANT
    assert by_id["regression:chimera"].role == IRRELEVANT
    assert counts["direct_support_count"] <= 1
    assert counts["direct_support_count"] <= counts["evidence_bearing_paper_count"]
    assert counts["evidence_bearing_paper_count"] <= counts["automatically_relevant_paper_count"]
    assert counts["automatically_relevant_paper_count"] <= counts["candidate_paper_count"]


def test_surface_similarity_and_undefined_formula_fail(selection_case, purpose):
    candidate, derivation, gap, papers, audit = _invalid_predictive_case(selection_case, purpose)
    result = validate_candidate_for_promotion(
        candidate=candidate, derivation=derivation, direction=selection_case[1],
        gap=gap, purpose=purpose, papers=papers, full_audit=audit,
    )
    assert not result.passed
    assert any("structural_alignment_quality" in item for item in result.failures)
    assert build_modification_spec(candidate, derivation).unresolved_implementation_choices


def test_delayed_label_assumption_removes_prediction_time_failure(selection_case, purpose):
    candidate, derivation, gap, papers, audit = _invalid_predictive_case(selection_case, purpose)
    delayed_purpose = replace(
        purpose, available_inference_information=["features", "delayed feedback labels"],
    )
    result = validate_candidate_for_promotion(
        candidate=candidate, derivation=derivation, direction=selection_case[1],
        gap=gap, purpose=delayed_purpose, papers=papers, full_audit=audit,
    )
    assert not any("true-label residual" in item for item in result.failures)


def test_missing_human_review_remains_visible_without_changing_direct_role(
    selection_case, purpose,
):
    candidate, _, gap, papers, _ = _invalid_predictive_case(selection_case, purpose)
    papers[0].abstract = "Online learning under recurring concept drift has slow recovery."
    roles = classify_paper_roles(papers, purpose, gap, candidate)
    direct = next(item for item in roles if item.paper_id == papers[0].paper_id)
    assert direct.role == DIRECT_FAILURE_EVIDENCE
    assert direct.human_review_status == "NOT_REVIEWED"
