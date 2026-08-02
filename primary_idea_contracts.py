"""Dependency-neutral, versioned contract for primary-idea selection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence, TYPE_CHECKING

from models import AlgorithmCandidate, GapSignature, Paper, PurposeContract
from run_models import ResearchRun

if TYPE_CHECKING:
    from ux_models import DirectionSummary, IdeaDerivation


PRIMARY_IDEA_SELECTION_API_VERSION = "primary-idea-selection-v2"


@dataclass(frozen=True)
class PrimaryIdeaSelectionRequest:
    api_version: str
    candidates: Sequence[AlgorithmCandidate]
    derivations: Sequence["IdeaDerivation"]
    direction: "DirectionSummary"
    gap: GapSignature
    parent_run: ResearchRun
    automatic_recovery_used: bool = False
    purpose: PurposeContract | None = None
    papers: Sequence[Paper] = ()
    full_audits: Mapping[str, object] = field(default_factory=dict)

    def validate(self) -> None:
        if self.api_version != PRIMARY_IDEA_SELECTION_API_VERSION:
            raise ValueError(
                "Incompatible primary-idea selection request: expected API "
                f"{PRIMARY_IDEA_SELECTION_API_VERSION}, received {self.api_version}."
            )
