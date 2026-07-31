"""Transparent normalized multi-objective candidate scoring."""

from __future__ import annotations

from models import AlignmentResult, GapSignature, ScoreCard


def score_candidate(gap: GapSignature, alignment: AlignmentResult, *,
                    purpose_fit: float, feasibility: float, testability: float,
                    novelty: float, diversity: float, complexity_penalty: float = 0.0,
                    duplication_penalty: float = 0.0, metaphor_penalty: float = 0.0,
                    leakage_penalty: float = 0.0) -> ScoreCard:
    components = {
        "gap_evidence": min(1.0, gap.evidence_count / 4),
        "gap_confidence": gap.confidence_score,
        "practical_value": gap.practical_value_score,
        "purpose_fit": purpose_fit,
        "structural_alignment": alignment.score,
        "information_availability": 0.0 if alignment.conflicts else 1.0,
        "feasibility": feasibility,
        "testability": testability,
        "structural_novelty": novelty,
        "literature_support": min(1.0, .3 + .15 * gap.evidence_count),
        "trend": gap.trend_score,
        "diversity_contribution": diversity,
        "operator_compatibility": alignment.field_scores.get("slot", 0.0),
        "algorithm_slot_compatibility": alignment.field_scores.get("slot", 0.0),
    }
    penalties = {
        "complexity": complexity_penalty, "duplication": duplication_penalty,
        "metaphor": metaphor_penalty, "unsupported_claim": .05 if gap.evidence_count < 1 else 0.0,
        "inference_leakage": leakage_penalty, "parameter_count_confound": .05,
        "resource_budget": 0.0,
    }
    positive = sum(components.values()) / len(components)
    total = max(0.0, min(1.0, positive - sum(penalties.values()) / 4))
    confidence = "high" if total >= .72 else "medium" if total >= .48 else "low"
    return ScoreCard({k: round(v, 2) for k, v in components.items()},
                     {k: round(v, 2) for k, v in penalties.items()},
                     round(total, 2), confidence)
