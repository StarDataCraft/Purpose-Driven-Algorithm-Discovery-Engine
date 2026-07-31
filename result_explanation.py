"""Human-readable, deterministic explanation of an algorithm derivation."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from models import AlgorithmCandidate, AlignmentResult, GapSignature, MechanismSignature
from research_runs import ResearchRun


def research_result(
    run: ResearchRun | None, gap: GapSignature | None,
    mechanism: MechanismSignature | None, alignment: AlignmentResult | None,
    candidate: AlgorithmCandidate | None,
) -> dict[str, Any]:
    if not candidate or not gap:
        return {"conclusion": "No candidate result has been produced yet."}
    supported = {
        "paper_ids": list(dict.fromkeys(
            [*gap.evidence_paper_ids, *candidate.evidence_paper_ids]
        )),
        "evidence_sentences": gap.evidence_sentences[:5],
    }
    inferred = {
        "gap": gap.unresolved_remainder or gap.title,
        "transfer": (
            f"Apply {mechanism.name} to {candidate.affected_component}"
            if mechanism else "Mechanism mapping unavailable"
        ),
        "expected_change": candidate.expected_improvement,
    }
    unknown = list(dict.fromkeys([
        *candidate.expected_failure_modes,
        *candidate.scores.missing_evidence,
    ]))
    funnel = {
        "candidate_papers": run.candidate_paper_count if run else 0,
        "automatically_relevant": (
            run.automatically_relevant_paper_count if run else 0
        ),
        "evidence_events": run.evidence_event_count if run else 0,
        "raw_gap_instances": run.raw_gap_instance_count if run else 0,
        "canonical_gap_families": run.canonical_gap_family_count if run else 0,
        "promoted_gaps": run.promoted_gap_count if run else 0,
        "candidates": run.candidate_count if run else 0,
    }
    return {
        "conclusion": (
            f"Modify {candidate.base_algorithm}'s {candidate.affected_component} "
            f"with {', '.join(candidate.borrowed_mechanisms)} to address "
            f"{gap.failure_type}; reject the proposal if "
            f"{candidate.kill_criterion or candidate.minimal_experiment.failure_rule}."
        ),
        "gap": gap.title,
        "mechanism": mechanism.name if mechanism else "unknown",
        "alignment": (
            {"score": alignment.score, "matched_slots": alignment.matched_slots}
            if alignment else {"status": "unknown"}
        ),
        "before": candidate.base_algorithm,
        "change": {
            "component": candidate.affected_component,
            "operators": candidate.selected_operators,
            "update_rule": candidate.update_rule_delta,
            "state": candidate.new_state_variables,
        },
        "expected": candidate.expected_improvement,
        "supported": supported,
        "system_inferred": inferred,
        "unknown": unknown or ["Independent experimental validation"],
        "confidence": asdict(candidate.scores),
        "derivation_funnel": funnel,
    }
