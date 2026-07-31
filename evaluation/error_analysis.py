"""Canonical scientific-quality error taxonomy."""

from __future__ import annotations

from collections import Counter

ERROR_TAXONOMY = frozenset({
    "RETRIEVAL_IRRELEVANT", "RETRIEVAL_MISSED_REFERENCE",
    "RERANKING_FAILURE", "QUERY_TOO_BROAD", "QUERY_TOO_NARROW",
    "QUERY_ALGORITHM_LOCK", "EVIDENCE_EXTRACTION_MISSED",
    "EVIDENCE_EXTRACTION_UNSUPPORTED", "WRONG_FAILURE_TYPE",
    "WRONG_METRIC", "WRONG_TRAINING_INFERENCE_SCOPE",
    "COVERAGE_SAMPLE_ARTIFACT", "COVERAGE_METADATA_ARTIFACT",
    "ASSUMPTION_WRONG_VARIANT", "ASSUMPTION_WRONG_SCOPE",
    "ALGORITHM_BINDING_UNSUPPORTED", "KNOWN_SOLUTION_MISSED",
    "EXTERNAL_QUERY_LANGUAGE_LEAKAGE", "EXTERNAL_DOMAIN_MISMATCH",
    "MECHANISM_INVALID", "MECHANISM_METAPHORICAL",
    "ALIGNMENT_SURFACE_ONLY", "ALIGNMENT_SLOT_INCOMPATIBLE",
    "CANDIDATE_VAGUE", "CANDIDATE_DUPLICATE",
    "CANDIDATE_INFORMATION_LEAKAGE", "CANDIDATE_UNFALSIFIABLE",
})


def error_counts(results: list[object]) -> dict[str, int]:
    counts = Counter(
        error for result in results for error in getattr(result, "errors", [])
        if error in ERROR_TAXONOMY
    )
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def dominant_bottleneck(counts: dict[str, int]) -> str:
    if not counts:
        return "INSUFFICIENT_REVIEW"
    error = max(counts, key=counts.get)
    return error.split("_", 1)[0]
