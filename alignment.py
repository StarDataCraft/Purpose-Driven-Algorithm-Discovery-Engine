"""Typed field-level gap-to-mechanism alignment and hard rejection."""

from __future__ import annotations

import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import DATA_DIR, ML_DOMAIN
from models import AlignmentResult, GapSignature, MechanismSignature, PurposeContract

FIELD_PAIRS = {
    "problem": ("failure_type", "original_problem"),
    "signal": ("observable_failure_signal", "observed_signal"),
    "response": ("required_response", "response_rule"),
    "constraint": ("constraints", "resource_constraint"),
    "preservation": ("must_preserve", "equilibrium_or_target"),
    "timescale": ("timescale", "adaptation_timescale"),
}


def _text(value: object) -> str:
    return " ".join(value) if isinstance(value, list) else str(value or "")


def lexical_similarity(left: str, right: str) -> float:
    if not left.strip() or not right.strip():
        return 0.0
    matrix = TfidfVectorizer(ngram_range=(1, 2), stop_words="english").fit_transform([left, right])
    return float(cosine_similarity(matrix[0], matrix[1])[0, 0])


def _slot_weight(name: str, slot: str) -> float:
    matrix = json.loads((DATA_DIR / "compatibility_matrix.json").read_text())
    entry = matrix.get(name, {})
    if slot in entry.get("strong", []):
        return 1.0
    if slot in entry.get("medium", []):
        return .65
    if slot in entry.get("weak", []):
        return .15
    return .5


def align(gap: GapSignature, mechanism: MechanismSignature,
          purpose: PurposeContract | None = None) -> AlignmentResult:
    reasons: list[str] = []
    conflicts: list[str] = []
    missing: list[str] = []
    if mechanism.source_domain == ML_DOMAIN:
        reasons.append("external mechanism source is machine_learning")
    if gap.affected_component in mechanism.incompatible_slots:
        reasons.append("mechanism-slot mapping is explicitly incompatible")
    slot_score = _slot_weight(mechanism.name, gap.affected_component)
    if slot_score <= .15:
        reasons.append("mechanism-slot compatibility is weak")
    scores = {}
    for label, (gap_field, mechanism_field) in FIELD_PAIRS.items():
        left, right = _text(getattr(gap, gap_field)), _text(getattr(mechanism, mechanism_field))
        if not left or not right:
            missing.append(label)
        scores[label] = lexical_similarity(left, right)
    scores["slot"] = slot_score
    scores["evidence"] = min(1.0, .35 + .15 * mechanism.evidence_count)
    available = set(gap.available_inference_information)
    required = set(mechanism.required_signal)
    unavailable = [signal for signal in required if signal not in available and
                   not any(word in " ".join(available).casefold() for word in signal.casefold().split())]
    if purpose and unavailable:
        conflicts.extend(f"unavailable inference signal: {signal}" for signal in unavailable)
    if purpose and any(term in " ".join(mechanism.required_signal).casefold()
                       for term in ("clean label", "future observation", "ground truth state")):
        reasons.append("inference leakage")
    weighted = (.16 * scores["problem"] + .15 * scores["signal"] + .18 * scores["response"]
                + .08 * scores["constraint"] + .08 * scores["preservation"]
                + .05 * scores["timescale"] + .22 * slot_score + .08 * scores["evidence"])
    weighted -= .08 * len(conflicts) + .03 * len(missing)
    return AlignmentResult(gap.gap_id, mechanism.mechanism_id, scores,
                           [gap.affected_component] if slot_score > .15 else [],
                           conflicts, missing, max(0.0, min(1.0, weighted)),
                           bool(reasons), reasons)
