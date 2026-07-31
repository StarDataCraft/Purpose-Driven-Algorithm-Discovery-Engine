"""Optional citation-neighborhood evidence; never required for core discovery."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CitationEvidence:
    seed_paper_id: str
    neighbor_ids: tuple[str, ...]
    corroborating_ids: tuple[str, ...]
    enabled: bool
    status: str


def citation_evidence(
    seed_paper_id: str, references: list[str] | None = None,
    corroborating_ids: list[str] | None = None,
) -> CitationEvidence:
    references = references or []
    corroborating_ids = corroborating_ids or []
    return CitationEvidence(
        seed_paper_id, tuple(dict.fromkeys(references)),
        tuple(dict.fromkeys(corroborating_ids)), bool(references),
        "AVAILABLE" if references else "NOT_REQUESTED_OR_UNAVAILABLE",
    )
