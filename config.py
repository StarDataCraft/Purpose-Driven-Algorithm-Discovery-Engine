"""Application configuration and bounded defaults."""

from __future__ import annotations

from pathlib import Path

from app_settings import SETTINGS, Settings, load_settings

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
