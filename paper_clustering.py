"""Deterministic deployment-friendly research clustering."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha1

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import pairwise_distances

from coverage_analysis import CoverageRecord
from models import Paper


@dataclass
class ResearchCluster:
    cluster_id: str
    label_terms: list[str]
    paper_ids: list[str]
    centroid: list[float]
    representative_papers: list[str]
    task_distribution: dict[str, int]
    algorithm_distribution: dict[str, int]
    condition_distribution: dict[str, int]
    metric_distribution: dict[str, int]
    year_distribution: dict[int, int]
    source_diversity: int
    cohesion: float
    separation: float
    embedding_model: str
    cluster_method: str
    confidence: float


def cluster_papers(papers: list[Paper], embeddings: np.ndarray,
                   records: list[CoverageRecord], threshold: float = .55
                   ) -> list[ResearchCluster]:
    if not papers:
        return []
    if len(papers) == 1:
        labels = np.array([0])
    else:
        labels = AgglomerativeClustering(
            n_clusters=None, metric="cosine", linkage="average",
            distance_threshold=threshold,
        ).fit_predict(embeddings)
    by_record = {record.paper_id: record for record in records}
    output = []
    for label in sorted(set(labels)):
        indices = [i for i, value in enumerate(labels) if value == label]
        subset = [papers[i] for i in indices]
        texts = [f"{paper.title} {paper.abstract}" for paper in subset]
        vectorizer = TfidfVectorizer(stop_words="english", max_features=8)
        matrix = vectorizer.fit_transform(texts)
        terms = list(vectorizer.get_feature_names_out()[:5])
        centroid = embeddings[indices].mean(axis=0)
        distances = pairwise_distances(embeddings[indices], centroid.reshape(1, -1), metric="cosine")
        cohesion = float(1 - distances.mean())
        records_subset = [by_record[p.paper_id] for p in subset]
        output.append(ResearchCluster(
            cluster_id="cluster:" + sha1(
                ":".join(sorted(p.paper_id for p in subset)).encode()
            ).hexdigest()[:12],
            label_terms=terms, paper_ids=[p.paper_id for p in subset],
            centroid=centroid.tolist(), representative_papers=[
                subset[int(np.argmin(distances))].paper_id
            ],
            task_distribution=dict(Counter(r.task for r in records_subset)),
            algorithm_distribution=dict(Counter(r.algorithm for r in records_subset)),
            condition_distribution=dict(Counter(
                c for r in records_subset for c in r.distribution_conditions + r.missingness_conditions
            )),
            metric_distribution=dict(Counter(
                metric for r in records_subset for metric in r.metric_categories
            )),
            year_distribution=dict(Counter(p.year for p in subset)),
            source_diversity=len({p.source for p in subset}),
            cohesion=round(cohesion, 3), separation=0.0,
            embedding_model="provided", cluster_method="agglomerative-cosine",
            confidence=round(max(0.0, cohesion), 3),
        ))
    return output
