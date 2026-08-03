"""Regression coverage for the deployment-facing session-schema contract."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import app
import session_schema


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "SESSION_SCHEMA_API_VERSION",
    "SESSION_STATE_SCHEMA_VERSION",
    "normalize_primary_selection_record",
    "resolve_external_result",
}


def run_isolated(source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", source], cwd=ROOT, text=True,
        capture_output=True, check=False,
    )


def test_lightweight_import_has_complete_versioned_contract():
    assert Path(session_schema.__file__).resolve() == ROOT / "session_schema.py"
    assert REQUIRED <= set(dir(session_schema))
    assert session_schema.SESSION_SCHEMA_API_VERSION == "session-schema-api-v2"


def test_schema_import_does_not_load_external_pipeline():
    result = run_isolated(
        "import sys, session_schema; "
        "assert 'external_discovery_pipeline' not in sys.modules; "
        "print(session_schema.__file__)"
    )
    assert result.returncode == 0, result.stderr
    assert str(ROOT / "session_schema.py") in result.stdout


def test_resolver_loads_external_model_only_when_needed():
    source = """
import sys, types
import session_schema
assert 'external_discovery_pipeline' not in sys.modules
module = types.ModuleType('external_discovery_pipeline')
class ExternalDiscoveryResult:
    migration_warnings = []
    migration_provenance = 'current'
    @classmethod
    def from_dict(cls, value): return cls()
    def identity(self): return ('run', 'direction', 'gap')
module.ExternalDiscoveryResult = ExternalDiscoveryResult
sys.modules['external_discovery_pipeline'] = module
resolution = session_schema.resolve_external_result({})
assert resolution.status == 'CURRENT'
assert resolution.result is not None
"""
    result = run_isolated(source)
    assert result.returncode == 0, result.stderr


def test_old_schema_produces_contract_diagnostic_not_import_error():
    old_schema = SimpleNamespace(
        __file__="/deployment/session_schema.py",
        SESSION_SCHEMA_API_VERSION="session-schema-api-v1",
        SESSION_STATE_SCHEMA_VERSION="session-state-v1",
        resolve_external_result=lambda value: value,
    )
    diagnostic = app.session_schema_contract_diagnostic(old_schema)
    assert not diagnostic["compatible"]
    assert diagnostic["loaded_api_version"] == "session-schema-api-v1"
    assert diagnostic["missing_exports"] == ["normalize_primary_selection_record"]


def test_partially_initialized_downstream_does_not_block_schema_import():
    result = run_isolated(
        "import sys, types; "
        "sys.modules['external_discovery_pipeline'] = types.ModuleType('external_discovery_pipeline'); "
        "import session_schema; "
        "assert session_schema.SESSION_STATE_SCHEMA_VERSION == 'session-state-v2'; "
        "assert callable(session_schema.normalize_primary_selection_record)"
    )
    assert result.returncode == 0, result.stderr


def test_clean_app_import_in_subprocess():
    result = run_isolated("import app; print(app.__file__)")
    assert result.returncode == 0, result.stderr
    assert str(ROOT / "app.py") in result.stdout
