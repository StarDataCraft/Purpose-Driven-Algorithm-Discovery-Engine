import os
import subprocess
import sys

from config import load_settings


def test_mode_selection(monkeypatch):
    monkeypatch.setenv("GAP_ENGINE_MODE", "enhanced")
    monkeypatch.setenv("ENABLE_SPECTER2", "false")
    settings = load_settings()
    assert settings.gap_engine_mode == "enhanced"
    assert not settings.enable_specter2


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
