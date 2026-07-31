"""Lexical queries and canonical structural novelty fingerprints."""

from __future__ import annotations

from models import AlgorithmCandidate
from text_processing import normalize_text


def fingerprint_candidate(candidate: AlgorithmCandidate) -> str:
    parts = [
        candidate.base_algorithm_family, candidate.affected_component,
        *candidate.selected_operators, *candidate.new_state_variables,
        candidate.update_rule_delta, candidate.memory_delta, candidate.routing_delta,
        ",".join(candidate.required_inference_information),
    ]
    return "|".join(normalize_text(part) for part in parts if part)


def novelty_queries(candidate: AlgorithmCandidate) -> list[str]:
    mechanism = " ".join(candidate.borrowed_mechanisms)
    operator = " ".join(candidate.selected_operators)
    return list(dict.fromkeys([
        candidate.candidate_name,
        f"{mechanism} {candidate.base_algorithm}",
        f"{candidate.gap_summary} {mechanism}",
        f"{operator} {candidate.base_algorithm}",
        f"{candidate.base_algorithm_family} {candidate.affected_component} {operator}",
    ]))


def assess_structural_novelty(candidate: AlgorithmCandidate,
                              known_fingerprints: list[str]) -> tuple[str, list[str]]:
    fingerprint = fingerprint_candidate(candidate)
    exact = [known for known in known_fingerprints if normalize_text(known) == normalize_text(fingerprint)]
    if exact:
        return "likely duplicate", exact
    equivalents = candidate.nearest_known_method_patterns
    if equivalents:
        return "known mechanism with new algorithm family", equivalents
    return "potentially structurally novel", []
