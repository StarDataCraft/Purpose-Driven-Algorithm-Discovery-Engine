"""Contracts protecting the production structural-discovery integration."""

from __future__ import annotations

import inspect
import re

import app
from app_settings import SETTINGS
from discovery_pipeline import discover_structural_gaps
from scientific_embeddings import TfidfEmbeddingBackend


def test_app_uses_canonical_structural_pipeline():
    source = inspect.getsource(app.goal_page)
    assert "discover_structural_gaps(" in source
    assert "apply_discovery_result(" in source


def test_offline_pipeline_produces_explicit_coverage_and_assumption_gaps(
    ml_papers, purpose
):
    # The bundled evidence is kept offline; add metric wording in memory so the
    # relevance-aware omission detector has comparable neighboring cells.
    for paper in ml_papers:
        paper.abstract = re.sub(
            r"recovery time|robustness|stability", "resilience",
            paper.abstract, flags=re.I,
        ) + " Evaluation reports online accuracy."
        paper.sections = {
            section: re.sub(
                r"recovery time|robustness|stability", "resilience",
                body, flags=re.I,
            )
            for section, body in paper.sections.items()
        }

    result = discover_structural_gaps(ml_papers, purpose)
    gap_types = {
        gap.structural_gap_subtype or gap.gap_type for gap in result.gaps
    }

    assert gap_types & {"explicit", "repeated"}
    assert "coverage" in gap_types
    assert "assumption_mismatch" in gap_types
    assert result.coverage_records
    assert result.known_solution_results


def test_production_entry_point_is_not_cue_only(ml_papers, purpose):
    result = discover_structural_gaps(ml_papers, purpose)

    assert result.assumption_mismatches
    assert any(
        gap.structural_gap_subtype == "assumption_mismatch"
        for gap in result.gaps
    )


def test_enhanced_backend_failure_is_recorded_as_fallback(
    ml_papers, purpose
):
    def unavailable_backend(mode, enabled, failures):
        assert mode == "enhanced"
        assert enabled
        failures.append("SPECTER2 unavailable in regression test")
        return TfidfEmbeddingBackend()

    enhanced = type(SETTINGS)(
        **{
            **SETTINGS.__dict__,
            "gap_engine_mode": "enhanced",
            "enable_specter2": True,
        }
    )
    result = discover_structural_gaps(
        ml_papers, purpose, settings=enhanced,
        backend_selector=unavailable_backend,
    )

    assert result.diagnostics["requested_mode"] == "enhanced"
    assert result.diagnostics["active_mode"] == "lightweight"
    assert result.diagnostics["fallback_occurred"] is True
    assert result.diagnostics["retrieval_method"] == "HYBRID FALLBACK"
    assert "SPECTER2 unavailable" in result.diagnostics["model_failures"][0]
