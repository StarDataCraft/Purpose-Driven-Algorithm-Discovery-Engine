"""Linux/cloud-equivalent startup contract for the lightweight application."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from run_models import ResearchRun, SelectedGapSnapshot, StageRun
from search_runs import ResearchRun as SearchExportedResearchRun
from research_runs import ResearchRun as LegacyExportedResearchRun
from streamlit.testing.v1 import AppTest


def main() -> None:
    assert SearchExportedResearchRun is ResearchRun
    assert LegacyExportedResearchRun is ResearchRun
    app_spec = importlib.util.find_spec("app")
    run_spec = importlib.util.find_spec("run_models")
    search_spec = importlib.util.find_spec("search_runs")
    print("app module:", app_spec.origin if app_spec else None)
    print("canonical run models:", run_spec.origin if run_spec else None)
    print("search_runs compatibility module:", search_spec.origin if search_spec else None)
    import app  # noqa: F401

    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    if at.exception:
        raise RuntimeError(f"Streamlit startup exceptions: {at.exception}")
    assert at.title and at.title[0].value == "Discover directions / 发现方向"
    assert len(at.sidebar.radio(key="_primary_step").options) == 3
    print("deployment smoke test: OK")


if __name__ == "__main__":
    main()
