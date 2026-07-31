"""Optional local scientific encoders with a lightweight TF-IDF fallback."""

from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from models import Paper
from text_processing import fingerprint, normalize_text


@dataclass
class EmbeddingInfo:
    backend: str
    model_name: str
    model_version: str
    available: bool
    failure: str = ""
    cache_hits: int = 0
    cache_misses: int = 0
    adapter: str = ""


class ScientificEmbeddingBackend(ABC):
    @abstractmethod
    def embed_documents(self, papers: list[Paper]) -> np.ndarray: ...

    @abstractmethod
    def embed_queries(self, queries: list[str]) -> np.ndarray: ...

    @abstractmethod
    def model_info(self) -> EmbeddingInfo: ...

    def is_available(self) -> bool:
        return self.model_info().available


class TfidfEmbeddingBackend(ScientificEmbeddingBackend):
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2), stop_words="english", max_features=4096
        )
        self._fitted = False

    def embed_documents(self, papers: list[Paper]) -> np.ndarray:
        texts = [f"{paper.title}. {paper.abstract}" for paper in papers]
        self._fitted = True
        return self.vectorizer.fit_transform(texts).toarray()

    def embed_queries(self, queries: list[str]) -> np.ndarray:
        if not self._fitted:
            self.vectorizer.fit(queries)
            self._fitted = True
        return self.vectorizer.transform(queries).toarray()

    def model_info(self) -> EmbeddingInfo:
        return EmbeddingInfo("tfidf", "scikit-learn TF-IDF", "tfidf-v1", True)


class Specter2EmbeddingBackend(ScientificEmbeddingBackend):
    """Lazy CPU-capable SPECTER2 encoder; imports transformers only on use."""

    def __init__(self, model_name: str = "allenai/specter2",
                 device: str = "cpu", batch_size: int = 8):
        self.model_name, self.device, self.batch_size = model_name, device, batch_size
        self._tokenizer = self._model = None
        self._failure = ""

    def _load(self) -> None:
        if self._model is not None or self._failure:
            return
        try:
            import torch
            from adapters import AutoAdapterModel
            from transformers import AutoTokenizer
            base_model = "allenai/specter2_base"
            self._tokenizer = AutoTokenizer.from_pretrained(base_model)
            self._model = AutoAdapterModel.from_pretrained(base_model)
            self._model.load_adapter(
                self.model_name, source="hf", load_as="specter2",
                set_active=True,
            )
            self._model.to(self.device).eval()
        except Exception as exc:
            self._failure = f"{type(exc).__name__}: {exc}"
            raise RuntimeError(self._failure) from exc

    def _embed(self, texts: list[str]) -> np.ndarray:
        self._load()
        import torch
        batches = []
        for start in range(0, len(texts), self.batch_size):
            encoded = self._tokenizer(
                texts[start:start + self.batch_size], padding=True,
                truncation=True, max_length=512, return_tensors="pt",
            ).to(self.device)
            with torch.no_grad():
                output = self._model(**encoded).last_hidden_state[:, 0, :]
            array = output.cpu().numpy()
            array /= np.maximum(np.linalg.norm(array, axis=1, keepdims=True), 1e-12)
            batches.append(array)
        return np.vstack(batches) if batches else np.empty((0, 0))

    def embed_documents(self, papers: list[Paper]) -> np.ndarray:
        return self._embed([f"{paper.title}{self._tokenizer.sep_token if self._tokenizer else ' [SEP] '}{paper.abstract}"
                            for paper in papers])

    def embed_queries(self, queries: list[str]) -> np.ndarray:
        return self._embed(queries)

    def model_info(self) -> EmbeddingInfo:
        return EmbeddingInfo(
            "specter2", "allenai/specter2_base", "local-pretrained",
            not bool(self._failure), self._failure,
            adapter=self.model_name,
        )


class EmbeddingCache:
    """SQLite cache keyed by model and content fingerprint."""

    def __init__(self, path: Path, max_records: int = 5000):
        self.max_records = max_records
        self.connection = sqlite3.connect(str(path))
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS embeddings (
               cache_key TEXT PRIMARY KEY, model TEXT, fingerprint TEXT,
               vector TEXT, created_at TEXT)"""
        )

    @staticmethod
    def key(model: str, paper: Paper, preprocessing: str = "v1") -> str:
        content = fingerprint(
            f"{normalize_text(paper.title)}:{normalize_text(paper.abstract)}"
        )
        return f"{model}:{preprocessing}:{paper.paper_id}:{content}"

    def get(self, key: str) -> np.ndarray | None:
        row = self.connection.execute(
            "SELECT vector FROM embeddings WHERE cache_key=?", (key,)
        ).fetchone()
        return np.array(json.loads(row[0]), dtype=float) if row else None

    def put(self, key: str, model: str, content_fingerprint: str,
            vector: np.ndarray) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO embeddings VALUES(?,?,?,?,?)",
            (key, model, content_fingerprint, json.dumps(vector.tolist()),
             datetime.now(timezone.utc).isoformat()),
        )
        self.connection.commit()
        self.connection.execute(
            """DELETE FROM embeddings WHERE cache_key IN (
               SELECT cache_key FROM embeddings ORDER BY created_at ASC
               LIMIT MAX(0, (SELECT COUNT(*) FROM embeddings) - ?)
            )""", (self.max_records,)
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()


def select_embedding_backend(mode: str, enable_specter2: bool,
                             failure_log: list[str] | None = None
                             ) -> ScientificEmbeddingBackend:
    if mode in {"enhanced", "full"} and enable_specter2:
        backend = Specter2EmbeddingBackend()
        try:
            backend._load()
            return backend
        except RuntimeError as exc:
            if failure_log is not None:
                failure_log.append(str(exc))
    return TfidfEmbeddingBackend()
