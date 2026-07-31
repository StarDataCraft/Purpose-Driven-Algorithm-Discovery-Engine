"""Curated algorithm skeletons with strict weakness ownership."""

from __future__ import annotations

import json
from pathlib import Path

from config import DATA_DIR
from models import AlgorithmRecord, GapSignature


def load_algorithm_library(path: Path | None = None) -> dict[str, AlgorithmRecord]:
    """Load compact JSON records and fill documented common fields."""
    raw = json.loads((path or DATA_DIR / "algorithm_library.json").read_text())
    records: dict[str, AlgorithmRecord] = {}
    for item in raw:
        record = AlgorithmRecord(
            aliases=item.get("aliases", []),
            objective=item.get("objective", "minimize the algorithm-specific empirical objective"),
            update_rule=item.get("update_rule", "fit parameters from observed training data"),
            state=item.get("state", "learned parameters and sufficient statistics"),
            information_flow=item.get("information_flow", "features to state to prediction"),
            strengths=item.get("strengths", ["established baseline"]),
            runtime_complexity=item.get("runtime_complexity", "algorithm and data dependent"),
            memory_complexity=item.get("memory_complexity", "algorithm and data dependent"),
            interpretability=item.get("interpretability", "family dependent"),
            online_capability=item.get("online_capability", "limited"),
            uncertainty_capability=item.get("uncertainty_capability", "limited"),
            missing_data_capability=item.get("missing_data_capability", "requires preprocessing"),
            canonical_baselines=item.get("canonical_baselines", []),
            related_methods=item.get("related_methods", []),
            **{key: item[key] for key in (
                "name", "family", "tasks", "data_types", "assumptions", "weaknesses",
                "known_failure_conditions", "modifiable_slots"
            )},
        )
        records[record.name.lower()] = record
    return records


def get_algorithm(name: str, library: dict[str, AlgorithmRecord] | None = None) -> AlgorithmRecord:
    """Resolve an algorithm by canonical name or alias."""
    library = library or load_algorithm_library()
    needle = name.lower()
    if needle in library:
        return library[needle]
    for record in library.values():
        if needle in (alias.lower() for alias in record.aliases):
            return record
    raise KeyError(f"Unknown algorithm: {name}")


def weakness_belongs(
    algorithm: AlgorithmRecord, weakness: str, gap: GapSignature | None = None
) -> bool:
    """Allow a weakness only if owned by the algorithm or explicitly evidenced."""
    normalized = weakness.casefold()
    if normalized in {value.casefold() for value in algorithm.weaknesses}:
        return True
    return bool(
        gap
        and gap.affected_algorithm.casefold() == algorithm.name.casefold()
        and gap.evidence_count > 0
        and normalized in gap.failure_type.casefold()
    )


ASSUMPTION_REGISTRY = {
    record.name: record.assumptions for record in load_algorithm_library().values()
}
