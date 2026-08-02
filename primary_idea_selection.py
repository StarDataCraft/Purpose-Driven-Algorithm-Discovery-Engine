"""Deterministic hard-gated selection of the primary algorithm idea."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Callable, Sequence

from models import AlgorithmCandidate, GapSignature
from run_models import ResearchRun
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
        }


def _known(value: str) -> bool:
    return value.strip().casefold() not in {"", "unknown", "unspecified", "none"}


def _gate_failures(
    candidate: AlgorithmCandidate, derivation: IdeaDerivation,
    direction: DirectionSummary, gap: GapSignature, run: ResearchRun,
) -> list[str]:
    failures: list[str] = []
    if not run.run_id or candidate.research_run_id != run.run_id:
        failures.append("invalid parent ResearchRun")
    if direction.parent_run_id != run.run_id or derivation.direction_id != direction.direction_id:
        failures.append("invalid selected direction")
    if gap.gap_id != candidate.gap_id or derivation.selected_gap_snapshot.get("gap_id") != gap.gap_id:
        failures.append("invalid selected gap")
    if run.evidence_bearing_paper_count < 1 or direction.evidence_bearing_paper_count < 1:
        failures.append("no evidence-bearing ML papers")
    if not run.external_paper_ids:
        failures.append("no external evidence")
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
        failures.append("missing exact modification slot")
    modification = candidate_modification(candidate).strip()
    generic = {
        "improve aggregation", "add memory", "increase robustness",
        "use adaptation", "apply feedback", "combine mechanisms",
        "no concrete modification was generated.",
    }
    if modification.casefold() in generic or len(modification.split()) < 3:
        failures.append("modification is generic or metaphor-only")
    if not candidate.new_state_variables and not candidate.selected_operators:
        failures.append("no concrete new state, trigger, or rule")
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
        failures.append("minimal experiment is incomplete")
    if not candidate.kill_criterion and not experiment.failure_rule:
        failures.append("missing kill criterion")
    if not candidate.novelty_status or not candidate.nearest_known_method_patterns:
        failures.append("known-solution or prior-art status is absent")
    if not derivation.uncertainties and not candidate.scores.missing_evidence:
        failures.append("explicit uncertainty is absent")
    if candidate.scores.rejection_flags:
        failures.extend(f"candidate rejection flag: {item}" for item in candidate.scores.rejection_flags)
    return failures


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
    *, candidates: Sequence[AlgorithmCandidate],
    derivations: Sequence[IdeaDerivation], direction: DirectionSummary,
    gap: GapSignature, parent_run: ResearchRun,
    automatic_recovery_used: bool = False,
) -> PrimaryIdeaSelectionResult:
    """Apply non-overridable gates, then stable weighted ranking."""
    if not candidates:
        return PrimaryIdeaSelectionResult(
            "NO_CANDIDATES", automatic_recovery_used=automatic_recovery_used,
        )
    derivation_by_id = {item.candidate_id: item for item in derivations}
    records: list[CandidateRankingRecord] = []
    rejected: dict[str, list[str]] = {}
    weights = {
        "user_problem_fit": .12, "evidence_strength": .10,
        "gap_validity": .10, "known_solution_risk": .07,
        "mechanism_quality": .09, "structural_alignment_quality": .12,
        "algorithm_specificity": .10, "implementation_feasibility": .08,
        "inference_information_availability": .07, "falsifiability": .07,
        "expected_metric_relevance": .04, "compute_memory_cost": .02,
        "uncertainty": .02,
    }
    valid: list[tuple[float, str, AlgorithmCandidate, IdeaDerivation, dict[str, float]]] = []
    for candidate in candidates:
        derivation = derivation_by_id.get(candidate.candidate_id)
        failures = (["missing matching derivation"] if derivation is None else
                    _gate_failures(candidate, derivation, direction, gap, parent_run))
        dims = _dimensions(candidate, derivation) if derivation else {}
        score = round(sum(weights[key] * dims.get(key, 0.0) for key in weights), 6)
        if failures:
            rejected[candidate.candidate_id] = failures
        else:
            valid.append((score, candidate.candidate_id, candidate, derivation, dims))
        records.append(CandidateRankingRecord(
            candidate.candidate_id, not failures, tuple(failures), dims, score,
        ))
    if not valid:
        return PrimaryIdeaSelectionResult(
            "NO_CANDIDATE_PASSED", ranking_records=records,
            rejected_candidate_ids=sorted(rejected), rejection_reasons=rejected,
            warnings=["No candidate satisfied every scientific hard gate."],
            automatic_recovery_used=automatic_recovery_used,
        )
    valid.sort(key=lambda item: (-item[0], item[1]))
    winner = valid[0]
    ranks = {candidate_id: index + 1 for index, (_, candidate_id, *_rest) in enumerate(valid)}
    ranked_records = []
    for record in records:
        rank = ranks.get(record.candidate_id, 0)
        reason = ""
        if rank > 1:
            reason = f"Lower hard-gated weighted score than {winner[2].candidate_name}."
        elif not record.passed_hard_gates:
            reason = "; ".join(record.gate_failures)
        ranked_records.append(CandidateRankingRecord(
            record.candidate_id, record.passed_hard_gates, record.gate_failures,
            record.dimensions, record.weighted_score, rank, reason,
        ))
    confidence = "high" if winner[0] >= .75 else "medium" if winner[0] >= .55 else "low"
    return PrimaryIdeaSelectionResult(
        "SELECTED", winner[2], winner[3], winner[1], ranked_records,
        sorted(rejected), rejected,
        "Selected after all scientific hard gates; it had the strongest "
        "weighted evidence, structural alignment, algorithm specificity, "
        "information availability, feasibility, and falsifiability profile.",
        confidence, automatic_recovery_used=automatic_recovery_used,
    )


def select_primary_idea_with_recovery(
    *, candidates: Sequence[AlgorithmCandidate],
    derivations: Sequence[IdeaDerivation], direction: DirectionSummary,
    gap: GapSignature, parent_run: ResearchRun,
    recover: Callable[[], tuple[Sequence[AlgorithmCandidate], Sequence[IdeaDerivation]]],
) -> PrimaryIdeaSelectionResult:
    """Run exactly one bounded evidence-recovery callback when selection fails."""
    initial = select_primary_idea(
        candidates=candidates, derivations=derivations, direction=direction,
        gap=gap, parent_run=parent_run,
    )
    if initial.status == "SELECTED":
        return initial
    recovered_candidates, recovered_derivations = recover()
    result = select_primary_idea(
        candidates=recovered_candidates, derivations=recovered_derivations,
        direction=direction, gap=gap, parent_run=parent_run,
        automatic_recovery_used=True,
    )
    if result.status != "SELECTED":
        result.warnings.append("One bounded automatic recovery cycle was exhausted.")
    return result
