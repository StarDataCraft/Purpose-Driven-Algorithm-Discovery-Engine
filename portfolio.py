"""Quality-diversity archive preventing mechanism and family monopolies."""

from __future__ import annotations

from collections import Counter

from models import AlgorithmCandidate


def quality_diversity_portfolio(candidates: list[AlgorithmCandidate], limit: int = 12
                                ) -> list[AlgorithmCandidate]:
    """Greedy grid archive across family/domain/slot/risk cells."""
    selected: list[AlgorithmCandidate] = []
    family_count: Counter[str] = Counter()
    mechanism_count: Counter[str] = Counter()
    cells: set[tuple[str, str, str]] = set()
    for candidate in sorted(candidates, key=lambda item: item.scores.total, reverse=True):
        mechanism = candidate.borrowed_mechanisms[0]
        domain = candidate.source_domains[0]
        cell = (candidate.base_algorithm_family, domain, candidate.affected_component)
        if cell in cells:
            continue
        cap = max(1, (limit + 2) // 3)
        if family_count[candidate.base_algorithm_family] >= cap or mechanism_count[mechanism] >= cap:
            continue
        selected.append(candidate)
        cells.add(cell)
        family_count[candidate.base_algorithm_family] += 1
        mechanism_count[mechanism] += 1
        if len(selected) >= limit:
            break
    return selected
