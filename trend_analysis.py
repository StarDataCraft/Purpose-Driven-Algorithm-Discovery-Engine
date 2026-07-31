"""Lightweight evidence trends that never dominate candidate quality."""

from __future__ import annotations

from collections import Counter

from models import Paper


def trend_indicators(papers: list[Paper]) -> dict[str, object]:
    by_year = Counter(paper.year for paper in papers)
    years = sorted(by_year)
    growth = 0.0
    if len(years) >= 2 and by_year[years[-2]]:
        growth = (by_year[years[-1]] - by_year[years[-2]]) / by_year[years[-2]]
    return {
        "publication_count_by_year": dict(by_year),
        "recent_growth_rate": round(growth, 2),
        "discipline_spread": len({paper.domain for paper in papers}),
        "source_diversity": len({paper.source for paper in papers}),
        "citation_proxy": sum(paper.citations for paper in papers),
    }
