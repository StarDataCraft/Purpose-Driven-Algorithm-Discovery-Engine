"""Application configuration and bounded defaults."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
FIXTURE_DIR = DATA_DIR / "offline_fixtures"
DEFAULT_DB = ROOT / "research_memory.db"

ML_DOMAIN = "machine_learning"
EXTERNAL_DOMAINS = (
    "biology", "ecology", "immunology", "neuroscience", "physics",
    "control_theory", "economics", "mechanism_design", "cognitive_science",
    "complex_systems", "operations_research", "dynamical_systems",
    "information_theory", "decision_theory", "evolutionary_systems",
    "network_science",
)
MODIFICATION_SLOTS = (
    "objective", "update_rule", "state_representation", "memory", "routing",
    "assignment", "aggregation", "uncertainty_estimate", "regularization",
    "sampling", "stopping", "component_birth_death", "model_selection",
    "initialization", "feedback_control", "expert_selection",
    "feature_acquisition", "state_estimation", "regime_detection",
)


@dataclass(frozen=True)
class Settings:
    """Network and search limits suitable for Streamlit Community Cloud."""

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


def _flag(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).casefold() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    mode = os.getenv("GAP_ENGINE_MODE", "lightweight").casefold()
    if mode not in {"lightweight", "enhanced", "full"}:
        mode = "lightweight"
    return Settings(
        gap_engine_mode=mode,
        enable_specter2=_flag("ENABLE_SPECTER2", mode in {"enhanced", "full"}),
        enable_scibert=_flag("ENABLE_SCIBERT", mode == "full"),
        transformer_device=os.getenv("TRANSFORMER_DEVICE", "cpu"),
        transformer_batch_size=int(os.getenv("TRANSFORMER_BATCH_SIZE", "8")),
        transformer_max_papers=int(os.getenv("TRANSFORMER_MAX_PAPERS", "200")),
        transformer_max_sentences=int(os.getenv("TRANSFORMER_MAX_SENTENCES", "1000")),
        model_cache_dir=os.getenv("MODEL_CACHE_DIR", ".model_cache"),
        scibert_checkpoint=os.getenv("SCIBERT_CHECKPOINT", ""),
    )


SETTINGS = load_settings()
