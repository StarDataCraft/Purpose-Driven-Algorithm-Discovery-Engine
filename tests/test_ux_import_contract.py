"""Strict deployment contract for the UX module imported by app.py."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
IMPORT_CONTRACT = """
from ux_models import (
    PIPELINE_VERSION, SELECTED_IDEA_SCHEMA_VERSION, SelectedIdeaContext,
    build_direction_portfolio, build_idea_derivation, build_idea_explanation,
    candidate_from_dict, candidate_modification, candidate_to_dict,
    derivation_from_dict, derivation_to_dict, direction_from_dict,
    direction_to_dict, gap_from_dict, gap_to_dict, selected_idea_fingerprints,
)
assert PIPELINE_VERSION
assert SELECTED_IDEA_SCHEMA_VERSION
assert SelectedIdeaContext is not None
import app
print("strict isolated import passed")
"""


def test_app_ux_import_contract() -> None:
    namespace: dict[str, object] = {}
    exec(IMPORT_CONTRACT, namespace)


def test_app_ux_import_contract_in_isolated_subprocess() -> None:
    code = (
        "import sys; "
        f"sys.path.insert(0, {str(ROOT)!r}); "
        + IMPORT_CONTRACT
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", code], cwd=ROOT,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "strict isolated import passed" in result.stdout
