"""Typed, deterministic presentation models for the three-part workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha1, sha256
import json
from typing import Any, Sequence

from gap_consolidation import CanonicalGapFamily
from models import (
    AlgorithmCandidate, AlignmentResult, ExperimentPlan, GapSignature,
    MechanismSignature, Paper, PurposeContract, ScoreCard,
)


PIPELINE_VERSION = "three-part-ux-v1"
SELECTED_IDEA_SCHEMA_VERSION = "selected-idea-context-v1"


def _canonical_fingerprint(snapshot: dict[str, Any]) -> str:
    payload = json.dumps(
        snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    )
    return sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SelectedIdeaContext:
    """Complete, self-consistent hand-off from Part 2 to Part 3."""

    selection_id: str
    selected_at_utc: str
    parent_run_id: str
    direction_id: str
    gap_id: str
    gap_family_id: str
    candidate_id: str
    derivation_id: str
    candidate_snapshot: dict[str, Any]
    derivation_snapshot: dict[str, Any]
    direction_snapshot: dict[str, Any]
    gap_snapshot: dict[str, Any]
    pipeline_version: str
    schema_version: str
    candidate_fingerprint: str
    derivation_fingerprint: str
    resolution_source: str = "immutable snapshot"
    validation_status: str = "COMPLETE"
    validation_notes: tuple[str, ...] = ()
    maturity_level: str = "LEGACY_UNASSESSED"
    maturity_limiters: tuple[dict[str, Any], ...] = ()
    repair_options: tuple[str, ...] = ()
    open_design_choices: tuple[dict[str, Any], ...] = ()
    resolved_hypothesis_snapshot: dict[str, Any] = field(default_factory=dict)
    final_evidence_assessment: dict[str, Any] = field(default_factory=dict)
    final_alignment_assessment: dict[str, Any] = field(default_factory=dict)
    final_operator_plan: dict[str, Any] = field(default_factory=dict)
    repairs_applied: tuple[dict[str, Any], ...] = ()
    experiment_spec: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SelectedIdeaContext":
        values = dict(payload)
        values["validation_notes"] = tuple(values.get("validation_notes", ()))
        values["maturity_limiters"] = tuple(values.get("maturity_limiters", ()))
        values["repair_options"] = tuple(values.get("repair_options", ()))
        values["open_design_choices"] = tuple(values.get("open_design_choices", ()))
        values["repairs_applied"] = tuple(values.get("repairs_applied", ()))
        for key in (
            "resolved_hypothesis_snapshot", "final_evidence_assessment",
            "final_alignment_assessment", "final_operator_plan", "experiment_spec",
        ):
            values[key] = dict(values.get(key, {}))
        return cls(**values)


def candidate_to_dict(candidate: AlgorithmCandidate) -> dict[str, Any]:
    return asdict(candidate)


def candidate_from_dict(payload: dict[str, Any]) -> AlgorithmCandidate:
    values = dict(payload)
    values["minimal_experiment"] = ExperimentPlan(**values["minimal_experiment"])
    values["scores"] = ScoreCard(**values["scores"])
    return AlgorithmCandidate(**values)


def derivation_to_dict(derivation: "IdeaDerivation") -> dict[str, Any]:
    return asdict(derivation)


def derivation_from_dict(payload: dict[str, Any]) -> "IdeaDerivation":
    values = dict(payload)
    for key in (
        "structural_correspondences", "analogy_boundaries", "selected_operators",
        "known_method_neighbors", "uncertainties",
    ):
        values[key] = tuple(values.get(key, ()))
    return IdeaDerivation(**values)


def direction_to_dict(direction: "DirectionSummary") -> dict[str, Any]:
    return asdict(direction)


def direction_from_dict(payload: dict[str, Any]) -> "DirectionSummary":
    values = dict(payload)
    for key in (
        "gap_family_ids", "gap_types", "evidence_paper_ids",
        "current_solution_families", "secondary_metrics", "uncertainties",
    ):
        values[key] = tuple(values.get(key, ()))
    return DirectionSummary(**values)


def gap_to_dict(gap: GapSignature) -> dict[str, Any]:
    return asdict(gap)


def gap_from_dict(payload: dict[str, Any]) -> GapSignature:
    return GapSignature(**dict(payload))


def selected_idea_fingerprints(
    candidate_snapshot: dict[str, Any], derivation_snapshot: dict[str, Any],
) -> tuple[str, str]:
    return (
        _canonical_fingerprint(candidate_snapshot),
        _canonical_fingerprint(derivation_snapshot),
    )


def candidate_modification(candidate: AlgorithmCandidate) -> str:
    """Return the concrete delta for the candidate's affected component."""
    deltas = {
        "objective": candidate.objective_delta,
        "update_rule": candidate.update_rule_delta,
        "feedback_control": candidate.update_rule_delta,
        "state_estimation": candidate.update_rule_delta,
        "model_selection": candidate.update_rule_delta,
        "initialization": candidate.initialization_delta,
        "memory": candidate.memory_delta,
        "routing": candidate.routing_delta,
        "expert_selection": candidate.routing_delta,
        "aggregation": candidate.aggregation_delta,
        "stopping": candidate.stopping_delta,
        "component_birth_death": candidate.component_lifecycle_delta,
    }
    delta = deltas.get(candidate.affected_component, "")
    if delta:
        return delta
    for fallback in (
        candidate.update_rule_delta, candidate.inference_delta,
        candidate.objective_delta, candidate.memory_delta,
        candidate.routing_delta, candidate.aggregation_delta,
        candidate.initialization_delta, candidate.stopping_delta,
        candidate.component_lifecycle_delta,
    ):
        if fallback:
            return fallback
    return "No concrete modification was generated."


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
    portfolio_tier: str = "RECOMMENDED"
    portfolio_rank: int = 0
    direction_signature: dict[str, Any] = field(default_factory=dict)
    selection_score: float = 0.0
    diversity_contribution: float = 1.0
    evidence_status: str = ""
    exploratory_reason: str = ""
    nearest_direction_id: str = ""
    similarity_to_nearest_direction: float = 0.0
    expansion_origin: str = "none"


@dataclass(frozen=True)
class DirectionSignature:
    task: str
    application_context: str
    failure_topology: str
    affected_algorithm_family: str
    affected_component: str
    gap_type: str
    primary_metric: str
    evidence_cluster_ids: tuple[str, ...]
    known_solution_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DirectionPortfolioResult:
    recommended: list[DirectionSummary]
    exploratory: list[DirectionSummary]
    all_directions: list[DirectionSummary]
    rejected: list[dict[str, Any]]
    target_count: int
    actual_count: int
    diversity_summary: dict[str, Any]
    expansion_attempted: bool
    expansion_actions: list[str]
    insufficient_choice_reason: str
    warnings: list[str]


def reconcile_direction_limitations(
    affected_algorithm_family: str, limitations: Sequence[str],
) -> tuple[str, ...]:
    """Remove stale limitations whose structured condition has been repaired."""
    values = list(limitations)
    if affected_algorithm_family.casefold() not in {"", "unknown", "unspecified", "unbound"}:
        values = [item for item in values
                  if "algorithm family is unknown" not in item.casefold()]
    return tuple(dict.fromkeys(values))


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
        contextual_paper_ids = [
            paper_id for paper_id in family.supporting_paper_ids
            if paper_id in by_paper
        ]
        direct_paper_ids = {
            paper_id
            for member in family.member_gaps
            for paper_id, section in zip(
                member.evidence_paper_ids, member.evidence_sections
            )
            if section != "purpose_contract" and paper_id in by_paper
        }
        for paper_id in contextual_paper_ids:
            paper = by_paper.get(paper_id)
            text = f"{paper.title} {paper.abstract}".casefold() if paper else ""
            role = (
                "CONTEXTUAL_BACKGROUND" if paper_id not in direct_paper_ids
                else "CURRENT_SOLUTION" if any(x in text for x in ("mitigat", "solution", "improv"))
                else "DIRECT_FAILURE_EVIDENCE"
            )
            roles[paper_id] = role
        uncertainties = list(family.rejection_reasons)
        if family.abstract_only_count:
            uncertainties.append("Some support is abstract-only.")
        if len(direct_paper_ids) < 3:
            uncertainties.append("Limited independent corroboration.")
        output.append(DirectionSummary(
            family.family_id, run_id, family.representative_title,
            family.plain_language_statement, gap.task, gap.application_context,
            gap.failure_type, gap.affected_algorithm_family,
            family.binding_granularity, (family.family_id,),
            tuple(family.evidence_types), tuple(contextual_paper_ids),
            len(direct_paper_ids), min(
                family.independent_source_count, len(direct_paper_ids)
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


def _direction_signature(
    purpose: PurposeContract, family: CanonicalGapFamily, gap: GapSignature,
) -> DirectionSignature:
    return DirectionSignature(
        task=gap.task.casefold().strip(),
        application_context=(gap.application_context or purpose.use_case).casefold().strip(),
        failure_topology=family.field_consensus.get("failure_topology", gap.failure_type).casefold().strip(),
        affected_algorithm_family=gap.affected_algorithm_family.casefold().strip(),
        affected_component=gap.affected_component.casefold().strip(),
        gap_type=(gap.structural_gap_subtype or gap.gap_type).casefold().strip(),
        primary_metric=gap.primary_metric.casefold().strip(),
        evidence_cluster_ids=tuple(sorted(set(family.supporting_paper_ids))),
        known_solution_status=("assessed" if family.known_mitigations else "no direct solution confirmed"),
    )


def _signature_similarity(left: DirectionSignature, right: DirectionSignature) -> float:
    categorical = (
        "task", "application_context", "failure_topology",
        "affected_algorithm_family", "affected_component", "gap_type",
        "primary_metric", "known_solution_status",
    )
    matches = sum(getattr(left, name) == getattr(right, name) for name in categorical)
    a, b = set(left.evidence_cluster_ids), set(right.evidence_cluster_ids)
    evidence_overlap = len(a & b) / len(a | b) if a or b else 1.0
    return round((matches + evidence_overlap) / (len(categorical) + 1), 3)


def _family_gate_reasons(
    family: CanonicalGapFamily, gap: GapSignature, papers_by_id: dict[str, Paper],
    *, exploratory: bool,
) -> list[str]:
    from gap_consolidation import promoted_gap_validation_reasons

    reasons = promoted_gap_validation_reasons(gap)
    if not family.supporting_paper_ids or not any(
        paper_id in papers_by_id for paper_id in family.supporting_paper_ids
    ):
        reasons.append("no supporting paper record")
    direct_paper_ids = {
        paper_id for member in (family.member_gaps or [gap])
        for paper_id, section in zip(
            member.evidence_paper_ids, member.evidence_sections
        ) if section != "purpose_contract" and paper_id in papers_by_id
    }
    if not direct_paper_ids:
        reasons.append("no direct evidence-bearing paper")
    if not family.unresolved_remainder.strip():
        reasons.append("no unresolved remainder")
    if exploratory:
        if family.promotion_status not in {
            "SINGLE_PAPER", "INSUFFICIENT_KNOWN_SOLUTION_SEARCH", "UNTESTABLE",
        }:
            reasons.append(f"ineligible exploratory status: {family.promotion_status}")
        if family.testability < .4:
            reasons.append("testability below exploratory threshold")
    elif family.promotion_status != "PROMOTED":
        reasons.append("did not pass full promotion gates")
    return list(dict.fromkeys(reasons))


def _quality_score(family: CanonicalGapFamily, gap: GapSignature) -> float:
    support = min(1.0, family.empirical_support_count / 3)
    source = min(1.0, family.independent_source_count / 2)
    binding = gap.evidence_strength_components.get("algorithm_binding", 0.0)
    remainder = 1.0 if family.unresolved_remainder else 0.0
    return round(
        .24 * gap.confidence_score + .2 * family.testability + .18 * support
        + .12 * source + .14 * binding + .12 * remainder, 4,
    )


def build_tiered_direction_portfolio(
    *, run_id: str, purpose: PurposeContract,
    promoted_families: Sequence[CanonicalGapFamily],
    exploratory_families: Sequence[CanonicalGapFamily],
    gaps: Sequence[GapSignature], papers: Sequence[Paper],
    preferred_count: int = 4, minimum_count: int = 3,
    maximum_count: int = 6,
) -> DirectionPortfolioResult:
    """Build a bounded, deterministic, evidence-gated quality-diversity set."""
    by_gap = {gap.gap_id: gap for gap in gaps}
    by_paper = {paper.paper_id: paper for paper in papers}
    rejected: list[dict[str, Any]] = []

    def candidates(families: Sequence[CanonicalGapFamily], tier: str):
        eligible = []
        for family in families:
            gap = by_gap.get(family.representative_gap_id)
            reasons = ["representative gap missing"] if gap is None else _family_gate_reasons(
                family, gap, by_paper, exploratory=tier == "EXPLORATORY",
            )
            if reasons:
                rejected.append({"family_id": family.family_id, "tier": tier, "reasons": reasons})
                continue
            eligible.append((family, gap, _direction_signature(purpose, family, gap), _quality_score(family, gap)))
        return sorted(eligible, key=lambda item: (-item[3], item[0].family_id))

    recommended_pool = candidates(promoted_families, "RECOMMENDED")
    selected: list[tuple[Any, ...]] = []

    def add_diverse(pool, limit):
        while pool and len(selected) < limit:
            ranked = []
            for item in pool:
                similarities = [
                    (_signature_similarity(item[2], prior[2]), prior[0].family_id)
                    for prior in selected
                ]
                nearest = max(similarities, default=(0.0, ""))
                contribution = round(1.0 - nearest[0], 3)
                ranked.append((item[3] + .25 * contribution, contribution, nearest, item))
            ranked.sort(key=lambda row: (-row[0], row[3][0].family_id))
            _, contribution, nearest, winner = ranked[0]
            pool.remove(winner)
            if selected and contribution < .1:
                rejected.append({"family_id": winner[0].family_id, "tier": "DUPLICATE", "reasons": [f"near-duplicate of {nearest[1]}"]})
                continue
            selected.append((*winner, contribution, nearest))

    add_diverse(recommended_pool, min(4, maximum_count))
    recommended_count = len(selected)
    expansion_attempted = recommended_count < minimum_count
    expansion_actions = []
    if expansion_attempted:
        expansion_actions.append("Evaluated coherent families that narrowly missed promotion once")
    if recommended_count < preferred_count:
        exploratory_pool = candidates(exploratory_families, "EXPLORATORY")
        add_diverse(exploratory_pool, min(preferred_count, maximum_count))

    summaries: list[DirectionSummary] = []
    for rank, item in enumerate(selected, 1):
        family, gap, signature, score, contribution, nearest = item
        tier = "RECOMMENDED" if rank <= recommended_count else "EXPLORATORY"
        base = build_direction_portfolio(run_id, purpose, [family], list(gaps), list(papers), 1)[0]
        exploratory_reason = ""
        if tier == "EXPLORATORY":
            reasons = list(reconcile_direction_limitations(
                base.affected_algorithm_family, family.rejection_reasons,
            ))
            exploratory_reason = "; ".join(reasons) or "Evidence did not pass every recommendation gate."
        summaries.append(DirectionSummary(
            **{**asdict(base),
               "portfolio_tier": tier, "portfolio_rank": rank,
               "direction_signature": signature.to_dict(), "selection_score": score,
               "diversity_contribution": contribution,
               "evidence_status": "full evidence gates passed" if tier == "RECOMMENDED" else "bounded exploratory evidence",
               "exploratory_reason": exploratory_reason,
               "nearest_direction_id": nearest[1], "similarity_to_nearest_direction": nearest[0],
               "expansion_origin": "none" if tier == "RECOMMENDED" else "bounded exploratory expansion"}
        ))
    recommended = [item for item in summaries if item.portfolio_tier == "RECOMMENDED"]
    exploratory = [item for item in summaries if item.portfolio_tier == "EXPLORATORY"]
    dimensions = {
        name: len({str(item.direction_signature.get(name, "")) for item in summaries})
        for name in ("failure_topology", "affected_component", "affected_algorithm_family", "gap_type", "primary_metric")
    }
    level = "high" if sum(value > 1 for value in dimensions.values()) >= 3 else "medium" if len(summaries) > 1 else "limited"
    insufficient = ""
    if len(summaries) < minimum_count:
        insufficient = (
            f"Only {len(summaries)} defensible direction(s) passed the current evidence and coherence gates after bounded expansion."
        )
    return DirectionPortfolioResult(
        recommended, exploratory, summaries, rejected, preferred_count,
        len(summaries), {"level": level, "dimensions": dimensions},
        expansion_attempted, expansion_actions, insufficient,
        [insufficient] if insufficient else [],
    )


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
    resolved_hypothesis: dict[str, Any] | None = None,
) -> IdeaExplanation:
    resolved = resolved_hypothesis or {}
    evidence = resolved.get("evidence", {})
    direct = list(evidence.get("direct_problem_evidence", ()))
    direct_count = len(direct) if resolved else sum(
        role == "DIRECT_FAILURE_EVIDENCE" for role in direction.paper_roles.values()
    )
    supported = tuple(dict.fromkeys([
        (
            f"{direct_count} paper(s) directly support "
            f"the recorded failure condition: {direction.failure_condition}."
            if direct_count
            else "Retrieved papers provide context, but no direct paper-stated "
                 "failure sentence supports this direction."
        ),
        f"The external mechanism records signal '{derivation.mechanism_signal}' "
        f"and response '{derivation.mechanism_response}'.",
    ]))
    inferred = (
        f"Mapping {derivation.mechanism_name} to "
        f"{candidate.affected_component} may provide {candidate.expected_improvement}.",
    )
    return IdeaExplanation(
        f"explanation:{candidate.candidate_id}", derivation.parent_run_id,
        direction.direction_id, candidate.candidate_id,
        str(resolved.get("title", candidate.candidate_name)),
        f"Modify {candidate.base_algorithm}'s {candidate.affected_component} "
        f"using {derivation.mechanism_name} to address "
        f"{direction.failure_condition}.",
        direction.plain_language_summary,
        f"{candidate.base_algorithm} uses its existing "
        f"{candidate.affected_component} without the proposed mechanism-triggered rule.",
        candidate_modification(candidate),
        candidate.expected_improvement,
        f"If {derivation.mechanism_signal} identifies the relevant condition, "
        f"{derivation.mechanism_response} may avoid relearning from scratch.",
        candidate.base_algorithm,
        " + ".join(resolved.get("selected_slot_bundle", ()))
        or candidate.affected_component,
        tuple(candidate.new_state_variables), derivation.mechanism_trigger,
        str(resolved.get("schematic_operator") or resolved.get("exact_operator")
            or candidate_modification(candidate)),
        tuple(candidate.required_training_information),
        tuple(candidate.required_inference_information),
        candidate.complexity_delta, candidate.memory_delta, purpose.use_case,
        tuple(candidate.must_not_degrade),
        tuple(candidate.nearest_known_method_patterns), candidate.novelty_status,
        tuple(candidate.expected_failure_modes),
        supported, inferred,
        tuple(dict.fromkeys([*derivation.uncertainties,
                             "Potential novelty remains unverified."])),
        tuple(candidate.falsification_tests),
        dict(resolved.get("experiment_spec", asdict(candidate.minimal_experiment))),
        tuple(item.get("paper_id", "") for group in (
            evidence.get("direct_problem_evidence", ()),
            evidence.get("external_mechanism_evidence", ()),
            evidence.get("current_solution_evidence", ()),
        ) for item in group) if resolved else tuple(candidate.evidence_paper_ids),
        tuple(diagram_specs),
        derivation.confidence_by_stage,
    )
