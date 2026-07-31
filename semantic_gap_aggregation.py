"""Semantic aggregation guarded by structural compatibility."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from models import GapSignature


@dataclass
class CanonicalGapFamily:
    member_gap_ids: list[str]
    representative_gap_id: str
    field_consensus: dict[str, str]
    field_disagreements: dict[str, list[str]]
    evidence_count: int
    source_diversity: int
    semantic_cohesion: float
    structural_cohesion: float
    unresolved_variants: list[str]


def structurally_compatible(left: GapSignature, right: GapSignature) -> bool:
    return (
        (left.structural_gap_subtype or left.gap_type) ==
        (right.structural_gap_subtype or right.gap_type)
        and left.affected_component == right.affected_component
        and left.failure_type == right.failure_type
        and left.affected_algorithm_family == right.affected_algorithm_family
    )


def aggregate_semantic_gaps(gaps: list[GapSignature], embeddings: np.ndarray,
                            threshold: float = .82) -> list[CanonicalGapFamily]:
    used = set()
    output = []
    similarities = cosine_similarity(embeddings) if len(gaps) else np.empty((0, 0))
    for i, gap in enumerate(gaps):
        if i in used:
            continue
        members = [i]
        for j in range(i + 1, len(gaps)):
            if j not in used and similarities[i, j] >= threshold and structurally_compatible(gap, gaps[j]):
                members.append(j)
                used.add(j)
        used.add(i)
        member_gaps = [gaps[index] for index in members]
        output.append(CanonicalGapFamily(
            member_gap_ids=[item.gap_id for item in member_gaps],
            representative_gap_id=gap.gap_id,
            field_consensus={
                "failure_type": gap.failure_type,
                "affected_component": gap.affected_component,
                "algorithm_family": gap.affected_algorithm_family,
            },
            field_disagreements={},
            evidence_count=len({p for item in member_gaps for p in item.evidence_paper_ids}),
            source_diversity=len({item.source_diversity for item in member_gaps}),
            semantic_cohesion=round(float(np.mean([
                similarities[a, b] for a in members for b in members
            ])), 3),
            structural_cohesion=1.0,
            unresolved_variants=[item.title for item in member_gaps[1:]],
        ))
    return output
