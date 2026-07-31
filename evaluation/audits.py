"""Conservative stage-specific quality audits."""

from __future__ import annotations

import re
from hashlib import sha1

from evaluation.schemas import AuditResult
from models import (
    AlgorithmCandidate, AlignmentResult, GapSignature, MechanismSignature,
)


def audit_gap(gap: GapSignature, relevant_paper_ids: set[str]) -> AuditResult:
    supported = bool(set(gap.evidence_paper_ids) & relevant_paper_ids)
    missing = [
        field for field in (
            "failure_type", "affected_component", "observable_failure_signal",
            "required_response",
        ) if not getattr(gap, field)
    ]
    label = "CORRECT" if supported and not missing else (
        "PARTIALLY_CORRECT" if supported else "UNSUPPORTED"
    )
    errors = [] if supported else ["EVIDENCE_EXTRACTION_UNSUPPORTED"]
    return AuditResult(
        gap.gap_id, label,
        ([f"missing fields: {', '.join(missing)}"] if missing else [])
        + (["evidence intersects reviewed relevant papers"] if supported else []),
        errors, {
            "field_completeness": round((4 - len(missing)) / 4, 3),
            "evidence_support": float(supported),
            "abstract_only": float(
                bool(gap.evidence_sections)
                and all(section == "abstract" for section in gap.evidence_sections)
            ),
        },
    )


def audit_coverage_gap(
    gap: object, *, live: bool, known_solution_status: str = "",
    minimum_support: int = 8, maximum_unknown_ratio: float = .45,
) -> AuditResult:
    cluster_size = int(getattr(gap, "cluster_paper_count", 0))
    completeness = float(getattr(gap, "metadata_completeness", 0))
    relevance = float(getattr(gap, "expected_relevance", 0))
    comparable = bool(getattr(gap, "comparison_cells", []))
    if live and cluster_size < minimum_support:
        label, errors = "SAMPLE_SIZE_ARTIFACT", ["COVERAGE_SAMPLE_ARTIFACT"]
    elif 1 - completeness > maximum_unknown_ratio:
        label, errors = "METADATA_ARTIFACT", ["COVERAGE_METADATA_ARTIFACT"]
    elif relevance < .5:
        label, errors = "LOGICALLY_IRRELEVANT", []
    elif not comparable:
        label, errors = "WEAK_SUPPORT", []
    elif known_solution_status == "LIKELY_SOLVED":
        label, errors = "LIKELY_ALREADY_ADDRESSED", []
    else:
        label, errors = "PLAUSIBLE", []
    return AuditResult(
        getattr(gap, "gap_id", "coverage:unknown"), label,
        [f"cluster_size={cluster_size}", f"metadata_completeness={completeness}",
         f"purpose_relevance={relevance}", f"comparable={comparable}"],
        errors,
    )


def audit_mismatch(mismatch: object) -> AuditResult:
    confidence = float(getattr(mismatch, "confidence", 0))
    relation = str(getattr(mismatch, "contradiction_relation", ""))
    evidence = getattr(
        getattr(mismatch, "observed_condition", None), "evidence_sentence", ""
    )
    if "variant" in relation.casefold():
        label, errors = "VARIANT_EXCEPTION", ["ASSUMPTION_WRONG_VARIANT"]
    elif not evidence:
        label, errors = "WEAK_EVIDENCE", ["ASSUMPTION_WRONG_SCOPE"]
    elif confidence >= .75:
        label, errors = "VALID_CONTRADICTION", []
    else:
        label, errors = "VALID_TENSION", []
    return AuditResult(
        getattr(mismatch, "mismatch_id", "mismatch:unknown"), label,
        [f"relation={relation}", f"confidence={confidence}",
         f"evidence_backed={bool(evidence)}"], errors,
    )


def binding_granularity(binding: object) -> str:
    method = str(getattr(binding, "binding_method", "fallback"))
    confidence = float(getattr(binding, "confidence", 0))
    if method == "explicit paper mention" and confidence >= .6:
        return "exact algorithm"
    if getattr(binding, "family", "") and confidence >= .4:
        return "algorithm family"
    if confidence > 0:
        return "broad method class"
    return "unspecified"


def audit_binding(binding: object) -> AuditResult:
    granularity = binding_granularity(binding)
    unsupported = (
        granularity == "exact algorithm"
        and int(getattr(binding, "paper_count", 0)) == 0
    )
    return AuditResult(
        str(getattr(binding, "algorithm", "Unspecified")),
        "unsupported" if unsupported else granularity,
        [f"binding_method={getattr(binding, 'binding_method', '')}",
         f"confidence={getattr(binding, 'confidence', 0)}"],
        ["ALGORITHM_BINDING_UNSUPPORTED"] if unsupported else [],
    )


def audit_known_solution(
    result: object, expected_direct_solution: bool = False,
) -> AuditResult:
    status = str(getattr(result, "status", "insufficient evidence"))
    methods = list(getattr(result, "mitigating_methods", []))
    label = (
        "PARTIALLY_ADDRESSED" if methods or "partial" in status
        else "INSUFFICIENT_SEARCH"
    )
    return AuditResult(
        str(getattr(result, "gap_id", "known:unknown")), label,
        [f"mitigating_methods={len(methods)}",
         str(getattr(result, "search_coverage", ""))],
        ["KNOWN_SOLUTION_MISSED"] if (
            label == "INSUFFICIENT_SEARCH" and expected_direct_solution
        ) else [],
    )


def audit_external_query(domain: str, query: str) -> AuditResult:
    leaked = any(term in query.casefold() for term in (
        "online accuracy", "classifier aggregation",
        "remove stationary distribution", "model robustness",
    ))
    domain_terms = {
        "immunology": ("immune", "antigen", "memory cell", "repertoire"),
        "ecology": ("ecological", "disturbance", "resilience", "legacy", "niche"),
        "control_theory": ("control", "switching", "stability", "mode"),
        "neuroscience": ("context", "pattern completion", "memory guided"),
        "physics": ("hysteresis", "relaxation", "metastable", "transition"),
        "dynamical_systems": ("hysteresis", "relaxation", "metastable", "state"),
    }
    native = any(term in query.casefold() for term in domain_terms.get(domain, (domain,)))
    label = "ML_LANGUAGE_LEAKAGE" if leaked else "GOOD" if native else "UNCERTAIN"
    return AuditResult(
        f"{domain}:{sha1(query.encode()).hexdigest()[:12]}", label,
        [f"domain={domain}", f"native_terminology={native}"],
        ["EXTERNAL_QUERY_LANGUAGE_LEAKAGE"] if leaked else [],
    )


def audit_mechanism(mechanism: MechanismSignature) -> AuditResult:
    required = [
        mechanism.observed_signal, mechanism.internal_state,
        mechanism.response_rule, mechanism.trigger_condition,
        mechanism.adaptation_timescale, mechanism.resource_constraint,
        mechanism.equilibrium_or_target, mechanism.failure_boundary,
    ]
    completeness = sum(bool(value and value != "unspecified") for value in required)
    evidence = bool(mechanism.evidence_sentences and mechanism.evidence_paper_ids)
    generic = mechanism.name.casefold() in {
        "higher", "improved", "robustness", "adaptation", "stability",
    }
    if generic:
        label, errors = "GENERIC_CONCEPT", ["MECHANISM_INVALID"]
    elif completeness >= 6 and evidence:
        label, errors = "VALID_OPERATIONAL_MECHANISM", []
    elif evidence:
        label, errors = "PARTIAL_MECHANISM", []
    else:
        label, errors = "UNSUPPORTED", ["MECHANISM_INVALID"]
    return AuditResult(
        mechanism.mechanism_id, label,
        [f"signature_fields={completeness}/8", f"evidence_supported={evidence}"],
        errors, {"complete_signature": completeness / 8, "evidence_support": float(evidence)},
    )


def audit_alignment(result: AlignmentResult) -> AuditResult:
    if result.rejected and any("slot" in reason for reason in result.rejection_reasons):
        label, errors = "SLOT_INCOMPATIBLE", ["ALIGNMENT_SLOT_INCOMPATIBLE"]
    elif result.rejected:
        label, errors = "SURFACE_SIMILARITY", ["ALIGNMENT_SURFACE_ONLY"]
    elif (
        result.score >= .7 and result.matched_slots
        and result.field_scores.get("topology", 0) >= .75
    ):
        label, errors = "STRONG_STRUCTURAL_MATCH", []
    elif result.score >= .5:
        label, errors = "PLAUSIBLE_MATCH", []
    else:
        label, errors = "SURFACE_SIMILARITY", ["ALIGNMENT_SURFACE_ONLY"]
    return AuditResult(
        f"{result.gap_id}:{result.mechanism_id}", label,
        [f"score={result.score}", f"matched_slots={result.matched_slots}",
         f"conflicts={result.conflicts}"], errors,
    )


def candidate_rubric(candidate: AlgorithmCandidate) -> AuditResult:
    scores = {
        "problem_specificity": min(4, sum(bool(value) for value in (
            candidate.gap_summary, candidate.primary_metric,
            candidate.applicability_conditions,
        )) + 1),
        "evidence_strength": min(4, len(set(candidate.evidence_paper_ids))),
        "algorithm_binding": 4 if candidate.base_algorithm != "Unspecified" else 2,
        "mechanism_operationality": min(4, len(candidate.selected_operators) + 1),
        "modification_specificity": 4 if (
            candidate.affected_component and any((
                candidate.update_rule_delta, candidate.routing_delta,
                candidate.memory_delta, candidate.component_lifecycle_delta,
                candidate.aggregation_delta, candidate.objective_delta,
            ))
        ) else 1,
        "information_feasibility": 4 if not candidate.scores.rejection_flags else 2,
        "novelty_honesty": 3 if candidate.novelty_status == "insufficient evidence" else 2,
        "falsifiability": 4 if (
            candidate.kill_criterion and candidate.falsification_tests
        ) else 0,
        "experiment_feasibility": 4 if (
            candidate.minimal_experiment.hypothesis
            and candidate.minimal_experiment.success_rule
            and candidate.minimal_experiment.failure_rule
        ) else 1,
        "purpose_value": 4 if candidate.expected_improvement else 0,
    }
    errors = []
    if scores["modification_specificity"] < 3:
        errors.append("CANDIDATE_VAGUE")
    if scores["falsifiability"] == 0:
        errors.append("CANDIDATE_UNFALSIFIABLE")
    return AuditResult(
        candidate.candidate_id, "RUBRIC", [], errors,
        {key: float(value) for key, value in scores.items()},
    )
