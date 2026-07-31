"""Validated external-mechanism extraction with evidence preservation."""

from __future__ import annotations

import json
import re
from copy import deepcopy

from config import DATA_DIR, ML_DOMAIN
from models import MechanismSignature, Paper
from signatures import load_mechanism_seeds
from text_processing import normalize_text, split_sentences


def _resources() -> tuple[set[str], set[str]]:
    data = json.loads((DATA_DIR / "stopwords.json").read_text())
    return set(data["invalid_mechanisms"]), set(data["mechanism_cues"])


def validate_mechanism_phrase(phrase: str, source_domain: str = "") -> tuple[bool, list[str]]:
    invalid, cues = _resources()
    normalized = normalize_text(phrase)
    reasons = []
    if not normalized or normalized in invalid:
        reasons.append("invalid or generic phrase")
    if len(normalized.split()) < 2:
        reasons.append("mechanism must be a specific multi-token process")
    if not any(cue in normalized for cue in cues):
        reasons.append("no process, state, feedback, allocation, or transition cue")
    if source_domain == ML_DOMAIN:
        reasons.append("machine-learning source is not cross-disciplinary")
    return not reasons, reasons


def extract_mechanisms(papers: list[Paper]) -> tuple[list[MechanismSignature], list[dict[str, str]]]:
    seeds = load_mechanism_seeds()
    extracted: dict[str, MechanismSignature] = {}
    rejected: list[dict[str, str]] = []
    for paper in papers:
        domain = paper.domain
        for sentence in split_sentences(" ".join([paper.abstract, *paper.sections.values()])):
            normalized = normalize_text(sentence)
            matched = False
            for seed in seeds:
                tokens = [token for token in normalize_text(seed.name).split() if len(token) > 4]
                if sum(token in normalized for token in tokens) < 1:
                    continue
                matched = True
                mechanism = extracted.get(seed.mechanism_id, deepcopy(seed))
                mechanism.source_domain = domain or seed.source_domain
                mechanism.evidence_sentences = list(dict.fromkeys(mechanism.evidence_sentences + [sentence]))
                mechanism.evidence_sections = list(dict.fromkeys(mechanism.evidence_sections + ["abstract"]))
                mechanism.evidence_paper_ids = list(dict.fromkeys(mechanism.evidence_paper_ids + [paper.paper_id]))
                mechanism.evidence_count = len(mechanism.evidence_paper_ids)
                mechanism.confidence_score = min(.98, seed.confidence_score + .02 * mechanism.evidence_count)
                valid, reasons = validate_mechanism_phrase(mechanism.name, mechanism.source_domain)
                if valid:
                    extracted[seed.mechanism_id] = mechanism
                else:
                    rejected.append({"phrase": mechanism.name, "reason": "; ".join(reasons)})
            if not matched:
                for generic in re.findall(r"\b(?:higher|proposed|effective|research|significant|novel|improved|performance)\b", normalized):
                    rejected.append({"phrase": generic, "reason": "invalid or generic phrase"})
    return list(extracted.values()), rejected


def cross_domain_only(mechanisms: list[MechanismSignature]) -> list[MechanismSignature]:
    return [mechanism for mechanism in mechanisms if mechanism.source_domain != ML_DOMAIN]
