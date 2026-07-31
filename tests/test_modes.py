import os
import re
import subprocess
import sys
from pathlib import Path

import app
import app_settings
import config
from app_settings import load_settings, setting_field_names


def test_mode_selection(monkeypatch):
    monkeypatch.setenv("GAP_ENGINE_MODE", "enhanced")
    monkeypatch.setenv("ENABLE_SPECTER2", "false")
    settings = load_settings()
    assert settings.gap_engine_mode == "enhanced"
    assert not settings.enable_specter2


def test_default_full_and_invalid_modes():
    default = load_settings({})
    enhanced = load_settings({"GAP_ENGINE_MODE": "enhanced"})
    full = load_settings({"GAP_ENGINE_MODE": "full"})
    invalid = load_settings({"GAP_ENGINE_MODE": "invalid"})
    assert default.gap_engine_mode == "lightweight"
    assert enhanced.gap_engine_mode == "enhanced"
    assert full.gap_engine_mode == "full"
    assert invalid.gap_engine_mode == "lightweight"
    assert invalid.configuration_warnings
    assert enhanced.engine_mode == enhanced.gap_engine_mode
    assert full.requested_mode == full.gap_engine_mode


def test_single_settings_construction_and_reference_contract():
    assert config.SETTINGS is app_settings.SETTINGS
    assert app.SETTINGS is app_settings.SETTINGS
    root = Path(__file__).resolve().parents[1]
    referenced = set()
    for path in root.glob("*.py"):
        referenced.update(re.findall(r"SETTINGS\.([A-Za-z_][A-Za-z0-9_]*)", path.read_text()))
    assert referenced <= setting_field_names()


def test_engine_state_defaults_handles_legacy_hot_reload_object():
    class LegacySettings:
        engine_mode = "enhanced"

    defaults = app.engine_state_defaults(LegacySettings())
    assert defaults["requested_mode"] == "enhanced"
    assert defaults["active_mode"] == "lightweight"
    assert defaults["configuration_warnings"]


def test_lightweight_import_does_not_import_transformers():
    code = (
        "import sys; import scientific_embeddings; "
        "assert 'transformers' not in sys.modules; print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True,
        env={**os.environ, "GAP_ENGINE_MODE": "lightweight"},
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "ok"
