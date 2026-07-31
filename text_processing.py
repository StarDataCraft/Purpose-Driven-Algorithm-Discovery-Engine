"""Deterministic section-aware scientific text processing."""

from __future__ import annotations

import re
from hashlib import sha1

SECTION_WEIGHTS = {
    "limitations": 1.0, "future work": 1.0, "discussion": .9, "conclusion": .9,
    "error analysis": .85, "ablation": .75, "experiments": .65,
    "introduction": .55, "abstract": .4,
}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s\-]", " ", text.casefold())).strip()


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if len(part.strip()) > 20]


def normalized_title(title: str) -> str:
    return normalize_text(re.sub(r"\b(a|an|the)\b", " ", title))


def fingerprint(text: str) -> str:
    return sha1(normalize_text(text).encode()).hexdigest()[:16]


def section_weight(section: str) -> float:
    key = section.casefold()
    return max((weight for name, weight in SECTION_WEIGHTS.items() if name in key), default=.35)
