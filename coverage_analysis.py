"""Sparse evidence coverage extraction and relevance-aware omission detection."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from hashlib import sha1
from typing import Any

from models import GapSignature, Paper, PurposeContract
from text_processing import split_sentences

UNKNOWN = "UNKNOWN"


@dataclass
class CoverageRecord:
    record_id: str
    paper_id: str
    task: str = UNKNOWN
    task_subtype: str = UNKNOWN
    application_domain: str = UNKNOWN
    algorithm: str = UNKNOWN
    algorithm_family: str = UNKNOWN
    data_type: str = UNKNOWN
    dataset: str = UNKNOWN
    benchmark: str = UNKNOWN
    training_conditions: list[str] = field(default_factory=list)
    inference_conditions: list[str] = field(default_factory=list)
    distribution_conditions: list[str] = field(default_factory=list)
    missingness_conditions: list[str] = field(default_factory=list)
    deployment_conditions: list[str] = field(default_factory=list)
    evaluation_protocols: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    metric_categories: list[str] = field(default_factory=list)
    failure_conditions: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    publication_year: int = 0
    source: str = UNKNOWN
    evidence_sentences: list[str] = field(default_factory=list)
    evidence_sections: list[str] = field(default_factory=list)
    field_provenance: dict[str, str] = field(default_factory=dict)
    confidence_by_field: dict[str, float] = field(default_factory=dict)
    overall_confidence: float = 0.0


@dataclass
class CoverageGap:
    gap_id: str
    gap_type: str
    title: str
    research_cluster_id: str
    covered_dimensions: dict[str, list[str]]
    missing_combination: dict[str, str]
    comparison_cells: list[dict[str, Any]]
    expected_relevance: float
    observed_count: int
    neighboring_count: int
    cluster_paper_count: int
    source_diversity: int
    year_span: int
    omission_persistence: float
    metadata_completeness: float
    practical_importance: float
    evaluation_feasibility: float
    affected_algorithms: list[str]
    affected_tasks: list[str]
    primary_missing_metric: str
    proposed_evaluation_setting: str
    evidence_paper_ids: list[str]
    evidence_sentences: list[str]
    confidence: float
    rejection_flags: list[str] = field(default_factory=list)
    score_components: dict[str, float] = field(default_factory=dict)


PATTERNS = {
    "missingness": {
        "MNAR": r"\bMNAR\b|missing not at random",
        "MAR": r"\bMAR\b|missing at random",
        "MCAR": r"\bMCAR\b|missing completely at random",
        "train-test mismatch": r"train[- ]test missing|missingness shift",
    },
    "distribution": {
        "recurring drift": r"recurring concept drift|recurring regime",
        "distribution shift": r"distribution shift|domain shift",
        "nonstationary": r"nonstationar|regime switch",
        "IID": r"\bIID\b|independent and identically distributed",
    },
    "metrics": {
        "calibration": r"calibration|ECE|Brier",
        "robustness": r"robustness|recovery time|stability",
        "accuracy": r"accuracy|AUROC|F1",
        "clustering": r"\bARI\b|\bNMI\b",
        "efficiency": r"latency|memory|runtime|compute",
    },
    "protocols": {
        "stress test": r"stress test|under shift|missingness mismatch",
        "cross-validation": r"cross[- ]validation",
        "online evaluation": r"online accuracy|streaming evaluation",
        "standard benchmark": r"benchmark|test set",
    },
}


def _matches(text: str, mapping: dict[str, str]) -> list[str]:
    return [name for name, pattern in mapping.items() if re.search(pattern, text, re.I)]


def extract_coverage_records(papers: list[Paper], purpose: PurposeContract | None = None
                             ) -> list[CoverageRecord]:
    records = []
    for paper in papers:
        text = " ".join([paper.title, paper.abstract, *paper.sections.values()])
        sentences = split_sentences(text)
        missingness = _matches(text, PATTERNS["missingness"])
        distribution = _matches(text, PATTERNS["distribution"])
        metrics = _matches(text, PATTERNS["metrics"])
        protocols = _matches(text, PATTERNS["protocols"])
        algorithm = next((name for name in (
            "Random Forest", "K-means", "Gaussian Process", "Naive Bayes",
            "Deep Ensemble", "Transformer"
        ) if name.casefold() in text.casefold()), UNKNOWN)
        family = {
            "Random Forest": "ensemble", "Deep Ensemble": "ensemble",
            "K-means": "clustering", "Gaussian Process": "probabilistic_kernel",
            "Naive Bayes": "probabilistic_classifier", "Transformer": "attention_model",
        }.get(algorithm, UNKNOWN)
        known = [
            purpose.task if purpose else UNKNOWN, algorithm,
            *missingness, *distribution, *metrics, *protocols,
        ]
        completeness = sum(value != UNKNOWN for value in known) / max(1, len(known))
        provenance = {
            "task": "purpose_contract" if purpose else "unknown",
            "algorithm": "explicit_rule" if algorithm != UNKNOWN else "unknown",
            "publication_year": "metadata", "source": "metadata",
        }
        records.append(CoverageRecord(
            record_id="coverage:" + sha1(paper.paper_id.encode()).hexdigest()[:12],
            paper_id=paper.paper_id, task=purpose.task if purpose else UNKNOWN,
            application_domain=purpose.use_case if purpose else UNKNOWN,
            algorithm=algorithm, algorithm_family=family,
            data_type=purpose.data_type if purpose else UNKNOWN,
            missingness_conditions=missingness,
            distribution_conditions=distribution,
            evaluation_protocols=protocols, metrics=metrics,
            metric_categories=metrics,
            failure_conditions=distribution + missingness,
            publication_year=paper.year, source=paper.source,
            evidence_sentences=sentences[:8],
            evidence_sections=list(paper.sections) or ["abstract"],
            field_provenance=provenance,
            confidence_by_field={
                "algorithm": .9 if algorithm != UNKNOWN else 0.0,
                "task": .95 if purpose else 0.0, "metadata": 1.0,
            }, overall_confidence=round(.35 + .6 * completeness, 2),
        ))
    return records


def sparse_coverage_cube(records: list[CoverageRecord], dimensions: tuple[str, ...]
                         ) -> dict[tuple[str, ...], int]:
    """Build a sparse cube; list fields contribute one cell per value."""
    counts: Counter[tuple[str, ...]] = Counter()
    for record in records:
        values: list[list[str]] = []
        for dimension in dimensions:
            value = getattr(record, dimension)
            values.append(value or [UNKNOWN] if isinstance(value, list) else [str(value)])
        cells = [()]
        for options in values:
            cells = [prefix + (option,) for prefix in cells for option in options]
        counts.update(cells)
    return dict(counts)


def coverage_matrix(records: list[CoverageRecord], row: str, column: str,
                    normalized: bool = False) -> list[dict[str, Any]]:
    cube = sparse_coverage_cube(records, (row, column))
    totals = Counter(key[0] for key in cube for _ in range(cube[key]))
    return [
        {row: key[0], column: key[1], "count": count,
         "value": round(count / totals[key[0]], 3) if normalized and totals[key[0]] else count}
        for key, count in sorted(cube.items())
    ]


def detect_coverage_gaps(records: list[CoverageRecord], purpose: PurposeContract,
                         min_support: int = 3, max_unknown_ratio: float = .45
                         ) -> list[CoverageGap]:
    """Detect only purpose-relevant omissions supported by comparable neighbors."""
    if len(records) < min_support:
        return []
    unknown_ratio = sum(
        record.algorithm_family == UNKNOWN for record in records
    ) / len(records)
    if unknown_ratio > max_unknown_ratio:
        return []
    present_missingness = Counter(
        condition for record in records for condition in record.missingness_conditions
    )
    present_metrics = Counter(metric for record in records for metric in record.metric_categories)
    candidates = []
    desired: list[tuple[str, str, str]] = []
    purpose_text = f"{purpose.current_failure} {purpose.desired_improvement} {purpose.user_notes}".casefold()
    if any(token in purpose_text for token in ("missing", "mnar", "feature")):
        desired.extend([("missingness_conditions", "MNAR", "stress test"),
                        ("metric_categories", "calibration", "calibration evaluation")])
    if "cluster" in purpose.task.casefold():
        desired.extend([("metric_categories", "robustness", "multi-seed stability evaluation")])
    if any(token in purpose_text for token in ("drift", "regime")):
        desired.extend([("metric_categories", "robustness", "post-shift recovery evaluation")])
    for dimension, missing, protocol in desired:
        counts = present_missingness if dimension == "missingness_conditions" else present_metrics
        observed = counts[missing]
        neighbors = sum(counts.values()) - observed
        if observed or neighbors < min_support:
            continue
        paper_ids = sorted({record.paper_id for record in records})
        sources = {record.source for record in records}
        years = [record.publication_year for record in records if record.publication_year]
        metadata = 1 - unknown_ratio
        score = {
            "cluster_support": min(1.0, len(records) / 8),
            "neighboring_coverage": min(1.0, neighbors / 6),
            "purpose_relevance": 1.0,
            "metadata_completeness": metadata,
            "evaluation_feasibility": .9,
        }
        confidence = sum(score.values()) / len(score)
        candidates.append(CoverageGap(
            gap_id="coverage-gap:" + sha1(f"{dimension}:{missing}:{paper_ids}".encode()).hexdigest()[:12],
            gap_type="coverage", title=f"Missing {missing} coverage for {purpose.task}",
            research_cluster_id="cluster:purpose", covered_dimensions={
                dimension: sorted(counts)
            }, missing_combination={dimension: missing},
            comparison_cells=[{"value": key, "count": value} for key, value in counts.items()],
            expected_relevance=1.0, observed_count=0, neighboring_count=neighbors,
            cluster_paper_count=len(records), source_diversity=len(sources),
            year_span=max(years)-min(years)+1 if years else 0,
            omission_persistence=.8 if len(set(years)) > 1 else .4,
            metadata_completeness=metadata, practical_importance=.85,
            evaluation_feasibility=.9,
            affected_algorithms=sorted({r.algorithm for r in records if r.algorithm != UNKNOWN}),
            affected_tasks=[purpose.task], primary_missing_metric=missing if "metric" in dimension else "",
            proposed_evaluation_setting=protocol, evidence_paper_ids=paper_ids,
            evidence_sentences=[s for r in records for s in r.evidence_sentences[:1]],
            confidence=round(confidence, 2), score_components=score,
        ))
    return candidates


def coverage_gap_to_signature(gap: CoverageGap, purpose: PurposeContract) -> GapSignature:
    algorithm = gap.affected_algorithms[0] if gap.affected_algorithms else "Unspecified"
    return GapSignature(
        gap_id=gap.gap_id, title=gap.title, gap_type="structural",
        task=purpose.task, application_context=purpose.use_case, data_type=purpose.data_type,
        affected_algorithm=algorithm, affected_algorithm_family="unspecified",
        failure_type=f"missing evaluation: {next(iter(gap.missing_combination.values()))}",
        affected_component="model_selection", current_method_pattern="covered neighboring evaluations",
        observable_failure_signal="unknown boundary-condition performance",
        required_response=gap.proposed_evaluation_setting,
        unresolved_assumptions=[], constraints=[], must_preserve=purpose.must_not_degrade,
        primary_metric=purpose.primary_metric, secondary_metrics=purpose.secondary_metrics,
        available_training_information=purpose.available_training_information,
        available_inference_information=purpose.available_inference_information,
        evidence_sentences=gap.evidence_sentences, evidence_sections=["corpus coverage"],
        evidence_paper_ids=gap.evidence_paper_ids, evidence_count=len(gap.evidence_paper_ids),
        source_diversity=gap.source_diversity, explicitness_score=0,
        aggregation_score=gap.score_components["cluster_support"], structural_gap_score=gap.confidence,
        trend_score=gap.omission_persistence, practical_value_score=gap.practical_importance,
        testability_score=gap.evaluation_feasibility, confidence_score=gap.confidence,
        detection_method="coverage_matrix", structural_gap_subtype="coverage",
        coverage_gap_id=gap.gap_id, research_cluster_id=gap.research_cluster_id,
        comparison_evidence=[str(cell) for cell in gap.comparison_cells],
        missing_dimension=str(gap.missing_combination),
        metadata_completeness=gap.metadata_completeness,
        evidence_strength_components=gap.score_components,
    )
