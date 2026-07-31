"""Gap-oriented ML queries and structure-driven external queries."""

from __future__ import annotations

from models import GapSignature, PurposeContract


def generate_ml_queries(purpose: PurposeContract, algorithm: str = "") -> list[str]:
    subject = algorithm or purpose.task
    failure = purpose.current_failure or "unresolved challenge"
    return list(dict.fromkeys([
        f"{purpose.task} limitations {failure}",
        f"{subject} failure under {failure}",
        f"{purpose.task} remains challenging {purpose.primary_metric}",
        f"{subject} assumption violation",
        f"{purpose.task} future work robustness",
        f"{subject} deployment limitations {purpose.data_type}",
        f"{purpose.task} inference-time missing information",
    ]))


DOMAIN_VOCABULARY = {
    "biology": "adaptive stability under changing environments",
    "ecology": "recovery competition niches under resource limits",
    "immunology": "memory reactivation after recurring threats",
    "neuroscience": "predictive error feedback memory",
    "physics": "regime transition critical threshold",
    "control_theory": "stable feedback observability under perturbation",
    "mechanism_design": "incentive alignment reliable aggregation",
    "operations_research": "constrained resource allocation",
}


def generate_external_queries(gap: GapSignature, domains: list[str] | None = None) -> dict[str, list[str]]:
    domains = domains or list(DOMAIN_VOCABULARY)
    output: dict[str, list[str]] = {}
    structural = " ".join(filter(None, [
        gap.failure_type, gap.observable_failure_signal, gap.required_response,
        gap.affected_component, gap.timescale, " ".join(gap.constraints),
    ]))
    for domain in domains:
        vocabulary = DOMAIN_VOCABULARY.get(domain, "adaptive mechanism under constraints")
        output[domain] = [
            f"{domain} {vocabulary} {gap.failure_type}",
            f"{domain} {gap.required_response} under {gap.observable_failure_signal}",
            f"{domain} {structural}",
        ]
    return output
