"""Deterministic review-queue construction for a future SciBERT training cycle."""

from __future__ import annotations

from dataclasses import dataclass
import random


@dataclass(frozen=True)
class ActiveLearningItem:
    item_id: str
    uncertainty: float
    rule_model_disagreement: float
    label_conflict: float
    diversity: float
    rare_class_bonus: float
    impact: float
    unsupported_prediction: float
    no_cue_bonus: float
    priority: float = 0.0


def prioritize_review_queue(
    items: list[ActiveLearningItem], *, seed: int = 17,
) -> list[ActiveLearningItem]:
    """Rank annotation work without treating the base model as a classifier."""
    rng = random.Random(seed)
    scored = []
    for item in items:
        score = (
            .25 * item.uncertainty
            + .18 * item.rule_model_disagreement
            + .14 * item.label_conflict
            + .12 * item.diversity
            + .08 * item.rare_class_bonus
            + .10 * item.impact
            + .08 * item.unsupported_prediction
            + .05 * item.no_cue_bonus
        )
        scored.append((
            round(score, 6), rng.random(),
            ActiveLearningItem(**{
                **item.__dict__, "priority": round(score, 6),
            }),
        ))
    return [row[2] for row in sorted(
        scored, key=lambda row: (-row[0], row[1], row[2].item_id)
    )]
