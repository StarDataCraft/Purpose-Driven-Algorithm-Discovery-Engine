import numpy as np

from coverage_analysis import extract_coverage_records
from models import Paper
from paper_clustering import cluster_papers


def test_fixed_corpus_cluster_assignments_are_reproducible(purpose):
    papers = [
        Paper("a", "Random Forest drift", "online drift accuracy", 2024, "x"),
        Paper("b", "Ensemble drift", "online drift recovery", 2025, "y"),
        Paper("c", "K-means density", "cluster ARI heterogeneous", 2025, "x"),
    ]
    embeddings = np.array([[1., 0.], [.95, .05], [0., 1.]])
    records = extract_coverage_records(papers, purpose)
    first = cluster_papers(papers, embeddings, records, .3)
    second = cluster_papers(papers, embeddings, records, .3)
    assert [cluster.paper_ids for cluster in first] == [
        cluster.paper_ids for cluster in second
    ]
    assert len(first) == 2
