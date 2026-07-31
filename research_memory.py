"""SQLite research memory including failures that suppress repeated weak paths."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
 id INTEGER PRIMARY KEY, kind TEXT NOT NULL, record_key TEXT NOT NULL,
 payload TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(kind, record_key)
);
CREATE TABLE IF NOT EXISTS failures (
 fingerprint TEXT PRIMARY KEY, category TEXT NOT NULL, reason TEXT NOT NULL,
 occurrences INTEGER NOT NULL DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ratings (
 candidate_id TEXT PRIMARY KEY, rating REAL NOT NULL, notes TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS schema_migrations (
 version INTEGER PRIMARY KEY, applied_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS structural_records (
 id INTEGER PRIMARY KEY, kind TEXT NOT NULL, record_key TEXT NOT NULL,
 payload TEXT NOT NULL, model_mode TEXT, model_version TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(kind, record_key)
);
INSERT OR IGNORE INTO schema_migrations(version) VALUES (2);
"""

FAILURE_CATEGORIES = {
    "mechanism-slot incompatibility", "metaphor-only transfer",
    "unavailable inference signal", "label leakage", "future-information leakage",
    "duplicate of known method", "no measurable improvement", "excessive complexity",
    "weak evidence", "poor purpose fit", "failure under ablation",
    "parameter-count confound", "compute-budget violation", "memory-budget violation",
    "unstable update", "unsupported mechanism extraction",
}


class ResearchMemory:
    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.executescript(SCHEMA)

    def save(self, kind: str, record_key: str, record: Any) -> None:
        payload = asdict(record) if is_dataclass(record) else record
        self.connection.execute(
            "INSERT OR REPLACE INTO records(kind,record_key,payload) VALUES(?,?,?)",
            (kind, record_key, json.dumps(payload, default=str)),
        )
        self.connection.commit()

    def list(self, kind: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT record_key,payload,created_at FROM records WHERE kind=? ORDER BY id DESC", (kind,)
        ).fetchall()
        return [{"key": key, "payload": json.loads(payload), "created_at": created}
                for key, payload, created in rows]

    def remember_failure(self, fingerprint: str, category: str, reason: str) -> None:
        if category not in FAILURE_CATEGORIES:
            category = "weak evidence"
        self.connection.execute(
            """INSERT INTO failures(fingerprint,category,reason) VALUES(?,?,?)
               ON CONFLICT(fingerprint) DO UPDATE SET occurrences=occurrences+1, reason=excluded.reason""",
            (fingerprint, category, reason),
        )
        self.connection.commit()

    def failure_penalty(self, fingerprint: str) -> float:
        row = self.connection.execute(
            "SELECT occurrences FROM failures WHERE fingerprint=?", (fingerprint,)
        ).fetchone()
        return min(.5, .1 * row[0]) if row else 0.0

    def failures(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT fingerprint,category,reason,occurrences FROM failures ORDER BY occurrences DESC"
        ).fetchall()
        return [dict(zip(("fingerprint", "category", "reason", "occurrences"), row)) for row in rows]

    def failure_penalties(self) -> dict[str, float]:
        """Expose bounded penalties for future search runs."""
        return {
            fingerprint: min(.5, .1 * occurrences)
            for fingerprint, occurrences in self.connection.execute(
                "SELECT fingerprint,occurrences FROM failures"
            ).fetchall()
        }

    def rate(self, candidate_id: str, rating: float, notes: str = "") -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO ratings(candidate_id,rating,notes) VALUES(?,?,?)",
            (candidate_id, rating, notes),
        )
        self.connection.commit()

    def save_structural(self, kind: str, record_key: str, record: Any,
                        model_mode: str = "lightweight",
                        model_version: str = "") -> None:
        payload = asdict(record) if is_dataclass(record) else record
        self.connection.execute(
            """INSERT OR REPLACE INTO structural_records
               (kind,record_key,payload,model_mode,model_version) VALUES(?,?,?,?,?)""",
            (kind, record_key, json.dumps(payload, default=str),
             model_mode, model_version),
        )
        self.connection.commit()

    def save_evaluation_review(self, review: Any) -> None:
        """Persist optional human quality labels without mixing them with outputs."""
        self.save("evaluation_review", review.item_id + ":" + review.timestamp, review)

    def evaluation_reviews(self) -> list[dict[str, Any]]:
        return self.list("evaluation_review")

    def schema_version(self) -> int:
        row = self.connection.execute(
            "SELECT MAX(version) FROM schema_migrations"
        ).fetchone()
        return int(row[0] or 1)

    def close(self) -> None:
        self.connection.close()
