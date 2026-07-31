"""Conflict-aware multi-label weak supervision for scientific gap sentences."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class GapLabel(str, Enum):
    BACKGROUND = "BACKGROUND"
    CONTRIBUTION = "CONTRIBUTION"
    METHOD = "METHOD"
    RESULT = "RESULT"
    LIMITATION = "LIMITATION"
    FAILURE_CONDITION = "FAILURE_CONDITION"
    ASSUMPTION = "ASSUMPTION"
    FUTURE_WORK = "FUTURE_WORK"
    MISSING_EVALUATION = "MISSING_EVALUATION"
    DEPLOYMENT_CONSTRAINT = "DEPLOYMENT_CONSTRAINT"
    RESOURCE_CONSTRAINT = "RESOURCE_CONSTRAINT"
    EXPERIMENTAL_FAILURE = "EXPERIMENTAL_FAILURE"
    CONTRADICTORY_RESULT = "CONTRADICTORY_RESULT"
    OTHER = "OTHER"


ABSTAIN = 0
POSITIVE = 1
NEGATIVE = -1


@dataclass
class RuleVote:
    rule: str
    label: str
    vote: int
    weight: float


@dataclass
class WeakLabelResult:
    labels: list[str]
    probability_by_label: dict[str, float]
    rule_votes: list[RuleVote]
    confidence: float
    conflicts: list[str]


RULES = [
    ("limitation_cue", GapLabel.LIMITATION, r"\b(limitation|limited|struggles?|cannot|however)\b", 1.0),
    ("failure_pattern", GapLabel.FAILURE_CONDITION, r"\b(fails?|degrades?|poor|unstable|sensitive)\b", 1.0),
    ("experimental_failure", GapLabel.EXPERIMENTAL_FAILURE, r"\b(experiment|trial|evaluation).{0,40}\b(failed|degraded|unstable)\b", .95),
    ("assumption_construction", GapLabel.ASSUMPTION, r"\b(assumes?|requires? complete|depends? on)\b", .95),
    ("future_work", GapLabel.FUTURE_WORK, r"\b(future work|remains? to|should investigate)\b", .9),
    ("missing_evaluation", GapLabel.MISSING_EVALUATION, r"\b(not evaluated|lacks? evaluation|no .* benchmark)\b", 1.0),
    ("deployment", GapLabel.DEPLOYMENT_CONSTRAINT, r"\b(at inference|deployment|sensor access|future context)\b", .9),
    ("resource", GapLabel.RESOURCE_CONSTRAINT, r"\b(memory|latency|compute|runtime|resource budget)\b", .85),
    ("contradiction", GapLabel.CONTRADICTORY_RESULT, r"\b(in contrast|conflicting|whereas .* degrades)\b", .85),
    ("contribution", GapLabel.CONTRIBUTION, r"\b(we propose|we introduce|novel framework)\b", .8),
    ("result", GapLabel.RESULT, r"\b(achieves?|outperforms?|results? show)\b", .75),
    ("method", GapLabel.METHOD, r"\b(we train|algorithm|objective|update rule)\b", .65),
]


def label_sentence(sentence: str, section: str = "") -> WeakLabelResult:
    votes = []
    scores = {label.value: 0.0 for label in GapLabel}
    for name, label, pattern, weight in RULES:
        if re.search(pattern, sentence, re.I):
            adjusted = weight
            if section.casefold() in {"limitations", "discussion", "future work"} and label in {
                GapLabel.LIMITATION, GapLabel.FAILURE_CONDITION, GapLabel.FUTURE_WORK
            }:
                adjusted += .2
            if section.casefold() == "abstract" and label == GapLabel.CONTRIBUTION:
                adjusted += .1
            votes.append(RuleVote(name, label.value, POSITIVE, adjusted))
            scores[label.value] += adjusted
    conflicts = []
    if scores[GapLabel.CONTRIBUTION] and scores[GapLabel.LIMITATION]:
        conflicts.append("contribution_limitation")
    probabilities = {
        label: round(min(1.0, score / 1.2), 3)
        for label, score in scores.items() if score
    }
    labels = [label for label, probability in probabilities.items() if probability >= .55]
    if not labels:
        labels = [GapLabel.OTHER.value]
        probabilities[GapLabel.OTHER.value] = .55
    confidence = max(probabilities.values()) * (0.85 if conflicts else 1.0)
    return WeakLabelResult(labels, probabilities, votes, round(confidence, 3), conflicts)
