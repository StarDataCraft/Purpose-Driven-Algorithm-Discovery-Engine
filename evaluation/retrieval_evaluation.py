"""Retrieval metrics that never imply whole-literature recall."""

from __future__ import annotations

import math
from collections import defaultdict

from models import Paper
from evaluation.schemas import QueryContribution

RELEVANCE_GAIN = {
    "HIGHLY_RELEVANT": 3, "RELEVANT": 2, "PARTIALLY_RELEVANT": 1,
    "IRRELEVANT": 0, "UNCERTAIN": 0,
}


def precision_at_k(labels: list[str], k: int) -> float:
    subset = labels[:k]
    return round(sum(RELEVANCE_GAIN.get(label, 0) >= 2 for label in subset) / max(1, k), 4)


def ndcg_at_k(labels: list[str], k: int) -> float:
    gains = [RELEVANCE_GAIN.get(label, 0) for label in labels[:k]]
    dcg = sum((2 ** gain - 1) / math.log2(index + 2)
              for index, gain in enumerate(gains))
    ideal = sorted(
        [RELEVANCE_GAIN.get(label, 0) for label in labels], reverse=True
    )[:k]
    idcg = sum((2 ** gain - 1) / math.log2(index + 2)
               for index, gain in enumerate(ideal))
    return round(dcg / idcg, 4) if idcg else 0.0


def retrieval_metrics(papers: list[Paper], labels: dict[str, str]) -> dict[str, float]:
    ordered = [labels.get(paper.paper_id, "UNCERTAIN") for paper in papers]
    relevant = sum(RELEVANCE_GAIN[label] >= 2 for label in ordered)
    highly = sum(label == "HIGHLY_RELEVANT" for label in ordered)
    return {
        "precision_at_5": precision_at_k(ordered, 5),
        "precision_at_10": precision_at_k(ordered, 10),
        "precision_at_20": precision_at_k(ordered, 20),
        "ndcg_at_10": ndcg_at_k(ordered, 10),
        "ndcg_at_20": ndcg_at_k(ordered, 20),
        "relevant_paper_count": relevant,
        "highly_relevant_paper_count": highly,
        "source_diversity": len({paper.source for paper in papers}),
        "year_coverage": len({paper.year for paper in papers}),
        "duplicate_rate": 0.0,
        "abstract_availability": round(
            sum(bool(paper.abstract) for paper in papers) / max(1, len(papers)), 4
        ),
        "full_evidence_availability": round(
            sum(bool(paper.sections) for paper in papers) / max(1, len(papers)), 4
        ),
    }


def query_contributions(
    papers: list[Paper], queries: list[str], labels: dict[str, str],
    stage: str,
) -> list[QueryContribution]:
    by_query: dict[int, list[tuple[int, Paper]]] = defaultdict(list)
    for rank, paper in enumerate(papers, 1):
        for query_id in paper.query_ids:
            if query_id.startswith("q:"):
                by_query[int(query_id.split(":")[1])].append((rank, paper))
    output = []
    for index, query in enumerate(queries):
        records = by_query.get(index, [])
        ids = {paper.paper_id for _, paper in records}
        query_labels = [labels.get(paper.paper_id, "UNCERTAIN") for _, paper in records]
        quality = []
        if records and not any(RELEVANCE_GAIN[label] >= 2 for label in query_labels):
            quality.append("LOW_YIELD")
        if not records:
            quality.append("LOW_YIELD")
        output.append(QueryContribution(
            query, True, "benchmark_problem", stage, len(records), len(ids),
            sum(RELEVANCE_GAIN[label] >= 2 for label in query_labels),
            sum(label == "HIGHLY_RELEVANT" for label in query_labels),
            max(0, len(records) - len(ids)),
            round(sum(rank for rank, _ in records) / max(1, len(records)), 3),
            [], 1, 0.0, quality,
        ))
    return output
