"""Explicit, aggregated, and structural ML/DL gap extraction."""

from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha1
import re

from algorithm_library import load_algorithm_library
from models import GapSignature, Paper, PurposeContract
from text_processing import section_weight, split_sentences

GAP_CUES = re.compile(
    r"\b(however|nevertheless|remains? challenging|fails? when|limited to|limitation|"
    r"does not address|future work|unexplored|underexplored|degrades? under|assumes? that|"
    r"cannot handle|open problem|bottleneck|poor performance|sensitive to|struggles? with|"
    r"lacks? robustness|not evaluated|requires? access|depends? on|unresolved)\b", re.I
)
FAILURES = {
    "concept drift": ("recurring concept drift", "performance decay after regime recurrence", "reactivate prior specialists"),
    "recurr": ("recurring concept drift", "performance decay after regime recurrence", "reactivate prior specialists"),
    "distribution shift": ("distribution shift", "out-of-distribution metric degradation", "adapt while preserving in-distribution performance"),
    "missing": ("missingness shift", "performance varies with feature availability", "route or estimate using available features"),
    "initialization": ("initialization sensitivity", "variance across restarts", "stabilize assignments and diversify components"),
    "regime": ("regime change", "persistent residual or error jump", "estimate regime and switch response"),
    "calibration": ("miscalibration", "calibration error rises", "correct confidence using observable outcomes"),
    "redundan": ("component redundancy", "high component overlap", "specialize or retire redundant components"),
    "forget": ("catastrophic forgetting", "past-task accuracy decay", "retain and reactivate bounded memory"),
}


def _algorithm_for(text: str, purpose: PurposeContract | None) -> tuple[str, str, str]:
    library = load_algorithm_library()
    candidates = sorted(library.values(), key=lambda item: len(item.name), reverse=True)
    for algorithm in candidates:
        names = [algorithm.name, *algorithm.aliases]
        if any(re.search(rf"\b{re.escape(name)}\b", text, re.I) for name in names):
            slot = next((s for s in algorithm.modifiable_slots if s in text.casefold()),
                        algorithm.modifiable_slots[0])
            return algorithm.name, algorithm.family, slot
    if purpose and purpose.allowed_algorithm_families:
        family = purpose.allowed_algorithm_families[0]
        matched = next((record for record in library.values() if record.family == family), None)
        if matched:
            return matched.name, matched.family, matched.modifiable_slots[0]
    return "Unspecified", "unspecified", "update_rule"


def _failure(text: str, purpose: PurposeContract | None) -> tuple[str, str, str]:
    lowered = text.casefold()
    for cue, values in FAILURES.items():
        if cue in lowered:
            return values
    failure = purpose.current_failure if purpose else "unresolved failure"
    return failure, f"measurable degradation under {failure}", f"reduce {failure}"


def mine_explicit_gaps(papers: list[Paper], purpose: PurposeContract | None = None) -> list[GapSignature]:
    gaps = []
    for paper in papers:
        sources = paper.sections or {"abstract": paper.abstract}
        for section, body in sources.items():
            for sentence in split_sentences(body):
                if not GAP_CUES.search(sentence):
                    continue
                algorithm, family, slot = _algorithm_for(f"{paper.title} {sentence}", purpose)
                failure, signal, response = _failure(sentence, purpose)
                scope_weight = section_weight(section)
                identifier = sha1(f"{paper.paper_id}:{sentence}".encode()).hexdigest()[:12]
                gaps.append(GapSignature(
                    gap_id=f"gap:{identifier}", title=f"{algorithm}: {failure}",
                    gap_type="explicit", task=purpose.task if purpose else "machine learning",
                    application_context=purpose.use_case if purpose else "reported study",
                    data_type=purpose.data_type if purpose else "unspecified",
                    affected_algorithm=algorithm, affected_algorithm_family=family,
                    failure_type=failure, affected_component=slot,
                    current_method_pattern=algorithm, observable_failure_signal=signal,
                    required_response=response,
                    unresolved_assumptions=[failure], constraints=[],
                    must_preserve=purpose.must_not_degrade if purpose else [],
                    primary_metric=purpose.primary_metric if purpose else "task metric",
                    secondary_metrics=purpose.secondary_metrics if purpose else [],
                    available_training_information=purpose.available_training_information if purpose else ["training data"],
                    available_inference_information=purpose.available_inference_information if purpose else ["input features"],
                    evidence_sentences=[sentence], evidence_sections=[section],
                    evidence_paper_ids=[paper.paper_id], evidence_count=1,
                    source_diversity=1, explicitness_score=scope_weight,
                    aggregation_score=0.0, structural_gap_score=.4,
                    trend_score=.5, practical_value_score=.7,
                    testability_score=.75, confidence_score=round(.45 + .45 * scope_weight, 3),
                    timescale="online" if "drift" in failure else "per evaluation",
                ))
    return gaps


def aggregate_gaps(gaps: list[GapSignature], minimum_evidence: int = 2) -> list[GapSignature]:
    groups: dict[tuple[str, str, str], list[GapSignature]] = defaultdict(list)
    for gap in gaps:
        groups[(gap.affected_algorithm_family, gap.failure_type, gap.affected_component)].append(gap)
    aggregated = []
    for (_, _, _), items in groups.items():
        paper_ids = sorted({pid for item in items for pid in item.evidence_paper_ids})
        if len(paper_ids) < minimum_evidence:
            continue
        base = items[0]
        aggregated.append(GapSignature(**{
            **base.__dict__,
            "gap_id": f"agg:{sha1(':'.join(paper_ids).encode()).hexdigest()[:12]}",
            "gap_type": "aggregated",
            "title": f"Repeated evidence: {base.title}",
            "evidence_sentences": [s for item in items for s in item.evidence_sentences],
            "evidence_sections": [s for item in items for s in item.evidence_sections],
            "evidence_paper_ids": paper_ids,
            "evidence_count": len(paper_ids),
            "source_diversity": len({pid.split(":")[0] for pid in paper_ids}),
            "aggregation_score": min(1.0, .35 + .15 * len(paper_ids)),
            "confidence_score": min(.95, base.confidence_score + .1 * (len(paper_ids) - 1)),
        }))
    return aggregated


def corpus_summary(papers: list[Paper], gaps: list[GapSignature]) -> dict[str, object]:
    return {
        "paper_count": len(papers),
        "papers_by_year": dict(Counter(p.year for p in papers)),
        "failure_frequency": dict(Counter(g.failure_type for g in gaps)),
        "algorithm_family_concentration": dict(Counter(g.affected_algorithm_family for g in gaps)),
        "metric_coverage": sorted({g.primary_metric for g in gaps}),
        "source_diversity": len({p.source for p in papers}),
    }


def mine_gaps(papers: list[Paper], purpose: PurposeContract | None = None) -> list[GapSignature]:
    explicit = mine_explicit_gaps(papers, purpose)
    return explicit + aggregate_gaps(explicit)
