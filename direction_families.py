"""Group candidates into interpretable research direction families."""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha1

from models import AlgorithmCandidate, DirectionFamily


def create_direction_families(candidates: list[AlgorithmCandidate]) -> list[DirectionFamily]:
    groups: dict[tuple[str, str], list[AlgorithmCandidate]] = defaultdict(list)
    for candidate in candidates:
        key = (candidate.affected_component, candidate.borrowed_mechanisms[0])
        groups[key].append(candidate)
    output = []
    for (slot, mechanism), items in groups.items():
        name = f"{mechanism.title()} for {slot.replace('_', ' ')}"
        identifier = sha1(name.encode()).hexdigest()[:10]
        family = DirectionFamily(
            family_id=f"family:{identifier}", name=name,
            origin_gap_ids=sorted({item.gap_id for item in items}),
            source_domains=sorted({d for item in items for d in item.source_domains}),
            mechanism_ids=sorted({m for item in items for m in item.borrowed_mechanisms}),
            target_tasks=sorted({item.minimal_experiment.target_task for item in items}),
            affected_algorithm_families=sorted({item.base_algorithm_family for item in items}),
            modification_slots=[slot],
            common_operators=sorted({o for item in items for o in item.selected_operators}),
            intended_applications=sorted({item.minimal_experiment.application_context for item in items}),
            expected_benefits=sorted({item.expected_improvement for item in items}),
            trade_offs=sorted({trade for item in items for trade in item.trade_offs}),
            candidate_ids=[item.candidate_id for item in items],
            risk_level="high" if len(items[0].borrowed_mechanisms) > 2 else
                       "medium" if len(items[0].borrowed_mechanisms) == 2 else "low",
            evidence_strength=round(sum(item.scores.components["gap_confidence"] for item in items) / len(items), 2),
            novelty_status="requires literature validation",
            best_first_experiment=items[0].minimal_experiment.hypothesis,
        )
        for item in items:
            item.direction_family = family.family_id
        output.append(family)
    return output
