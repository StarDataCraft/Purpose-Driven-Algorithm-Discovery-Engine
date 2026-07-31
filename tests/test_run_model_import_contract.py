from __future__ import annotations

from dataclasses import asdict
from pathlib import Path


def test_research_run_public_import_contract():
    from search_runs import ResearchRun, SelectedGapSnapshot, StageRun

    assert ResearchRun is not None
    assert SelectedGapSnapshot is not None
    assert StageRun is not None


def test_compatibility_exports_have_canonical_identity():
    from research_runs import ResearchRun as LegacyResearchRun
    from run_models import ResearchRun as CanonicalResearchRun
    from search_runs import ResearchRun as SearchResearchRun

    assert LegacyResearchRun is CanonicalResearchRun
    assert SearchResearchRun is CanonicalResearchRun


def test_run_model_serialization_round_trip():
    from run_models import ResearchRun, SelectedGapSnapshot, StageRun

    stage = StageRun("stage:1", "paper_reranking", "run:1", "now")
    run = ResearchRun.create("purpose:1", "LIVE", "lightweight", (2022, 2026))
    run.stages = [stage]
    restored = ResearchRun.from_dict(run.to_dict())
    assert restored.to_dict() == run.to_dict()
    assert isinstance(restored.stages[0], StageRun)

    snapshot = SelectedGapSnapshot(
        "gap:1", "Gap", "Plain statement", "explicit", "classification",
        "ensemble", "family", "drift", "accuracy", ("paper:1",),
        ("method:1",), "still unresolved", .8, "now", run.run_id,
    )
    assert SelectedGapSnapshot.from_dict(
        asdict(snapshot)
    ).to_dict() == snapshot.to_dict()


def test_canonical_model_dependency_direction():
    source = (Path(__file__).parents[1] / "run_models.py").read_text()
    forbidden = ("import app", "import streamlit", "import discovery_pipeline")
    assert not any(item in source for item in forbidden)
