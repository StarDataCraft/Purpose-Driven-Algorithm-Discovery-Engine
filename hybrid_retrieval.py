"""Auditable sparse/dense retrieval using reciprocal-rank fusion."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from models import Paper
from scientific_embeddings import ScientificEmbeddingBackend, TfidfEmbeddingBackend


@dataclass
class RetrievalScore:
    paper_id: str
    sparse_rank: int
    dense_rank: int | None
    hybrid_rank: int
    sparse_score: float
    dense_score: float | None
    fusion_score: float


def scientific_query_text(task: str, failure: str, algorithm: str,
                          condition: str, response: str, metric: str,
                          deployment: str) -> str:
    return ". ".join(filter(None, [
        f"Task: {task}", f"Failure: {failure}", f"Algorithm: {algorithm}",
        f"Data condition: {condition}", f"Desired response: {response}",
        f"Metric: {metric}", f"Deployment: {deployment}",
    ]))


def _ranks(scores: np.ndarray) -> dict[int, int]:
    order = np.argsort(-scores, kind="stable")
    return {int(index): rank + 1 for rank, index in enumerate(order)}


def hybrid_rerank(papers: list[Paper], lexical_query: str, semantic_query: str,
                  dense_backend: ScientificEmbeddingBackend | None = None,
                  rrf_k: int = 60) -> tuple[list[Paper], list[RetrievalScore]]:
    sparse = TfidfEmbeddingBackend()
    documents = sparse.embed_documents(papers)
    sparse_query = sparse.embed_queries([lexical_query])
    sparse_scores = cosine_similarity(documents, sparse_query).ravel()
    sparse_ranks = _ranks(sparse_scores)
    dense_scores = None
    dense_ranks = {}
    if dense_backend and dense_backend.model_info().backend != "tfidf":
        dense_documents = dense_backend.embed_documents(papers)
        dense_query = dense_backend.embed_queries([semantic_query])
        dense_scores = cosine_similarity(dense_documents, dense_query).ravel()
        dense_ranks = _ranks(dense_scores)
    fusion = np.array([
        1 / (rrf_k + sparse_ranks[index]) +
        (1 / (rrf_k + dense_ranks[index]) if dense_scores is not None else 0)
        for index in range(len(papers))
    ])
    hybrid_ranks = _ranks(fusion)
    order = sorted(range(len(papers)), key=lambda i: hybrid_ranks[i])
    scores = [
        RetrievalScore(
            papers[index].paper_id, sparse_ranks[index],
            dense_ranks.get(index), hybrid_ranks[index],
            round(float(sparse_scores[index]), 6),
            round(float(dense_scores[index]), 6) if dense_scores is not None else None,
            round(float(fusion[index]), 6),
        ) for index in order
    ]
    return [papers[index] for index in order], scores
