import numpy as np

from hybrid_retrieval import hybrid_rerank
from models import Paper
from scientific_embeddings import (
    EmbeddingCache, EmbeddingInfo, ScientificEmbeddingBackend,
    select_embedding_backend,
)


class FakeBackend(ScientificEmbeddingBackend):
    def embed_documents(self, papers):
        return np.array([[1., 0.], [0., 1.], [.7, .7]])

    def embed_queries(self, queries):
        return np.array([[0., 1.]])

    def model_info(self):
        return EmbeddingInfo("fake-dense", "fake", "1", True)


def papers():
    return [
        Paper("exact", "robustness", "keyword only", 2025, "x"),
        Paper("semantic", "adaptive recovery", "returns rapidly after changing regimes", 2025, "x"),
        Paper("other", "general study", "robustness under unrelated setting", 2025, "x"),
    ]


def test_hybrid_preserves_sparse_and_adds_semantic_rank():
    ranked, scores = hybrid_rerank(
        papers(), "robustness", "recovery under regimes", FakeBackend()
    )
    by_id = {score.paper_id: score for score in scores}
    assert by_id["exact"].sparse_rank < by_id["semantic"].sparse_rank
    assert by_id["semantic"].dense_rank == 1
    assert {paper.paper_id for paper in ranked} == {"exact", "semantic", "other"}


def test_rank_fusion_is_deterministic():
    first = hybrid_rerank(papers(), "robustness", "recovery", FakeBackend())[1]
    second = hybrid_rerank(papers(), "robustness", "recovery", FakeBackend())[1]
    assert first == second


def test_embedding_cache_invalidates_changed_abstract(tmp_path):
    cache = EmbeddingCache(tmp_path / "embeddings.sqlite")
    paper = papers()[0]
    first = cache.key("model", paper)
    paper.abstract = "changed"
    second = cache.key("model", paper)
    assert first != second
    cache.close()


def test_model_failure_falls_back(monkeypatch):
    def fail(self):
        raise RuntimeError("unavailable")
    monkeypatch.setattr("scientific_embeddings.Specter2EmbeddingBackend._load", fail)
    failures = []
    backend = select_embedding_backend("enhanced", True, failures)
    assert backend.model_info().backend == "tfidf"
    assert failures == ["unavailable"]
