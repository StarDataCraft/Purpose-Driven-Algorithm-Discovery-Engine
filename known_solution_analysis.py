"""Deterministic known-mitigation query generation and local-corpus triage."""

from __future__ import annotations

from dataclasses import dataclass

from models import GapSignature, Paper


@dataclass
class KnownSolutionResult:
    gap_id: str
    queries: list[str]
    mitigating_methods: list[str]
    status: str
    unresolved_remainder: str
    search_coverage: str
    uncertainty: str


def known_solution_queries(gap: GapSignature) -> list[str]:
    return list(dict.fromkeys([
        f"{gap.affected_algorithm} {gap.failure_type}",
        f"{gap.task} {gap.missing_dimension or gap.failure_type}",
        f"{gap.task} {gap.primary_metric}",
        f"{gap.affected_algorithm} robust variant",
        f"{gap.affected_algorithm} online variant",
        f"{gap.failure_type} benchmark",
    ]))


def assess_known_solutions(gap: GapSignature, papers: list[Paper]
                           ) -> KnownSolutionResult:
    queries = known_solution_queries(gap)
    tokens = {
        token for token in
        f"{gap.failure_type} {gap.affected_algorithm}".casefold().split()
        if len(token) > 4
    }
    matches = [
        paper.title for paper in papers
        if tokens and len(tokens & set(paper.title.casefold().split())) >= 1
        and any(term in f"{paper.title} {paper.abstract}".casefold()
                for term in ("adaptive", "robust", "handling", "mitigation", "nonstationary"))
    ]
    status = "partially addressed" if matches else "insufficient evidence"
    return KnownSolutionResult(
        gap.gap_id, queries, matches, status,
        "Determine whether mitigation covers the same condition, metric, and deployment scope.",
        f"local retrieved corpus ({len(papers)} papers)",
        "A dedicated live query may find additional mitigations.",
    )
