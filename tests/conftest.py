"""Shared deterministic offline fixtures."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models import Paper, PurposeContract  # noqa: E402


@pytest.fixture
def purpose() -> PurposeContract:
    return PurposeContract(
        "p1", "user", "adaptive decision support", "online learning", "tabular streams",
        "recurring concept drift", "reduce recovery time", "average online accuracy",
        ["recovery time", "memory use"], ["stable-regime accuracy"],
        available_training_information=["features", "delayed outcome feedback"],
        available_inference_information=[
            "input features", "prediction residual", "regime similarity",
            "observable deviation", "outcome feedback", "component overlap",
            "observable outputs", "order parameter",
        ],
        allowed_algorithm_families=["ensemble"],
    )


@pytest.fixture
def ml_papers() -> list[Paper]:
    values = json.loads((ROOT / "data/offline_fixtures/ml_papers.json").read_text())
    return [Paper(**value) for value in values]


@pytest.fixture
def external_papers() -> list[Paper]:
    values = json.loads((ROOT / "data/offline_fixtures/external_papers.json").read_text())
    return [Paper(**value) for value in values]
