"""Deterministic two-stage ML and discipline-native external queries."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from algorithm_library import load_algorithm_library
from app_settings import SETTINGS
from models import GapSignature, Paper, PurposeContract

MAX_QUERY_LENGTH = SETTINGS.maximum_query_length


@dataclass
class QueryAudit:
    generated_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    deduplicated_count: int = 0
    rejection_reasons: dict[str, int] = field(default_factory=dict)
    rejected_queries: list[dict[str, str]] = field(default_factory=list)


@dataclass
class AlgorithmBindingEvidence:
    algorithm: str
    family: str
    direct_name_mentions: int
    alias_mentions: int
    paper_count: int
    cluster_count: int
    source_diversity: int
    task_relevance: float
    failure_relevance: float
    binding_method: str
    confidence: float
    evidence_paper_ids: list[str]
    evidence_sentences: list[str]
    title_mentions: int = 0
    failure_context_mentions: int = 0
    task_compatible: bool = True
    binding_granularity: str = "unspecified"
    selection_reason: str = ""


@dataclass
class CrossDomainProblemSignature:
    system_condition: str
    disturbance_pattern: str
    observed_failure: str
    desired_capability: str
    memory_requirement: str
    resource_constraint: str
    feedback_requirement: str
    timescale: str
    affected_ml_slot: str
    must_preserve: list[str]
    available_signal: list[str]


@dataclass
class DomainSelection:
    domain: str
    matched_problem_roles: list[str]
    relevance_score: float
    reasons: list[str]
    missing_correspondence: list[str]
    selected: bool


RECURRENCE_SYNONYMS = [
    "recurring concept drift", "recurrent concept drift", "concept recurrence",
    "recurring regimes", "recovery after concept drift", "post-drift recovery",
    "adaptation delay", "drift recovery time", "concept history reuse",
    "previous concept reactivation", "recurring-state recognition",
    "delayed labels under drift",
]
RECOVERY_METRICS = [
    "recovery time", "adaptation delay", "post-drift regret",
    "recurrence recognition delay", "prequential accuracy",
    "worst-window accuracy", "forgetting", "memory overhead",
    "false drift alarms", "expert reactivation accuracy",
]


def expand_metric_families(purpose: PurposeContract) -> list[str]:
    metrics = [
        purpose.primary_metric, *purpose.secondary_metrics,
        *purpose.must_not_degrade,
    ]
    text = f"{purpose.current_failure} {purpose.desired_improvement}".casefold()
    if "drift" in text or "recurr" in text:
        metrics.extend(RECOVERY_METRICS)
    return list(dict.fromkeys(item for item in metrics if item))


def validate_queries(
    candidates: list[str], *, unsupported_algorithms: set[str] | None = None,
    max_length: int = MAX_QUERY_LENGTH,
) -> tuple[list[str], QueryAudit]:
    audit = QueryAudit(generated_count=len(candidates))
    accepted: list[str] = []
    seen: set[str] = set()
    unsupported_algorithms = unsupported_algorithms or set()
    for raw in candidates:
        query = re.sub(r"\s+", " ", raw).strip(" ,.-")
        reason = ""
        normalized = query.casefold()
        if len(query) > max_length:
            reason = "too long"
        elif "remove stationary distribution" in normalized:
            reason = "contradictory or malformed phrase"
        elif any(name.casefold() in normalized for name in unsupported_algorithms):
            reason = "unsupported algorithm"
        elif len(set(re.findall(r"\w+", normalized))) < 3:
            reason = "low information"
        elif normalized in seen:
            audit.deduplicated_count += 1
            reason = "duplicate"
        if reason:
            audit.rejected_count += 1
            audit.rejection_reasons[reason] = audit.rejection_reasons.get(reason, 0) + 1
            audit.rejected_queries.append({"query": query, "reason": reason})
            continue
        seen.add(normalized)
        accepted.append(query)
    audit.accepted_count = len(accepted)
    return accepted, audit


def generate_problem_queries(
    purpose: PurposeContract,
) -> tuple[list[str], QueryAudit]:
    text = f"{purpose.current_failure} {purpose.desired_improvement}".casefold()
    if "drift" in text or "recurr" in text:
        candidates = [
            f"{purpose.task} {term}" for term in RECURRENCE_SYNONYMS[:6]
        ] + [
            "stream classification recurring concepts",
            "online learning recurring contexts delayed labels",
            f"{purpose.data_type} concept history reuse",
            f"{purpose.task} worst-window accuracy after drift",
        ]
    else:
        candidates = [
            f"{purpose.task} {purpose.current_failure}",
            f"{purpose.task} {purpose.desired_improvement}",
            f"{purpose.data_type} {purpose.current_failure}",
            f"{purpose.task} failure boundary {purpose.deployment_environment}",
            f"{purpose.task} {purpose.primary_metric}",
            f"{purpose.task} deployment constraints",
        ]
    return validate_queries(candidates)


def detect_algorithm_bindings(
    papers: list[Paper], purpose: PurposeContract,
) -> list[AlgorithmBindingEvidence]:
    records = []
    recurring_tabular = (
        "recurr" in purpose.current_failure.casefold()
        and "tabular" in purpose.data_type.casefold()
    )
    compatible_names = {
        "random forest", "adaboost", "gradient boosted trees",
        "decision tree", "mixture of experts", "continual learning systems",
    }
    for algorithm in load_algorithm_library().values():
        direct_ids, alias_ids, sentences = set(), set(), []
        title_ids, context_ids = set(), set()
        for paper in papers:
            text = f"{paper.title}. {paper.abstract}"
            if re.search(rf"\b{re.escape(algorithm.name)}\b", text, re.I):
                direct_ids.add(paper.paper_id)
                sentences.append(text[:300])
                if re.search(
                    rf"\b{re.escape(algorithm.name)}\b", paper.title, re.I
                ):
                    title_ids.add(paper.paper_id)
                for sentence in re.split(r"(?<=[.!?])\s+", text):
                    if (
                        re.search(rf"\b{re.escape(algorithm.name)}\b", sentence, re.I)
                        and any(term in sentence.casefold() for term in (
                            "recurr", "drift", "recovery", "missing",
                            "cluster", "failure", "degrad",
                        ))
                    ):
                        context_ids.add(paper.paper_id)
            elif any(re.search(rf"\b{re.escape(alias)}\b", text, re.I)
                     for alias in algorithm.aliases):
                alias_ids.add(paper.paper_id)
                sentences.append(text[:300])
        ids = direct_ids | alias_ids
        if not ids:
            continue
        relevant = [
            paper for paper in papers if paper.paper_id in ids
            and any(term in f"{paper.title} {paper.abstract}".casefold()
                    for term in purpose.current_failure.casefold().split())
        ]
        source_count = len({
            paper.source for paper in papers if paper.paper_id in ids
        })
        compatible = not recurring_tabular or algorithm.name.casefold() in compatible_names
        confidence = min(.98, (
            .12 + .10 * len(direct_ids) + .05 * len(alias_ids)
            + .12 * len(title_ids) + .12 * len(context_ids)
            + .08 * source_count + (.12 if compatible else -.3)
        ))
        strong_exact = (
            confidence >= .65 and len(context_ids) >= 2
            and source_count >= 2 and compatible
        )
        granularity = (
            "exact algorithm" if strong_exact
            else "algorithm family" if confidence >= .4 and compatible
            else "broad method class" if confidence >= .25
            else "unspecified"
        )
        reason = (
            f"{len(ids)} mentioning papers; {len(context_ids)} target-failure "
            f"context mentions; {source_count} sources; "
            f"task compatible={compatible}; granularity={granularity}"
        )
        records.append(AlgorithmBindingEvidence(
            algorithm.name, algorithm.family, len(direct_ids), len(alias_ids),
            len(ids), len(ids), source_count, len(ids) / max(1, len(papers)),
            len(relevant) / max(1, len(ids)),
            "explicit paper mention" if direct_ids else "metadata classification",
            round(max(0.0, confidence), 3), sorted(ids), sentences[:5],
            len(title_ids), len(context_ids), compatible, granularity, reason,
        ))
    return sorted(
        records, key=lambda item: (item.confidence, item.paper_count), reverse=True
    )


def generate_focused_algorithm_queries(
    purpose: PurposeContract, bindings: list[AlgorithmBindingEvidence],
    confidence_threshold: float = .45,
) -> tuple[list[str], QueryAudit]:
    supported = [
        item for item in bindings
        if item.confidence >= confidence_threshold
        and item.task_compatible
        and item.binding_granularity in {"exact algorithm", "algorithm family"}
    ][:4]
    candidates = []
    for item in supported:
        subject = (
            item.algorithm if item.binding_granularity == "exact algorithm"
            else item.family.replace("_", " ")
        )
        candidates.extend([
            f"{subject} recurring concept drift recovery",
            f"{subject} concept recurrence adaptation delay",
        ])
    if not supported:
        candidates = [
            "streaming ensemble recurring concepts recovery",
            "online learning model family recurring regimes",
        ]
    return validate_queries(candidates)


def generate_ml_queries(
    purpose: PurposeContract, algorithm: str = "",
) -> list[str]:
    """Compatibility API; never binds an unsupported algorithm by default."""
    broad, _ = generate_problem_queries(purpose)
    if not algorithm:
        return broad
    allowed = {
        record.name for record in load_algorithm_library().values()
        if record.family in purpose.allowed_algorithm_families
    }
    if algorithm not in allowed:
        return broad
    focused, _ = validate_queries([
        f"{algorithm} {purpose.current_failure}",
        f"{algorithm} {purpose.desired_improvement}",
    ])
    return broad + focused


def normalize_cross_domain_problem(
    gap: GapSignature,
) -> CrossDomainProblemSignature:
    recurring = "recurr" in f"{gap.failure_type} {gap.required_response}".casefold()
    return CrossDomainProblemSignature(
        system_condition="recurring regime changes" if recurring else gap.failure_type,
        disturbance_pattern=(
            "previously observed regimes return after intervals"
            if recurring else gap.failure_type
        ),
        observed_failure=gap.observable_failure_signal,
        desired_capability=gap.required_response,
        memory_requirement=(
            "bounded long-term memory" if recurring else "retain useful prior state"
        ),
        resource_constraint=", ".join(gap.constraints) or "limited compute and memory",
        feedback_requirement="adapt without unstable oscillation",
        timescale=gap.timescale or "after each disturbance",
        affected_ml_slot=gap.affected_component,
        must_preserve=gap.must_preserve,
        available_signal=gap.available_inference_information,
    )


DOMAIN_PROFILES = {
    "immunology": {
        "roles": ["memory", "recurrence", "recovery"],
        "queries": [
            "immune memory reactivation recurrent exposure",
            "rapid secondary immune response repeated antigen challenge",
            "memory cell recall response latency",
            "immune repertoire retention recurrent threats",
        ],
    },
    "ecology": {
        "roles": ["memory", "recurrence", "recovery"],
        "queries": [
            "ecological memory recovery after recurrent disturbance",
            "community resilience repeated regime shifts",
            "legacy effects ecosystem recovery",
            "niche reoccupation repeated environmental change",
        ],
    },
    "control_theory": {
        "roles": ["switching", "feedback", "stability"],
        "queries": [
            "multiple model adaptive control recurring operating modes",
            "controller reactivation recurring mode switches",
            "adaptive control transient recovery repeated disturbances",
            "mode estimation switching systems stability",
        ],
    },
    "neuroscience": {
        "roles": ["memory", "recognition", "adaptation"],
        "queries": [
            "context memory reinstatement repeated environments",
            "pattern completion recurring contexts",
            "memory guided rapid adaptation recurring conditions",
        ],
    },
    "dynamical_systems": {
        "roles": ["switching", "recovery", "memory"],
        "queries": [
            "hysteresis recurrent regime transitions",
            "relaxation time repeated perturbations",
            "metastable state recurrence dynamics",
            "state dependent response repeated forcing",
        ],
    },
    "physics": {
        "roles": ["switching", "recovery"],
        "queries": [
            "hysteresis recurrent transitions",
            "relaxation time repeated perturbations",
            "metastable state recurrent transitions",
        ],
    },
    "biology": {
        "roles": ["memory", "adaptation"],
        "queries": [
            "biological memory recurrent environmental exposure",
            "rapid adaptive response repeated stress",
            "cellular memory response latency",
        ],
    },
    "complex_systems": {
        "roles": ["switching", "stability"],
        "queries": [
            "complex systems recurrent regime transitions",
            "adaptive resilience repeated perturbations",
            "path dependence recovery dynamics",
        ],
    },
    "operations_research": {
        "roles": ["resource"],
        "queries": ["adaptive allocation recurring demand regimes"],
    },
    "mechanism_design": {
        "roles": ["incentives"],
        "queries": ["adaptive incentives repeated environment changes"],
    },
}


def select_external_domains(
    signature: CrossDomainProblemSignature, maximum: int = 5,
) -> list[DomainSelection]:
    recurring = "recurr" in (
        signature.system_condition + signature.disturbance_pattern
    ).casefold()
    preferred = {
        "immunology", "ecology", "control_theory", "neuroscience",
        "dynamical_systems",
    } if recurring else {"control_theory", "complex_systems", "biology"}
    selections = []
    for domain, profile in DOMAIN_PROFILES.items():
        score = .35 + (.5 if domain in preferred else 0)
        reasons = ["maps recurring disturbance to native terminology"] if recurring else [
            "maps adaptation and stability roles"
        ]
        selections.append(DomainSelection(
            domain, list(profile["roles"]), round(score, 2), reasons,
            [] if domain in preferred else ["weaker direct recurrence correspondence"],
            False,
        ))
    selections.sort(key=lambda item: item.relevance_score, reverse=True)
    for item in selections[:maximum]:
        item.selected = True
    return selections


def generate_external_queries(
    gap: GapSignature, domains: list[str] | None = None,
) -> dict[str, list[str]]:
    signature = normalize_cross_domain_problem(gap)
    selected = domains or [
        item.domain for item in select_external_domains(signature) if item.selected
    ]
    output = {}
    for domain in selected:
        queries, _ = validate_queries(list(DOMAIN_PROFILES[domain]["queries"]))
        output[domain] = queries[:5]
    return output
