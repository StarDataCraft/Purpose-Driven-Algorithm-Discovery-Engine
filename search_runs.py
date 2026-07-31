"""Compatibility alias for an early deployment import spelling.

New code must import the canonical definitions from :mod:`run_models`.
"""

from run_models import (
    ACTUAL_SEARCH_MODES,
    QualityWarning,
    ResearchRun,
    SelectedGapSnapshot,
    SourceRetrievalResult,
    StageRun,
    paper_provenance,
    utc_now,
)

__all__ = [
    "ACTUAL_SEARCH_MODES",
    "QualityWarning",
    "ResearchRun",
    "SelectedGapSnapshot",
    "SourceRetrievalResult",
    "StageRun",
    "paper_provenance",
    "utc_now",
]
