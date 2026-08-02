"""Evidence-first research-axis and direction-candidate generation."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, replace
from hashlib import sha1
import re
from typing import Sequence

from algorithm_library import load_algorithm_library
from gap_consolidation import CanonicalGapFamily, promoted_gap_validation_reasons
from models import GapSignature, Paper, PurposeContract


@dataclass(frozen=True)
class ResearchProblemAxis:
    axis_id: str
    user_task: str
    target_failure: str
    lifecycle_stage: str
    candidate_affected_component: str
    candidate_metric: str
    required_capability: str
    search_vocabulary: tuple[str, ...]
    excluded_neighboring_problems: tuple[str, ...]
    evidence_threshold: int = 1


@dataclass(frozen=True)
class AlgorithmBindingResult:
    bound_family: str
    binding_granularity: str
    confidence: float
    supporting_paper_ids: tuple[str, ...]
    supporting_evidence_excerpts: tuple[str, ...]
    rejected_alternatives: tuple[str, ...]
    uncertainty: str


@dataclass(frozen=True)
class DirectionEvidencePath:
    paper_id: str
    evidence_sentence_id: str
    gap_id: str
    algorithm_family: str
    metric: str
    direction_candidate_id: str


@dataclass
class DirectionCandidate:
    candidate_direction_id: str
    purpose_axis_id: str
    title: str
    complete_problem_statement: str
    task: str
    condition: str
    failure_topology: str
    lifecycle_stage: str
    affected_algorithm_family: str
    binding_granularity: str
    algorithm_binding_confidence: float
    affected_component: str
    primary_metric: str
    metric_evidence: list[str]
    evidence_paper_ids: list[str]
    direct_evidence_sentence_ids: list[str]
    contextual_paper_ids: list[str]
    known_solutions: list[str]
    unresolved_remainder: str
    practical_value: float
    testability: float
    evidence_strength: float
    source_diversity: int
    coherence_score: float
    uncertainties: list[str]
    eligibility_status: str
    rejection_reasons: list[str]
    evidence_paths: list[DirectionEvidencePath] = field(default_factory=list)
    extraction_origin: str = ""
    original_title: str = ""


@dataclass
class DirectionGenerationResult:
    axes: list[ResearchProblemAxis]
    candidates: list[DirectionCandidate]
    recommended_families: list[CanonicalGapFamily]
    exploratory_families: list[CanonicalGapFamily]
    repaired_gaps: list[GapSignature]
    grouped_rejections: dict[str, int]
    diagnostics: dict[str, object]


TASK_FAMILY_REGISTRY = {
    "online": ("online ensemble", "streaming tree", "incremental classifier", "replay-based online learner"),
    "stream": ("online ensemble", "streaming tree", "incremental classifier"),
    "cluster": ("adaptive clustering method", "incremental clustering", "density-based stream clustering", "prototype-based adaptive clustering"),
    "missing": ("missingness-aware predictor", "robust tabular learner", "latent-variable imputation model"),
    "classification": ("incremental classifier", "robust tabular learner"),
}


def _clean(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _human(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("_", " ")).strip()


def generate_problem_axes(purpose: PurposeContract, maximum: int = 8) -> list[ResearchProblemAxis]:
    """Decompose a purpose into bounded search hypotheses, never evidence."""
    text = _clean(f"{purpose.task} {purpose.current_failure} {purpose.desired_improvement}")
    if "recurr" in text or "concept drift" in text:
        specs = [
            ("detection", "recurrence detection", "detection", "recurrence detection delay", "recognize returning regimes", ("recurrence detection", "concept recurrence recognition")),
            ("selection", "incorrect historical expert selection", "expert_selection", "expert reactivation accuracy", "select the correct historical specialist", ("historical expert selection", "recurring concept drift")),
            ("recovery", "slow post-recurrence recovery", "aggregation", purpose.primary_metric, "shorten recovery after recurrence", ("post drift recovery", "recurring regime adaptation")),
            ("false_match", "false recurrence matches", "routing", "false recurrence rate", "reject spurious historical matches", ("false recurrence detection", "concept matching")),
            ("memory", "forgetting useful prior regimes", "memory", "memory retention", "retain useful prior state", ("concept history reuse", "bounded replay memory")),
            ("archive", "unbounded historical model archive", "component_birth_death", "memory use", "bound archive growth", ("bounded model archive", "concept drift memory")),
            ("plasticity", "stability plasticity imbalance", "update_rule", "stable-regime accuracy", "adapt without destructive forgetting", ("stability plasticity", "online continual learning")),
        ]
    elif "missing" in text:
        specs = [
            ("detection", "training inference feature-availability shift", "feature_acquisition", purpose.primary_metric, "detect missingness-pattern shift", ("missingness shift detection", "feature availability")),
            ("routing", "incorrect routing with unavailable features", "routing", purpose.primary_metric, "route using observed features", ("missingness aware routing", "missing features prediction")),
            ("imputation", "biased latent feature reconstruction", "state_estimation", "imputation error", "estimate unavailable features without leakage", ("missingness aware imputation", "MNAR prediction")),
            ("robustness", "prediction degradation under missing features", "aggregation", purpose.primary_metric, "preserve predictive performance", ("missing feature robustness", "tabular missingness")),
            ("calibration", "confidence error under missingness shift", "uncertainty_estimate", "calibration error", "calibrate under changing availability", ("missingness calibration", "selective prediction")),
        ]
    elif "cluster" in text or "density" in text:
        specs = [
            ("birth", "delayed cluster birth recognition", "component_birth_death", purpose.primary_metric, "create components when supported", ("cluster birth detection", "evolving data streams")),
            ("death", "stale cluster retention", "component_birth_death", "retirement delay", "retire obsolete components", ("cluster death", "component retirement")),
            ("density", "heterogeneous density assignment failure", "assignment", "cluster assignment error", "adapt density-sensitive assignment", ("varying density stream clustering", "adaptive density clustering")),
            ("merge_split", "incorrect component merge or split", "model_selection", "structural detection error", "control merge and split decisions", ("cluster split merge", "dynamic clustering")),
            ("memory", "unbounded prototype growth", "memory", "memory use", "maintain a bounded prototype set", ("bounded prototype memory", "stream clustering")),
        ]
    else:
        specs = [
            ("detection", purpose.current_failure, "detection", purpose.primary_metric, "detect the failure condition", (purpose.current_failure, purpose.task)),
            ("adaptation", purpose.current_failure, "update_rule", purpose.primary_metric, purpose.desired_improvement, (purpose.current_failure, purpose.desired_improvement)),
            ("selection", purpose.current_failure, "model_selection", purpose.primary_metric, "select a compatible method", (purpose.task, "model selection")),
        ]
    axes = []
    for label, failure, component, metric, capability, vocabulary in specs[:maximum]:
        axes.append(ResearchProblemAxis(
            axis_id=f"axis:{sha1(f'{purpose.purpose_id}:{label}'.encode()).hexdigest()[:12]}",
            user_task=purpose.task, target_failure=failure,
            lifecycle_stage=label, candidate_affected_component=component,
            candidate_metric=metric, required_capability=capability,
            search_vocabulary=tuple(vocabulary),
            excluded_neighboring_problems=("unrelated task", "different data modality"),
        ))
    return axes


def axis_queries(axis: ResearchProblemAxis) -> list[str]:
    terms = " ".join(axis.search_vocabulary[:2])
    return [
        f"{axis.user_task} {terms} {axis.candidate_metric}",
        f"{terms} {axis.candidate_affected_component.replace('_', ' ')}",
    ]


def _task_registry_candidates(purpose: PurposeContract) -> tuple[str, ...]:
    text = _clean(f"{purpose.task} {purpose.current_failure}")
    output = []
    for cue, families in TASK_FAMILY_REGISTRY.items():
        if cue in text:
            output.extend(families)
    return tuple(dict.fromkeys(output or ("adaptive predictor",)))


def bind_algorithm_family(
    gap: GapSignature, papers: Sequence[Paper], purpose: PurposeContract,
) -> AlgorithmBindingResult:
    """One-pass contextual exact→family→method-class binding repair."""
    by_id = {paper.paper_id: paper for paper in papers}
    evidence_papers = [by_id[item] for item in gap.evidence_paper_ids if item in by_id]
    evidence_text = " ".join(
        f"{paper.title} {paper.abstract}" for paper in evidence_papers
    ).casefold()
    excerpts = tuple(gap.evidence_sentences[:4])
    library = load_algorithm_library()
    task_text = _clean(purpose.task)
    def task_compatible(record) -> bool:
        record_tasks = _clean(" ".join(record.tasks))
        if any(token in record_tasks for token in task_text.split()):
            return True
        return (
            ("online" in task_text and any(term in record_tasks for term in ("online", "continual")))
            or ("classif" in task_text and any(term in record_tasks for term in ("classification", "tabular learning")))
            or ("cluster" in task_text and "clustering" in record_tasks)
        )
    current_algorithm = _clean(gap.affected_algorithm)
    current_family = _clean(gap.affected_algorithm_family)
    if current_algorithm not in {"", "unknown", "unspecified", "unbound"}:
        record = next((item for item in library.values() if _clean(item.name) == current_algorithm), None)
        if record and task_compatible(record):
            return AlgorithmBindingResult(record.family, "exact algorithm", min(.95, .7 + .05 * len(evidence_papers)), tuple(p.paper_id for p in evidence_papers), excerpts, (), "")
        if record:
            return AlgorithmBindingResult("UNBOUND", "unbound", 0.0, (), excerpts, (record.family,), "Named algorithm is incompatible with the user task.")
    if current_family not in {"", "unknown", "unspecified", "unbound"}:
        compatible_family = any(
            _clean(record.family) == current_family and task_compatible(record)
            for record in library.values()
        )
        if compatible_family:
            return AlgorithmBindingResult(gap.affected_algorithm_family, "algorithm family", min(.9, .58 + .06 * len(evidence_papers)), tuple(p.paper_id for p in evidence_papers), excerpts, (), "Exact algorithm is not established.")
        return AlgorithmBindingResult("UNBOUND", "unbound", 0.0, (), excerpts, (gap.affected_algorithm_family,), "Algorithm family is incompatible with the user task.")

    if "online ensemble" in evidence_text and ("online" in task_text or "stream" in task_text):
        return AlgorithmBindingResult(
            "ensemble", "algorithm family", .68,
            tuple(p.paper_id for p in evidence_papers), excerpts, (),
            "Family phrase is supported; exact ensemble implementation is unknown.",
        )

    scored = []
    task_text = _clean(purpose.task)
    for record in library.values():
        title_hits = sum(_clean(name) in _clean(" ".join(p.title for p in evidence_papers)) for name in (record.name, *record.aliases))
        abstract_hits = sum(_clean(name) in evidence_text for name in (record.name, *record.aliases))
        task_ok = task_compatible(record)
        failure_hit = any(_clean(item) in _clean(gap.failure_type) or _clean(item) in evidence_text for item in record.known_failure_conditions)
        score = .35 * bool(title_hits) + .2 * bool(abstract_hits) + .2 * task_ok + .15 * failure_hit + .1 * min(1, len(evidence_papers) / 2)
        if not task_ok:
            score -= .45
        if score:
            scored.append((score, record))
    scored.sort(key=lambda item: (-item[0], item[1].family, item[1].name))
    if scored and scored[0][0] >= .55:
        best = scored[0]
        rejected = tuple(item[1].family for item in scored[1:4])
        return AlgorithmBindingResult(best[1].family, "algorithm family", round(best[0], 3), tuple(p.paper_id for p in evidence_papers), excerpts, rejected, "Family inferred contextually; exact algorithm is unknown.")

    candidates = _task_registry_candidates(purpose)
    failure_terms = set(_clean(gap.failure_type).split())
    evidence_terms = set(_clean(evidence_text).split())
    task_supported = bool(set(_clean(purpose.task).split()) & evidence_terms)
    failure_supported = bool(failure_terms & evidence_terms)
    if evidence_papers and task_supported and failure_supported:
        method_class = candidates[0]
        return AlgorithmBindingResult(method_class, "method class", .52, tuple(p.paper_id for p in evidence_papers), excerpts, tuple(candidates[1:]), "Broad method-class binding; exact family remains uncertain.")
    return AlgorithmBindingResult("UNBOUND", "unbound", 0.0, (), excerpts, candidates, "No evidence-supported task-compatible family was found.")


def generate_direction_title(gap: GapSignature, axis: ResearchProblemAxis) -> str:
    failure = _human(gap.failure_type or axis.target_failure)
    component = _human(gap.affected_component or axis.candidate_affected_component)
    metric = _human(gap.primary_metric or axis.candidate_metric)
    title = f"Reducing {metric} from {failure} through {component}"
    words = title.split()
    return " ".join(words[:18]).rstrip(" ,:;-.")


def generate_problem_statement(
    gap: GapSignature, axis: ResearchProblemAxis, family: str,
) -> str:
    return (
        f"Under {_human(gap.failure_type or axis.target_failure)} in "
        f"{_human(gap.task)}, the {_human(family)} family can fail at "
        f"{_human(gap.affected_component or axis.candidate_affected_component)}, "
        f"worsening {_human(gap.primary_metric or axis.candidate_metric)}; "
        f"the unresolved need is {_human(gap.required_response or axis.required_capability)}."
    )


def _best_axis(gap: GapSignature, axes: Sequence[ResearchProblemAxis]) -> ResearchProblemAxis:
    text = set(_clean(f"{gap.failure_type} {gap.affected_component} {gap.required_response} {gap.primary_metric}").split())
    return max(axes, key=lambda axis: (
        len(text & set(_clean(" ".join((axis.target_failure, axis.candidate_affected_component, axis.candidate_metric, *axis.search_vocabulary))).split())),
        axis.axis_id,
    ))


def _compatible_paper(paper: Paper, gap: GapSignature, purpose: PurposeContract) -> bool:
    text = set(_clean(f"{paper.title} {paper.abstract}").split())
    task = set(_clean(purpose.task).split())
    task_text = _clean(purpose.task)
    aliases = set()
    if "online" in task_text or "stream" in task_text:
        aliases.update(("stream", "streaming", "online", "drift"))
    if "classif" in task_text:
        aliases.update(("classification", "classifier", "prediction", "tabular"))
    if "cluster" in task_text:
        aliases.update(("cluster", "clustering", "centroid", "density"))
    failure = set(_clean(gap.failure_type).split())
    algorithm = set(_clean(f"{gap.affected_algorithm} {gap.affected_algorithm_family}").split())
    return bool(text & (task | aliases)) and bool(text & (failure | algorithm))


def generate_direction_candidates(
    purpose: PurposeContract, families: Sequence[CanonicalGapFamily],
    gaps: Sequence[GapSignature], papers: Sequence[Paper],
) -> DirectionGenerationResult:
    axes = generate_problem_axes(purpose)
    by_gap = {gap.gap_id: gap for gap in gaps}
    by_paper = {paper.paper_id: paper for paper in papers}
    candidates, repaired_gaps = [], []
    recommended, exploratory = [], []
    repair_counts = Counter()
    rejection_counts = Counter()
    origins = Counter()
    for family in families:
        gap = by_gap.get(family.representative_gap_id)
        if not gap:
            continue
        origins[gap.structural_gap_subtype or gap.gap_type] += 1
        axis = _best_axis(gap, axes)
        binding = bind_algorithm_family(gap, papers, purpose)
        repaired = gap
        original_title = gap.title
        structured_missing = [name for name, value in {
            "task": gap.task, "failure condition": gap.failure_type,
            "affected component": gap.affected_component,
            "primary metric": gap.primary_metric, "required response": gap.required_response,
        }.items() if not str(value).strip()]
        title_invalid = "incomplete title" in promoted_gap_validation_reasons(gap)
        if binding.binding_granularity != "unbound" and _clean(gap.affected_algorithm_family) in {"", "unknown", "unspecified", "unbound"}:
            repaired = replace(repaired, affected_algorithm_family=binding.bound_family)
            repair_counts["family_bindings"] += 1
        if title_invalid and not structured_missing:
            repaired = replace(repaired, title=generate_direction_title(repaired, axis))
            repair_counts["titles"] += 1
        problem = generate_problem_statement(repaired, axis, binding.bound_family)
        direct_records = []
        direct_sentence_ids = []
        for member in family.member_gaps or [gap]:
            for index, (paper_id, sentence, section) in enumerate(zip(
                member.evidence_paper_ids, member.evidence_sentences,
                member.evidence_sections,
            )):
                paper = by_paper.get(paper_id)
                if section != "purpose_contract" and paper and _compatible_paper(paper, repaired, purpose):
                    direct_records.append((paper_id, sentence))
                    direct_sentence_ids.append(f"{member.gap_id}:sentence:{index}")
        evidence_ids = sorted({item[0] for item in direct_records})
        contextual_ids = sorted({
            item for item in family.supporting_paper_ids
            if item in by_paper and item not in evidence_ids
            and _compatible_paper(by_paper[item], repaired, purpose)
        })
        coherence = round(len(evidence_ids) / max(1, len({item for item in family.supporting_paper_ids if item in by_paper})), 3)
        metric_evidence = [sentence for _, sentence in direct_records if set(_clean(repaired.primary_metric).split()) & set(_clean(sentence).split())]
        status = "RECOMMENDED_ELIGIBLE"
        reasons = []
        if structured_missing:
            status, reasons = "MALFORMED", [f"missing {item}" for item in structured_missing]
        elif binding.binding_granularity == "unbound":
            status, reasons = "UNBOUND", [binding.uncertainty]
        elif not repaired.primary_metric or _clean(repaired.primary_metric) in {"performance", "quality", "unknown"}:
            status, reasons = "UNSUPPORTED_METRIC", ["metric is absent or generic"]
        elif not evidence_ids:
            status, reasons = "INSUFFICIENT_EVIDENCE", ["no connected direct paper evidence path"]
        elif coherence < .4:
            status, reasons = "INCOHERENT_EVIDENCE", ["fewer than 40% of family papers pass hard task/failure compatibility"]
        elif family.promotion_status != "PROMOTED" or len(evidence_ids) < 2 or binding.confidence < .6:
            status = "EXPLORATORY_ELIGIBLE"
            reasons = list(family.rejection_reasons) or ["limited direct evidence or binding confidence"]
        candidate_id = f"direction-candidate:{sha1(f'{axis.axis_id}:{family.family_id}'.encode()).hexdigest()[:12]}"
        paths = [DirectionEvidencePath(pid, sid, repaired.gap_id, binding.bound_family, repaired.primary_metric, candidate_id) for (pid, _), sid in zip(direct_records, direct_sentence_ids)]
        candidate = DirectionCandidate(
            candidate_id, axis.axis_id, generate_direction_title(repaired, axis),
            problem, repaired.task, repaired.failure_type,
            family.field_consensus.get("failure_topology", repaired.failure_type),
            axis.lifecycle_stage, binding.bound_family,
            binding.binding_granularity, binding.confidence,
            repaired.affected_component, repaired.primary_metric,
            metric_evidence, evidence_ids, direct_sentence_ids, contextual_ids,
            family.known_mitigations, family.unresolved_remainder,
            repaired.practical_value_score, repaired.testability_score,
            repaired.confidence_score, len({by_paper[item].source for item in evidence_ids}),
            coherence, [item for item in (binding.uncertainty, *family.rejection_reasons) if item],
            status, reasons, paths, gap.detection_method or gap.structural_gap_subtype or gap.gap_type,
            original_title,
        )
        candidates.append(candidate)
        if status in {"RECOMMENDED_ELIGIBLE", "EXPLORATORY_ELIGIBLE"}:
            repaired = replace(repaired, title=candidate.title)
            repaired_gaps.append(repaired)
            repaired_family = replace(
                family, representative_gap_id=repaired.gap_id,
                representative_title=candidate.title,
                plain_language_statement=candidate.complete_problem_statement,
                algorithm_family_consensus=binding.bound_family,
                binding_granularity=binding.binding_granularity,
                promotion_status="PROMOTED" if status == "RECOMMENDED_ELIGIBLE" else "SINGLE_PAPER",
                rejection_reasons=[] if status == "RECOMMENDED_ELIGIBLE" else candidate.rejection_reasons,
                supporting_paper_ids=[*evidence_ids, *contextual_ids],
                member_gaps=[repaired, *[item for item in family.member_gaps if item.gap_id != repaired.gap_id]],
            )
            (recommended if status == "RECOMMENDED_ELIGIBLE" else exploratory).append(repaired_family)
        else:
            rejection_counts[status] += 1
    return DirectionGenerationResult(
        axes, candidates, recommended, exploratory, repaired_gaps,
        dict(rejection_counts), {
            "origin_counts": dict(origins), "repaired_titles": repair_counts["titles"],
            "repaired_family_bindings": repair_counts["family_bindings"],
            "connected_evidence_paths": sum(len(item.evidence_paths) for item in candidates),
            "axis_queries": {axis.axis_id: axis_queries(axis) for axis in axes},
        },
    )
