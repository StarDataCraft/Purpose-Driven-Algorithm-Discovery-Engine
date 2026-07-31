"""Typed algorithm assumptions, observed conditions, and predicate contradictions."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from hashlib import sha1
from pathlib import Path

from config import DATA_DIR
from models import GapSignature, Paper, PurposeContract
from text_processing import split_sentences


@dataclass
class AlgorithmAssumption:
    assumption_id: str
    algorithm: str
    algorithm_family: str
    assumption_type: str
    assumption_statement: str
    normalized_predicate: str
    required_condition: str
    violated_by_conditions: list[str]
    affected_slots: list[str]
    expected_failure_modes: list[str]
    relevant_metrics: list[str]
    severity: str
    canonical_reference: str
    source_type: str
    confidence: float
    necessity: str = "strong"
    variant_exceptions: list[str] = field(default_factory=list)
    context_notes: str = ""
    known_mitigations: list[str] = field(default_factory=list)


@dataclass
class ObservedCondition:
    condition_id: str
    paper_id: str
    condition_type: str
    normalized_predicate: str
    value: str
    scope: str
    evidence_sentence: str
    evidence_section: str
    extraction_method: str
    confidence: float


@dataclass
class AssumptionMismatch:
    mismatch_id: str
    gap_type: str
    title: str
    algorithm: str
    algorithm_family: str
    assumption: AlgorithmAssumption
    observed_condition: ObservedCondition
    contradiction_relation: str
    contradiction_strength: float
    evidence_scope: str
    affected_component: str
    expected_failure_mode: str
    observable_failure_signal: str
    required_response: str
    affected_metrics: list[str]
    must_preserve: list[str]
    evidence_paper_ids: list[str]
    evidence_sentences: list[str]
    source_diversity: int
    practical_relevance: float
    testability: float
    confidence: float
    rejection_flags: list[str] = field(default_factory=list)
    variant_exceptions: list[str] = field(default_factory=list)
    known_mitigating_methods: list[str] = field(default_factory=list)
    unresolved_remainder: str = ""


CONDITION_PATTERNS = {
    "recurring_drift": r"recurring (?:concept )?drift|previously seen regimes return",
    "nonstationarity": r"nonstationar|concept drift|regime switch|regime change",
    "inference_missingness": r"missing features? at inference|inference-time missing|complete features",
    "correlated_features": r"correlated features?|interacting feature groups",
    "heterogeneous_density": r"heterogeneous|varying cluster density",
    "dynamic_component_count": r"cluster birth|cluster death|dynamic (?:cluster|component)",
    "partial_observability": r"partial(?:ly)? observ|latent regime|limited sensor",
    "delayed_labels": r"delayed labels?|delayed outcome",
    "limited_memory": r"limited memory|memory budget",
    "limited_compute": r"compute budget|limited compute|latency",
    "gaussian_data": r"Gaussian data|normal distribution",
}

RELATIONS = {
    ("stationary_distribution", "recurring_drift"): ("contradiction", 1.0),
    ("stationary_distribution", "nonstationarity"): ("contradiction", .95),
    ("complete_features", "inference_missingness"): ("contradiction", 1.0),
    ("fixed_component_count", "dynamic_component_count"): ("contradiction", 1.0),
    ("conditional_independence", "correlated_features"): ("strong tension", .85),
    ("full_observability", "partial_observability"): ("contradiction", 1.0),
    ("gaussianity", "gaussian_data"): ("compatible", .95),
}


def load_assumption_registry(path: Path | None = None) -> list[AlgorithmAssumption]:
    values = json.loads((path or DATA_DIR / "assumption_registry.json").read_text())
    return [AlgorithmAssumption(**value) for value in values]


def extract_observed_conditions(papers: list[Paper], purpose: PurposeContract | None = None
                                ) -> list[ObservedCondition]:
    conditions = []
    for paper in papers:
        sections = paper.sections or {"abstract": paper.abstract}
        for section, text in sections.items():
            for sentence in split_sentences(text):
                for condition_type, pattern in CONDITION_PATTERNS.items():
                    if re.search(pattern, sentence, re.I):
                        scope = "inference" if "inference" in sentence.casefold() else \
                            "training" if "training" in sentence.casefold() else "application"
                        conditions.append(ObservedCondition(
                            condition_id="condition:" + sha1(
                                f"{paper.paper_id}:{condition_type}:{sentence}".encode()
                            ).hexdigest()[:12],
                            paper_id=paper.paper_id, condition_type=condition_type,
                            normalized_predicate=condition_type, value="present",
                            scope=scope, evidence_sentence=sentence,
                            evidence_section=section, extraction_method="controlled_pattern",
                            confidence=.9 if section.casefold() != "abstract" else .65,
                        ))
    if purpose:
        purpose_text = " ".join([
            purpose.current_failure, purpose.deployment_environment,
            *purpose.available_inference_information, *purpose.user_notes.split(),
        ])
        for condition_type, pattern in CONDITION_PATTERNS.items():
            if re.search(pattern, purpose_text, re.I):
                conditions.append(ObservedCondition(
                    condition_id=f"condition:purpose:{condition_type}", paper_id="purpose",
                    condition_type=condition_type, normalized_predicate=condition_type,
                    value="present", scope="application", evidence_sentence=purpose_text,
                    evidence_section="purpose_contract", extraction_method="purpose_contract_rule",
                    confidence=.95,
                ))
    return conditions


def detect_assumption_mismatches(
    assumptions: list[AlgorithmAssumption],
    conditions: list[ObservedCondition],
    used_algorithms: set[str],
    purpose: PurposeContract,
    variant_names: list[str] | None = None,
) -> list[AssumptionMismatch]:
    variant_text = " ".join(variant_names or []).casefold()
    output = []
    for assumption in assumptions:
        if assumption.algorithm not in used_algorithms and assumption.algorithm_family not in used_algorithms:
            continue
        if any(exception.casefold() in variant_text for exception in assumption.variant_exceptions):
            continue
        for condition in conditions:
            relation = RELATIONS.get(
                (assumption.normalized_predicate, condition.normalized_predicate),
                ("insufficient evidence", 0.0),
            )
            if relation[0] not in {"strong tension", "contradiction"}:
                continue
            confidence = min(assumption.confidence, condition.confidence) * relation[1]
            output.append(AssumptionMismatch(
                mismatch_id="mismatch:" + sha1(
                    f"{assumption.assumption_id}:{condition.condition_id}".encode()
                ).hexdigest()[:12],
                gap_type="assumption_mismatch",
                title=f"{assumption.algorithm}: {assumption.assumption_statement} conflicts with {condition.condition_type}",
                algorithm=assumption.algorithm, algorithm_family=assumption.algorithm_family,
                assumption=assumption, observed_condition=condition,
                contradiction_relation=relation[0], contradiction_strength=relation[1],
                evidence_scope=condition.scope,
                affected_component=assumption.affected_slots[0],
                expected_failure_mode=assumption.expected_failure_modes[0],
                observable_failure_signal=f"degradation in {assumption.relevant_metrics[0]}",
                required_response=f"remove or adapt {assumption.required_condition}",
                affected_metrics=assumption.relevant_metrics,
                must_preserve=purpose.must_not_degrade,
                evidence_paper_ids=[condition.paper_id],
                evidence_sentences=[condition.evidence_sentence],
                source_diversity=1, practical_relevance=.85, testability=.85,
                confidence=round(confidence, 2),
                variant_exceptions=assumption.variant_exceptions,
                known_mitigating_methods=assumption.known_mitigations,
                unresolved_remainder="Validate the mismatch under matched conditions.",
            ))
    return output


def mismatch_to_signature(mismatch: AssumptionMismatch, purpose: PurposeContract) -> GapSignature:
    return GapSignature(
        gap_id=mismatch.mismatch_id, title=mismatch.title, gap_type="structural",
        task=purpose.task, application_context=purpose.use_case, data_type=purpose.data_type,
        affected_algorithm=mismatch.algorithm,
        affected_algorithm_family=mismatch.algorithm_family,
        failure_type=mismatch.expected_failure_mode,
        affected_component=mismatch.affected_component,
        current_method_pattern=mismatch.assumption.assumption_statement,
        observable_failure_signal=mismatch.observable_failure_signal,
        required_response=mismatch.required_response,
        unresolved_assumptions=[mismatch.assumption.assumption_statement],
        constraints=[], must_preserve=mismatch.must_preserve,
        primary_metric=purpose.primary_metric, secondary_metrics=purpose.secondary_metrics,
        available_training_information=purpose.available_training_information,
        available_inference_information=purpose.available_inference_information,
        evidence_sentences=mismatch.evidence_sentences,
        evidence_sections=[mismatch.observed_condition.evidence_section],
        evidence_paper_ids=mismatch.evidence_paper_ids,
        evidence_count=len(mismatch.evidence_paper_ids),
        source_diversity=mismatch.source_diversity, explicitness_score=0,
        aggregation_score=0, structural_gap_score=mismatch.contradiction_strength,
        trend_score=.5, practical_value_score=mismatch.practical_relevance,
        testability_score=mismatch.testability, confidence_score=mismatch.confidence,
        detection_method="predicate_contradiction",
        structural_gap_subtype="assumption_mismatch", mismatch_id=mismatch.mismatch_id,
        field_provenance={
            "assumption": mismatch.assumption.source_type,
            "condition": mismatch.observed_condition.extraction_method,
        },
        contradiction_evidence=[
            f"{mismatch.assumption.normalized_predicate} -> "
            f"{mismatch.observed_condition.normalized_predicate}: "
            f"{mismatch.contradiction_relation}"
        ],
        known_mitigations=mismatch.known_mitigating_methods,
        unresolved_remainder=mismatch.unresolved_remainder,
        metadata_completeness=.85,
        evidence_strength_components={
            "assumption_contradiction_strength": mismatch.contradiction_strength,
            "condition_confidence": mismatch.observed_condition.confidence,
        },
    )
