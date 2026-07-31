"""Versioned benchmark task definitions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK_PATH = ROOT / "data/evaluation/benchmark_tasks.json"


@dataclass
class BenchmarkTask:
    task_id: str
    version: str
    title: str
    purpose: dict[str, object]
    target_concepts: list[str]
    algorithm_families: list[str]
    metrics: list[str]
    assumptions: list[str]
    known_solution_queries: list[str]


def load_benchmark_tasks(path: Path = TASK_PATH) -> dict[str, BenchmarkTask]:
    payload = json.loads(path.read_text())
    return {
        item["task_id"]: BenchmarkTask(**item) for item in payload["tasks"]
    }
