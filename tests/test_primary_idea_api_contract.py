"""Versioned primary-selector call and mixed-deployment regressions."""

from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path

import app
import primary_idea_selection
from primary_idea_contracts import (
    PRIMARY_IDEA_SELECTION_API_VERSION, PrimaryIdeaSelectionRequest,
)


ROOT = Path(__file__).parents[1]


def test_primary_idea_selection_api_contract_is_single_request():
    assert PRIMARY_IDEA_SELECTION_API_VERSION == "primary-idea-selection-v2"
    assert tuple(inspect.signature(
        primary_idea_selection.select_primary_idea
    ).parameters) == ("request",)
    assert app.selector_contract_diagnostic()["compatible"]
    app.assert_selector_contract()
    request = PrimaryIdeaSelectionRequest(
        api_version=PRIMARY_IDEA_SELECTION_API_VERSION,
        candidates=(), derivations=(), direction=None, gap=None,
        parent_run=None,
    )
    assert primary_idea_selection.select_primary_idea(request).status == "NO_CANDIDATES"


def test_production_app_does_not_call_many_keyword_selector_interface():
    tree = ast.parse((ROOT / "app.py").read_text())
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    selector_calls = [node for node in calls if isinstance(node.func, ast.Attribute)
                      and node.func.attr == "select_primary_idea"]
    assert len(selector_calls) == 1
    assert len(selector_calls[0].args) == 1
    assert not selector_calls[0].keywords


def test_old_request_schema_fails_with_clear_version_diagnostic():
    request = PrimaryIdeaSelectionRequest(
        api_version="primary-idea-selection-v1", candidates=(), derivations=(),
        direction=None, gap=None, parent_run=None,
    )
    try:
        primary_idea_selection.select_primary_idea(request)
    except ValueError as exc:
        assert "expected API primary-idea-selection-v2" in str(exc)
    else:
        raise AssertionError("Old request version was silently accepted")


def test_module_reload_exposes_current_callable_identity():
    before = primary_idea_selection.select_primary_idea
    reloaded = importlib.reload(primary_idea_selection)
    assert app.primary_selector is reloaded
    assert app.primary_selector.select_primary_idea is reloaded.select_primary_idea
    assert reloaded.select_primary_idea is not before
    assert app.selector_contract_diagnostic()["compatible"]


def test_mixed_module_version_is_detected_before_selection(monkeypatch):
    monkeypatch.setattr(
        app.primary_selector, "PRIMARY_IDEA_SELECTION_API_VERSION",
        "primary-idea-selection-v1",
    )
    diagnostic = app.selector_contract_diagnostic()
    assert not diagnostic["compatible"]
    assert diagnostic["expected_api_version"] == "primary-idea-selection-v2"
    assert diagnostic["loaded_api_version"] == "primary-idea-selection-v1"
