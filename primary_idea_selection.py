"""Calibrated maturity assessment and selection of research hypotheses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Callable, Sequence

from idea_maturity import (
    AssessmentIssue, AssessmentSeverity, IdeaMaturityLevel, issue, maturity_value,
)
from models import AlgorithmCandidate, GapSignature, Paper, PurposeContract
from primary_idea_contracts import (
    PRIMARY_IDEA_SELECTION_API_VERSION, PrimaryIdeaSelectionRequest,
)
from run_models import ResearchRun
from scientific_validation import validate_candidate_for_promotion
from ux_models import DirectionSummary, IdeaDerivation, candidate_modification


@dataclass(frozen=True)
class CandidateRankingRecord:
    candidate_id: str
    passed_hard_gates: bool
    gate_failures: tuple[str, ...]
    dimensions: dict[str, float]
    weighted_score: float
    rank: int = 0
    non_selection_reason: str = ""
    maturity_level: str = "REJECTED"
    fatal_failures: tuple[str, ...] = ()
    maturity_limiters: tuple[str, ...] = ()
    pareto_front: int = 0


@dataclass
class PrimaryIdeaSelectionResult:
    status: str
    selected_candidate: AlgorithmCandidate | None = None
    selected_derivation: IdeaDerivation | None = None
    selected_candidate_id: str = ""
    ranking_records: list[CandidateRankingRecord] = field(default_factory=list)
    rejected_candidate_ids: list[str] = field(default_factory=list)
    rejection_reasons: dict[str, list[str]] = field(default_factory=dict)
    selection_reason: str = ""
    confidence: str = "low"
    warnings: list[str] = field(default_factory=list)
    automatic_recovery_used: bool = False
    scientific_gate_results: dict[str, dict[str, object]] = field(default_factory=dict)
    maturity_distribution: dict[str, int] = field(default_factory=dict)
    exploratory_candidate_id: str = ""
    selected_maturity_level: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "selected_candidate_id": self.selected_candidate_id,
            "ranking_records": [asdict(item) for item in self.ranking_records],
            "rejected_candidate_ids": list(self.rejected_candidate_ids),
            "rejection_reasons": dict(self.rejection_reasons),
            "selection_reason": self.selection_reason,
            "confidence": self.confidence,
            "warnings": list(self.warnings),
            "automatic_recovery_used": self.automatic_recovery_used,
            "scientific_gate_results": dict(self.scientific_gate_results),
            "scientific_assessments": dict(self.scientific_gate_results),
            "fatal_rejections": dict(self.rejection_reasons),
            "maturity_limiters": {
                candidate_id: assessment.get("maturity_limiters", [])
                for candidate_id, assessment in self.scientific_gate_results.items()
            },
            "maturity_distribution": dict(self.maturity_distribution),
            "exploratory_candidate_id": self.exploratory_candidate_id,
            "selected_maturity_level": self.selected_maturity_level,
        }


def _known(value: str) -> bool:
    return value.strip().casefold() not in {"", "unknown", "unspecified", "none"}


def _contract_assessment(
    candidate: AlgorithmCandidate, derivation: IdeaDerivation,
    direction: DirectionSummary, gap: GapSignature, run: ResearchRun,
) -> tuple[list[str], list[AssessmentIssue]]:
    failures: list[str] = []
    limiters: list[AssessmentIssue] = []
    if not run.run_id or candidate.research_run_id != run.run_id:
        failures.append("invalid parent ResearchRun")
    if direction.parent_run_id != run.run_id or derivation.direction_id != direction.direction_id:
        failures.append("invalid selected direction")
    if gap.gap_id != candidate.gap_id or derivation.selected_gap_snapshot.get("gap_id") != gap.gap_id:
        failures.append("invalid selected gap")
    if run.evidence_bearing_paper_count < 1 or direction.evidence_bearing_paper_count < 1:
        limiters.append(issue(
            "problem_evidence_missing", AssessmentSeverity.MAJOR_LIMITER,
            "problem evidence: no evidence-bearing ML papers recorded",
            consequence="A research-worthy hypothesis needs direct problem evidence.",
            repair_option="Retrieve and review a task-compatible problem paper.",
        ))
    if not run.external_paper_ids:
        failures.append("external evidence: no external mechanism evidence")
    if not all((derivation.mechanism_signal, derivation.mechanism_state,
                derivation.mechanism_trigger, derivation.mechanism_response)):
        failures.append("external mechanism is not operational")
    if candidate.alignment_acceptance not in {
        "HARD_VALIDATION_PASSED", "STRONG", "PLAUSIBLE_ACCEPTED",
    }:
        failures.append("no accepted structural alignment")
    if not _known(candidate.base_algorithm_family) or not _known(direction.affected_algorithm_family):
        failures.append("algorithm family is unknown")
    if not candidate.affected_component or not _known(derivation.modification_slot):
        failures.append("algorithm action: no identifiable modification slot")
    modification = candidate_modification(candidate).strip()
    generic = {
        "improve aggregation", "add memory", "increase robustness",
        "use adaptation", "apply feedback", "combine mechanisms",
        "no concrete modification was generated.",
    }
    if modification.casefold() in generic or len(modification.split()) < 3:
        failures.append("modification is generic or metaphor-only")
    if not candidate.new_state_variables and not candidate.selected_operators:
        failures.append("algorithm action: no concrete state, trigger, or rule")
    available = {
        str(item).casefold()
        for item in candidate.minimal_experiment.information_audit.get("inference", [])
    }
    required = {str(item).casefold() for item in candidate.required_inference_information}
    if required and not required.issubset(available):
        failures.append("required inference information is unavailable")
    supported_metrics = {
        direction.primary_metric.casefold(), gap.primary_metric.casefold(),
        *(item.casefold() for item in gap.secondary_metrics),
    }
    if not candidate.primary_metric or candidate.primary_metric.casefold() not in supported_metrics:
        failures.append("primary metric is unsupported")
    experiment = candidate.minimal_experiment
    if not all((experiment.hypothesis, experiment.success_rule, experiment.failure_rule)):
        limiters.append(issue(
            "experiment_incomplete", AssessmentSeverity.MAJOR_LIMITER,
            "experiment design: minimal experiment is incomplete",
            consequence="The causal uncertainty cannot yet be resolved efficiently.",
            repair_option="Specify hypothesis, success threshold, failure threshold, and discriminating ablations.",
        ))
    if not candidate.kill_criterion and not experiment.failure_rule:
        limiters.append(issue(
            "kill_criterion_missing", AssessmentSeverity.MAJOR_LIMITER,
            "experiment design: missing kill criterion",
            consequence="An attractive result could otherwise evade falsification.",
            repair_option="Define the result that abandons or redesigns the mechanism.",
        ))
    if not candidate.novelty_status or not candidate.nearest_known_method_patterns:
        limiters.append(issue(
            "prior_art_absent", AssessmentSeverity.MAJOR_LIMITER,
            "prior art: targeted known-solution status is absent",
            consequence="Duplicate risk remains unresolved.",
            repair_option="Search problem, slot, mechanism-slot combination, and cross-task analogues.",
        ))
    if not derivation.uncertainties and not candidate.scores.missing_evidence:
        limiters.append(issue(
            "uncertainty_record_absent", AssessmentSeverity.MINOR_LIMITER,
            "uncertainty: explicit uncertainty record is absent",
            consequence="The research plan may overstate confidence.",
            repair_option="Record the weakest evidence link and fastest invalidation test.",
        ))
    if candidate.scores.rejection_flags:
        failures.extend(f"candidate rejection flag: {item}" for item in candidate.scores.rejection_flags)
    return failures, limiters


def _pareto_fronts(items: list[tuple[str, dict[str, float]]]) -> dict[str, int]:
    """Deterministic non-dominated sorting; lower cost is already normalized upward."""
    remaining = dict(items)
    fronts: dict[str, int] = {}
    front = 1
    keys = ("user_problem_fit", "evidence_strength", "mechanism_quality",
            "structural_alignment_quality", "implementation_feasibility",
            "inference_information_availability", "falsifiability", "compute_memory_cost")
    while remaining:
        nondominated = []
        for candidate_id, dimensions in remaining.items():
            dominated = any(
                other_id != candidate_id
                and all(other.get(key, 0.0) >= dimensions.get(key, 0.0) for key in keys)
                and any(other.get(key, 0.0) > dimensions.get(key, 0.0) for key in keys)
                for other_id, other in remaining.items()
            )
            if not dominated:
                nondominated.append(candidate_id)
        for candidate_id in sorted(nondominated):
            fronts[candidate_id] = front
            remaining.pop(candidate_id)
        front += 1
    return fronts


def _dimensions(candidate: AlgorithmCandidate, derivation: IdeaDerivation) -> dict[str, float]:
    components = candidate.scores.components
    penalties = candidate.scores.penalties
    return {
        "user_problem_fit": components.get("purpose_fit", 0.0),
        "evidence_strength": components.get("gap_evidence", 0.0),
        "gap_validity": components.get("gap_confidence", 0.0),
        "known_solution_risk": max(0.0, 1.0 - penalties.get("duplication", 0.0)),
        "mechanism_quality": components.get("operator_compatibility", 0.0),
        "structural_alignment_quality": max(
            derivation.confidence_by_stage.get("alignment", 0.0),
            components.get("structural_alignment", 0.0),
        ),
        "algorithm_specificity": components.get("algorithm_slot_compatibility", 0.0),
        "implementation_feasibility": components.get("feasibility", 0.0),
        "inference_information_availability": components.get("information_availability", 0.0),
        "falsifiability": components.get("testability", 0.0),
        "expected_metric_relevance": components.get("purpose_fit", 0.0),
        "compute_memory_cost": max(0.0, 1.0 - penalties.get("complexity", 0.0)
                                   - penalties.get("resource_budget", 0.0)),
        "uncertainty": 0.7 if derivation.uncertainties else 0.4,
    }


def select_primary_idea(
    request: PrimaryIdeaSelectionRequest,
) -> PrimaryIdeaSelectionResult:
    """Reject only fatal incoherence, then select by maturity and Pareto quality."""
    request.validate()
    candidates = request.candidates
    derivations = request.derivations
    direction = request.direction
    gap = request.gap
    parent_run = request.parent_run
    automatic_recovery_used = request.automatic_recovery_used
    purpose = request.purpose
    papers = request.papers
    full_audits = request.full_audits
    if not candidates:
        return PrimaryIdeaSelectionResult(
            "NO_CANDIDATES", automatic_recovery_used=automatic_recovery_used,
        )
    derivation_by_id = {item.candidate_id: item for item in derivations}
    records: list[CandidateRankingRecord] = []
    rejected: dict[str, list[str]] = {}
    scientific_results: dict[str, dict[str, object]] = {}
    weights = {
        "user_problem_fit": .12, "evidence_strength": .10,
        "gap_validity": .10, "known_solution_risk": .07,
        "mechanism_quality": .09, "structural_alignment_quality": .12,
        "algorithm_specificity": .10, "implementation_feasibility": .08,
        "inference_information_availability": .07, "falsifiability": .07,
        "expected_metric_relevance": .04, "compute_memory_cost": .02,
        "uncertainty": .02,
    }
    eligible: list[tuple[IdeaMaturityLevel, float, str, AlgorithmCandidate, IdeaDerivation, dict[str, float]]] = []
    exploratory: list[tuple[float, str, AlgorithmCandidate, IdeaDerivation, dict[str, float]]] = []
    maturity_by_id: dict[str, IdeaMaturityLevel] = {}
    limiter_by_id: dict[str, list[str]] = {}
    for candidate in candidates:
        derivation = derivation_by_id.get(candidate.candidate_id)
        failures: list[str] = ["provenance: missing matching derivation"] if derivation is None else []
        contract_limiters: list[AssessmentIssue] = []
        if derivation is not None:
            contract_failures, contract_limiters = _contract_assessment(
                candidate, derivation, direction, gap, parent_run,
            )
            failures.extend(contract_failures)
        maturity = (IdeaMaturityLevel.REJECTED if failures else
                    IdeaMaturityLevel.RESEARCH_WORTHY_HYPOTHESIS if purpose is None else
                    IdeaMaturityLevel.EXPLORATORY_HYPOTHESIS)
        maturity_limiters = list(contract_limiters)
        if derivation is not None and purpose is not None:
            scientific = validate_candidate_for_promotion(
                candidate=candidate, derivation=derivation, direction=direction,
                gap=gap, purpose=purpose, papers=papers,
                full_audit=(full_audits or {}).get(candidate.candidate_id),
            )
            failures.extend(item.issue for item in scientific.fatal_failures)
            maturity_limiters.extend((*scientific.major_limiters, *scientific.minor_limiters))
            maturity = IdeaMaturityLevel.REJECTED if failures else scientific.maturity_level
            if full_audits is not None and candidate.candidate_id not in full_audits:
                maturity_limiters.append(issue(
                    "full_audit_unavailable", AssessmentSeverity.MAJOR_LIMITER,
                    "full audit: unavailable for this candidate",
                    consequence="Independent review dimensions have not been calibrated.",
                    repair_option="Run the complete audit before claiming test-ready maturity.",
                ))
                if maturity_value(maturity) > maturity_value(IdeaMaturityLevel.RESEARCH_WORTHY_HYPOTHESIS):
                    maturity = IdeaMaturityLevel.RESEARCH_WORTHY_HYPOTHESIS
            scientific_results[candidate.candidate_id] = {
                "passed": scientific.passed,
                "fatal_failures": [asdict(item) for item in scientific.fatal_failures],
                "major_limiters": [asdict(item) for item in scientific.major_limiters],
                "minor_limiters": [asdict(item) for item in scientific.minor_limiters],
                "informational_notes": [asdict(item) for item in scientific.informational_notes],
                "maturity_limiters": [asdict(item) for item in (*scientific.major_limiters, *scientific.minor_limiters)],
                "strengths": list(scientific.strengths),
                "maturity_level": scientific.maturity_level.name,
                "maturity_reason": scientific.maturity_reason,
                "repair_options": list(scientific.repair_options),
                "confidence_by_dimension": scientific.confidence_by_dimension,
                "open_design_choices": [asdict(item) for item in scientific.open_design_choices],
                "repairs_applied": [asdict(item) for item in scientific.repairs_applied],
                "capability_operator_plan": asdict(scientific.capability_slot_assessment),
                "assessment_levels": {
                    "problem_evidence": scientific.problem_evidence_level,
                    "mechanism_evidence": scientific.mechanism_evidence_level,
                    "alignment": scientific.alignment_level,
                    "prior_art": scientific.prior_art_level,
                    "implementation": scientific.implementation_level,
                    "information_feasibility": scientific.information_feasibility_level,
                    "experiment": scientific.experiment_level,
                },
                "paper_counts": scientific.paper_counts,
                "paper_roles": [asdict(item) for item in scientific.paper_roles],
                "modification_spec": asdict(scientific.modification_spec),
            }
        failures = list(dict.fromkeys(failures))
        dims = _dimensions(candidate, derivation) if derivation else {}
        score = round(sum(weights[key] * dims.get(key, 0.0) for key in weights), 6)
        if failures:
            maturity = IdeaMaturityLevel.REJECTED
            rejected[candidate.candidate_id] = failures
        elif maturity_value(maturity) >= maturity_value(IdeaMaturityLevel.RESEARCH_WORTHY_HYPOTHESIS):
            eligible.append((maturity, score, candidate.candidate_id, candidate, derivation, dims))
        else:
            exploratory.append((score, candidate.candidate_id, candidate, derivation, dims))
        maturity_by_id[candidate.candidate_id] = maturity
        limiter_by_id[candidate.candidate_id] = list(dict.fromkeys(item.issue for item in maturity_limiters))
        records.append(CandidateRankingRecord(
            candidate.candidate_id, not failures, tuple(failures), dims, score,
            maturity_level=maturity.name, fatal_failures=tuple(failures),
            maturity_limiters=tuple(limiter_by_id[candidate.candidate_id]),
        ))
    distribution = {level.name: sum(value == level for value in maturity_by_id.values())
                    for level in IdeaMaturityLevel}
    if not eligible:
        if exploratory:
            exploratory.sort(key=lambda item: (-item[0], item[1]))
            best = exploratory[0]
            return PrimaryIdeaSelectionResult(
                "EXPLORATORY_AVAILABLE", best[2], best[3], best[1], records,
                sorted(rejected), rejected,
                "No research-worthy hypothesis passed yet; retained the strongest coherent exploratory hypothesis.",
                "low", warnings=["Exploratory hypothesis — not promoted."],
                automatic_recovery_used=automatic_recovery_used,
                scientific_gate_results=scientific_results,
                maturity_distribution=distribution, exploratory_candidate_id=best[1],
                selected_maturity_level=IdeaMaturityLevel.EXPLORATORY_HYPOTHESIS.value,
            )
        return PrimaryIdeaSelectionResult(
            "NO_COHERENT_IDEA", ranking_records=records,
            rejected_candidate_ids=sorted(rejected), rejection_reasons=rejected,
            warnings=["Every candidate failed at least one fatal scientific gate."],
            automatic_recovery_used=automatic_recovery_used,
            scientific_gate_results=scientific_results, maturity_distribution=distribution,
        )
    highest = max((item[0] for item in eligible), key=maturity_value)
    pool = [item for item in eligible if item[0] == highest]
    fronts = _pareto_fronts([(item[2], item[5]) for item in pool])
    pool.sort(key=lambda item: (fronts[item[2]], -item[1], item[2]))
    winner = pool[0]
    all_ranked = sorted(eligible, key=lambda item: (-maturity_value(item[0]), fronts.get(item[2], 99), -item[1], item[2]))
    ranks = {item[2]: index + 1 for index, item in enumerate(all_ranked)}
    ranked_records = []
    for record in records:
        rank = ranks.get(record.candidate_id, 0)
        reason = ""
        if rank > 1:
            reason = f"Lower maturity/Pareto rank than {winner[3].candidate_name}."
        elif not record.passed_hard_gates:
            reason = "; ".join(record.gate_failures)
        ranked_records.append(CandidateRankingRecord(
            record.candidate_id, record.passed_hard_gates, record.gate_failures,
            record.dimensions, record.weighted_score, rank, reason,
            record.maturity_level, record.fatal_failures, record.maturity_limiters,
            fronts.get(record.candidate_id, 0),
        ))
    confidence = "high" if winner[1] >= .75 else "medium" if winner[1] >= .55 else "low"
    return PrimaryIdeaSelectionResult(
        "SELECTED", winner[3], winner[4], winner[2], ranked_records,
        sorted(rejected), rejected,
        f"Selected from the highest maturity group ({highest.name}) using "
        "non-dominated quality ranking and explicit minimum scientific floors.",
        confidence, automatic_recovery_used=automatic_recovery_used,
        scientific_gate_results=scientific_results, maturity_distribution=distribution,
        selected_maturity_level=highest.value,
    )


def select_primary_idea_legacy(
    *, candidates: Sequence[AlgorithmCandidate],
    derivations: Sequence[IdeaDerivation], direction: DirectionSummary,
    gap: GapSignature, parent_run: ResearchRun,
    automatic_recovery_used: bool = False,
    purpose: PurposeContract | None = None,
    papers: Sequence[Paper] = (),
    full_audits: dict[str, object] | None = None,
) -> PrimaryIdeaSelectionResult:
    """Temporary explicit adapter for internal callers; unknown args still fail."""
    return select_primary_idea(PrimaryIdeaSelectionRequest(
        api_version=PRIMARY_IDEA_SELECTION_API_VERSION,
        candidates=tuple(candidates), derivations=tuple(derivations),
        direction=direction, gap=gap, parent_run=parent_run,
        automatic_recovery_used=automatic_recovery_used,
        purpose=purpose, papers=tuple(papers), full_audits=dict(full_audits or {}),
    ))


def select_primary_idea_with_recovery(
    *, candidates: Sequence[AlgorithmCandidate],
    derivations: Sequence[IdeaDerivation], direction: DirectionSummary,
    gap: GapSignature, parent_run: ResearchRun,
    recover: Callable[[], tuple[Sequence[AlgorithmCandidate], Sequence[IdeaDerivation]]],
    purpose: PurposeContract | None = None,
    papers: Sequence[Paper] = (),
    full_audits: dict[str, object] | None = None,
) -> PrimaryIdeaSelectionResult:
    """Run exactly one bounded evidence-recovery callback when selection fails."""
    initial = select_primary_idea_legacy(
        candidates=candidates, derivations=derivations, direction=direction,
        gap=gap, parent_run=parent_run, purpose=purpose, papers=papers,
        full_audits=full_audits,
    )
    if initial.status in {"SELECTED", "EXPLORATORY_AVAILABLE"}:
        return initial
    recovered_candidates, recovered_derivations = recover()
    result = select_primary_idea_legacy(
        candidates=recovered_candidates, derivations=recovered_derivations,
        direction=direction, gap=gap, parent_run=parent_run,
        automatic_recovery_used=True, purpose=purpose, papers=papers,
        full_audits=full_audits,
    )
    if result.status not in {"SELECTED", "EXPLORATORY_AVAILABLE"}:
        result.warnings.append("One bounded automatic recovery cycle was exhausted.")
    return result
