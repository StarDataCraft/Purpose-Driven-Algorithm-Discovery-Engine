"""Canonical, environment-backed application settings schema."""

from __future__ import annotations

import os
from dataclasses import dataclass, fields
from typing import Mapping

VALID_GAP_ENGINE_MODES = frozenset({"lightweight", "enhanced", "full"})


@dataclass(frozen=True)
class Settings:
    """Single source of truth for network, search, and local model settings."""

    request_timeout: float = 12.0
    max_retries: int = 3
    rate_limit_seconds: float = 0.15
    max_papers: int = 50
    max_candidates: int = 24
    max_graph_nodes: int = 1000
    cache_ttl_seconds: int = 86_400
    openalex_email: str | None = None
    gap_engine_mode: str = "lightweight"
    enable_specter2: bool = False
    enable_scibert: bool = False
    transformer_device: str = "cpu"
    transformer_batch_size: int = 8
    transformer_max_papers: int = 200
    transformer_max_sentences: int = 1000
    model_cache_dir: str = ".model_cache"
    clustering_threshold: float = 0.55
    semantic_deduplication_threshold: float = 0.88
    minimum_coverage_support: int = 3
    maximum_unknown_ratio: float = 0.45
    max_embedding_cache_records: int = 5000
    max_annotation_rows: int = 1000
    scibert_checkpoint: str = ""
    configuration_warnings: tuple[str, ...] = ()

    @property
    def engine_mode(self) -> str:
        """Backward-compatible alias; canonical storage is gap_engine_mode."""
        return self.gap_engine_mode

    @property
    def requested_mode(self) -> str:
        """Backward-compatible alias; canonical storage is gap_engine_mode."""
        return self.gap_engine_mode


def _flag(environment: Mapping[str, str], name: str, default: bool) -> bool:
    value = environment.get(name)
    if value is None:
        return default
    return value.casefold() in {"1", "true", "yes", "on"}


def _integer(
    environment: Mapping[str, str],
    name: str,
    default: int,
    warnings: list[str],
    minimum: int = 1,
) -> int:
    value = environment.get(name)
    if value is None:
        return default
    try:
        parsed = int(value)
        if parsed < minimum:
            raise ValueError
        return parsed
    except ValueError:
        warnings.append(
            f"Invalid {name}={value!r}; using deployment-safe default {default}."
        )
        return default


def load_settings(environment: Mapping[str, str] | None = None) -> Settings:
    """Create a fresh normalized settings object from an environment mapping."""
    environment = os.environ if environment is None else environment
    warnings: list[str] = []
    raw_mode = environment.get("GAP_ENGINE_MODE", "lightweight").strip().casefold()
    mode = raw_mode
    if mode not in VALID_GAP_ENGINE_MODES:
        warnings.append(
            f"Invalid GAP_ENGINE_MODE={raw_mode!r}; using 'lightweight'."
        )
        mode = "lightweight"
    return Settings(
        gap_engine_mode=mode,
        enable_specter2=_flag(
            environment, "ENABLE_SPECTER2", mode in {"enhanced", "full"}
        ),
        enable_scibert=_flag(environment, "ENABLE_SCIBERT", mode == "full"),
        transformer_device=environment.get("TRANSFORMER_DEVICE", "cpu"),
        transformer_batch_size=_integer(
            environment, "TRANSFORMER_BATCH_SIZE", 8, warnings
        ),
        transformer_max_papers=_integer(
            environment, "TRANSFORMER_MAX_PAPERS", 200, warnings
        ),
        transformer_max_sentences=_integer(
            environment, "TRANSFORMER_MAX_SENTENCES", 1000, warnings
        ),
        model_cache_dir=environment.get("MODEL_CACHE_DIR", ".model_cache"),
        scibert_checkpoint=environment.get("SCIBERT_CHECKPOINT", ""),
        configuration_warnings=tuple(warnings),
    )


def setting_field_names() -> set[str]:
    """Expose the canonical contract for static reference tests."""
    return {field.name for field in fields(Settings)} | {
        "engine_mode", "requested_mode"
    }


SETTINGS = load_settings()
