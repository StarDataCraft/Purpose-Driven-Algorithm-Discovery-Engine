"""Typed, deterministic presentation models for the three-part workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha1
from typing import Any

from gap_consolidation import CanonicalGapFamily
from models import (
    AlgorithmCandidate, AlignmentResult, GapSignature, MechanismSignature,
    Paper, PurposeContract,
)


PIPELINE_VERSION = "three-part-ux-v1"


@dataclass(frozen=True)
class DirectionSummary:
    direction_id: str
    parent_run_id: str
    title: str
    plain_language_summary: str
    task: str
    application_context: str
    failure_condition: str
    affected_algorithm_family: str
    binding_granularity: str
    gap_family_ids: tuple[str, ...]
    gap_types: tuple[str, ...]
    evidence_paper_ids: tuple[str, ...]
    evidence_bearing_paper_count: int
    independent_source_count: int
    paper_roles: dict[str, str]
    current_solution_families: tuple[str, ...]
    known_solution_status: str
    unresolved_remainder: str
    primary_metric: str
    secondary_metrics: tuple[str, ...]
    practical_value: float
    testability: float
    evidence_confidence: float
    algorithm_binding_confidence: float
    known_solution_confidence: float
    risk_level: str
    promotion_reason: str
    uncertainties: tuple[str, ...]
    selected_gap_id: str
    pipeline_version: str = PIPELINE_VERSION


@dataclass(frozen=True)
class IdeaDerivation:
    derivation_id: str
    parent_run_id: str
    direction_id: str
    gap_family_id: str
    selected_gap_snapshot: dict[str, Any]
    problem_statement: str
    required_capability: str
    external_domain: str
    mechanism_id: str
    mechanism_name: str
    original_external_problem: str
    mechanism_signal: str
    mechanism_state: str
    mechanism_trigger: str
    mechanism_response: str
    mechanism_constraint: str
    structural_correspondences: tuple[str, ...]
    analogy_boundaries: tuple[str, ...]
    base_algorithm_family: str
    modification_slot: str
    selected_operators: tuple[str, ...]
    candidate_id: str
    expected_metric_effect: str
    known_method_neighbors: tuple[str, ...]
    novelty_status: str
    confidence_by_stage: dict[str, float]
    uncertainties: tuple[str, ...]
    pipeline_version: str = PIPELINE_VERSION


@dataclass(frozen=True)
class IdeaExplanation:
    explanation_id: str
    parent_run_id: str
    direction_id: str
    candidate_id: str
    title: str
    one_sentence_conclusion: str
    problem: str
    current_behavior: str
    proposed_change: str
    expected_result: str
    causal_hypothesis: str
    base_algorithm: str
    modification_slot: str
    new_state_variables: tuple[str, ...]
    new_trigger: str
    new_rule: str
    training_information: tuple[str, ...]
    inference_information: tuple[str, ...]
    compute_effect: str
    memory_effect: str
    intended_use: str
    must_not_degrade: tuple[str, ...]
    closest_known_methods: tuple[str, ...]
    novelty_status: str
    main_risks: tuple[str, ...]
    supported_claims: tuple[str, ...]
    inferred_claims: tuple[str, ...]
    unknowns: tuple[str, ...]
    falsification_tests: tuple[str, ...]
    minimal_experiment: dict[str, Any]
    supporting_paper_ids: tuple[str, ...]
    diagram_specs: tuple[dict[str, Any], ...]
    confidence_by_stage: dict[str, float]
    pipeline_version: str = PIPELINE_VERSION


def build_direction_portfolio(
    run_id: str, purpose: PurposeContract, families: list[CanonicalGapFamily],
    gaps: list[GapSignature], papers: list[Paper], maximum: int = 8,
) -> list[DirectionSummary]:
    by_gap = {gap.gap_id: gap for gap in gaps}
    by_paper = {paper.paper_id: paper for paper in papers}
    output = []
    ordered_families = sorted(
        families,
        key=lambda family: (
            by_gap.get(family.representative_gap_id).affected_component
            != "model_selection"
            if by_gap.get(family.representative_gap_id) else False,
            family.empirical_support_count,
            family.testability,
        ),
        reverse=True,
    )
    for family in ordered_families[:maximum]:
        gap = by_gap.get(family.representative_gap_id)
        if not gap:
            continue
        roles = {}
        actual_paper_ids = [
            paper_id for paper_id in family.supporting_paper_ids
            if paper_id in by_paper
        ]
        for paper_id in actual_paper_ids:
            paper = by_paper.get(paper_id)
            text = f"{paper.title} {paper.abstract}".casefold() if paper else ""
            role = (
                "current solution" if any(x in text for x in ("mitigat", "solution", "improv"))
                else "empirical failure evidence" if any(x in text for x in ("degrad", "fail", "slow"))
                else "direct gap evidence"
            )
            roles[paper_id] = role
        uncertainties = list(family.rejection_reasons)
        if family.abstract_only_count:
            uncertainties.append("Some support is abstract-only.")
        if len(actual_paper_ids) < 3:
            uncertainties.append("Limited independent corroboration.")
        output.append(DirectionSummary(
            family.family_id, run_id, family.representative_title,
            family.plain_language_statement, gap.task, gap.application_context,
            gap.failure_type, gap.affected_algorithm_family,
            family.binding_granularity, (family.family_id,),
            tuple(family.evidence_types), tuple(actual_paper_ids),
            len(actual_paper_ids), min(
                family.independent_source_count, len(actual_paper_ids)
            ),
            roles, tuple(family.known_mitigations),
            "assessed" if family.known_mitigations else "no direct solution confirmed",
            family.unresolved_remainder, gap.primary_metric,
            tuple(gap.secondary_metrics), gap.practical_value_score,
            gap.testability_score, gap.confidence_score,
            gap.evidence_strength_components.get("algorithm_binding", 0.0),
            .7 if family.known_mitigations else .4,
            "medium" if gap.confidence_score >= .6 else "high",
            "Passed evidence, testability, and known-solution promotion gates.",
            tuple(dict.fromkeys(uncertainties)) or ("Novelty remains unverified.",),
            gap.gap_id,
        ))
    return output


def build_idea_derivation(
    run_id: str, direction: DirectionSummary, gap: GapSignature,
    mechanism: MechanismSignature, alignment: AlignmentResult,
    candidate: AlgorithmCandidate,
) -> IdeaDerivation:
    correspondences = tuple(
        f"{mechanism.observed_signal} ↔ {slot}"
        for slot in alignment.matched_slots
    ) or (f"{mechanism.transferable_operator} ↔ {candidate.affected_component}",)
    return IdeaDerivation(
        "derivation:" + sha1(
            f"{direction.direction_id}:{candidate.candidate_id}".encode()
        ).hexdigest()[:12],
        run_id, direction.direction_id, direction.gap_family_ids[0],
        dict(candidate.selected_gap_snapshot), gap.title, gap.required_response,
        mechanism.source_domain, mechanism.mechanism_id, mechanism.name,
        mechanism.original_problem, mechanism.observed_signal,
        mechanism.internal_state, mechanism.trigger_condition,
        mechanism.response_rule, mechanism.resource_constraint,
        correspondences,
        (mechanism.failure_boundary or "The analogy is structural, not literal.",),
        candidate.base_algorithm_family, candidate.affected_component,
        tuple(candidate.selected_operators), candidate.candidate_id,
        candidate.expected_improvement,
        tuple(candidate.nearest_known_method_patterns), candidate.novelty_status,
        {"gap": gap.confidence_score, "mechanism": mechanism.confidence_score,
         "alignment": alignment.score, "candidate": candidate.scores.total},
        tuple(dict.fromkeys([
            *alignment.missing_information, *candidate.scores.missing_evidence,
        ])) or ("Experimental validation is still required.",),
    )


def build_idea_explanation(
    purpose: PurposeContract, direction: DirectionSummary,
    derivation: IdeaDerivation, candidate: AlgorithmCandidate,
    diagram_specs: list[dict[str, Any]],
) -> IdeaExplanation:
    supported = tuple(dict.fromkeys([
        f"Evidence papers identify: {direction.failure_condition}.",
        f"The external mechanism records signal '{derivation.mechanism_signal}' "
        f"and response '{derivation.mechanism_response}'.",
    ]))
    inferred = (
        f"Mapping {derivation.mechanism_name} to "
        f"{candidate.affected_component} may provide {candidate.expected_improvement}.",
    )
    return IdeaExplanation(
        f"explanation:{candidate.candidate_id}", derivation.parent_run_id,
        direction.direction_id, candidate.candidate_id, candidate.candidate_name,
        f"Modify {candidate.base_algorithm}'s {candidate.affected_component} "
        f"using {derivation.mechanism_name} to address "
        f"{direction.failure_condition}.",
        direction.plain_language_summary, candidate.base_algorithm,
        candidate.update_rule_delta or candidate.inference_delta,
        candidate.expected_improvement,
        f"If {derivation.mechanism_signal} identifies the relevant condition, "
        f"{derivation.mechanism_response} may avoid relearning from scratch.",
        candidate.base_algorithm, candidate.affected_component,
        tuple(candidate.new_state_variables), derivation.mechanism_trigger,
        candidate.update_rule_delta, tuple(candidate.required_training_information),
        tuple(candidate.required_inference_information),
        candidate.complexity_delta, candidate.memory_delta, purpose.use_case,
        tuple(candidate.must_not_degrade),
        tuple(candidate.nearest_known_method_patterns), candidate.novelty_status,
        tuple(candidate.expected_failure_modes),
        supported, inferred,
        tuple(dict.fromkeys([*derivation.uncertainties,
                             "Potential novelty remains unverified."])),
        tuple(candidate.falsification_tests), asdict(candidate.minimal_experiment),
        tuple(candidate.evidence_paper_ids), tuple(diagram_specs),
        derivation.confidence_by_stage,
    )
