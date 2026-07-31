"""Loading and validation of structured mechanism signatures."""

from __future__ import annotations

import json

from config import DATA_DIR
from models import MechanismSignature


def load_mechanism_seeds() -> list[MechanismSignature]:
    return [
        MechanismSignature(**item)
        for item in json.loads((DATA_DIR / "mechanism_seed_library.json").read_text())
    ]
