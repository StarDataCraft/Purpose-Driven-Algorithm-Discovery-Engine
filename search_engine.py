"""Reproducible stochastic multi-scale search with hard rejection before ranking."""

from __future__ import annotations

import random
from dataclasses import dataclass

from algorithm_library import get_algorithm, load_algorithm_library, weakness_belongs
from alignment import align
from falsification import preflight_rejections
from models import AlgorithmCandidate, GapSignature, MechanismSignature, PurposeContract
from operator_library import compatible_operators
from scoring import score_candidate
from synthesis import synthesize_candidate


@dataclass
class SearchResult:
    candidates: list[AlgorithmCandidate]
    rejected_paths: list[dict[str, object]]


def _mechanism_groups(mechanisms: list[MechanismSignature], scale: str,
                      rng: random.Random) -> list[list[MechanismSignature]]:
    shuffled = list(mechanisms)
    rng.shuffle(shuffled)
    if scale == "small":
        return [[mechanism] for mechanism in shuffled]
    if scale == "medium":
        pairs = []
        for left in shuffled:
            right = next((item for item in shuffled
                          if item.source_domain != left.source_domain
                          and not set(item.compatible_slots).isdisjoint(left.compatible_slots)), None)
            if right:
                pairs.append([left, right])
        return pairs or [[mechanism] for mechanism in shuffled]
    groups = []
    ecology = [item for item in shuffled if item.source_domain in ("ecology", "biology")]
    for mechanism in ecology:
        complements = [item for item in shuffled if item.source_domain != mechanism.source_domain][:2]
        groups.append([mechanism, *complements])
    return groups or [[mechanism] for mechanism in shuffled]


def search_candidates(purpose: PurposeContract | None, gaps: list[GapSignature],
                      mechanisms: list[MechanismSignature], seed: int = 42,
                      scale: str = "small", limit: int = 20,
                      failure_penalties: dict[str, float] | None = None) -> SearchResult:
    if purpose is None:
        raise ValueError("A PurposeContract is required")
    if not gaps:
        raise ValueError("A selected gap is required")
    if not purpose.primary_metric:
        raise ValueError("An evaluation metric is required")
    if not purpose.available_inference_information:
        raise ValueError("Available inference information must be defined")
    rng = random.Random(seed)
    failure_penalties = failure_penalties or {}
    library = load_algorithm_library()
    candidates, rejected = [], []
    for gap in gaps:
        try:
            algorithm = get_algorithm(gap.affected_algorithm, library)
        except KeyError:
            options = [item for item in library.values()
                       if item.family == gap.affected_algorithm_family
                       or gap.task in item.tasks]
            if not options:
                rejected.append({"gap": gap.gap_id, "reasons": ["no affected algorithm"]})
                continue
            algorithm = rng.choice(options)
        if not weakness_belongs(algorithm, gap.failure_type, gap) and not any(
            failure in gap.failure_type.casefold()
            for failure in (value.casefold() for value in algorithm.known_failure_conditions)
        ):
            rejected.append({"gap": gap.gap_id, "algorithm": algorithm.name,
                             "reasons": ["weakness is not bound to selected algorithm"]})
            continue
        for group in _mechanism_groups(mechanisms, scale, rng):
            primary = group[0]
            alignment = align(gap, primary, purpose)
            operators = compatible_operators(gap.affected_component)
            if not operators:
                rejected.append({"gap": gap.gap_id, "mechanism": primary.name,
                                 "reasons": ["no compatible operator"]})
                continue
            rng.shuffle(operators)
            reasons = list(alignment.rejection_reasons)
            viable = [
                operator for operator in operators
                if not preflight_rejections(purpose, gap, primary, operator)
            ]
            if not viable:
                reasons.extend(preflight_rejections(purpose, gap, primary, operators[0]))
                chosen = operators[:1]
            else:
                chosen = viable[:1 if scale == "small" else min(2, len(viable))]
            if reasons:
                rejected.append({"gap": gap.gap_id, "mechanism": primary.name,
                                 "operator": chosen[0].name, "reasons": sorted(set(reasons))})
                continue
            path_fingerprint = "|".join((gap.gap_id, primary.name, chosen[0].name))
            learned_penalty = failure_penalties.get(path_fingerprint, 0.0)
            if learned_penalty >= .5:
                rejected.append({"gap": gap.gap_id, "mechanism": primary.name,
                                 "operator": chosen[0].name,
                                 "reasons": ["repeatedly rejected by research memory"]})
                continue
            complexity = {"small": .02, "medium": .10, "large": .22}[scale]
            scores = score_candidate(
                gap, alignment, purpose_fit=.9, feasibility=.85 - complexity,
                testability=gap.testability_score, novelty=.65,
                diversity=.6, complexity_penalty=complexity,
                duplication_penalty=learned_penalty,
            )
            trace = {
                "seed": seed, "search_scale": scale,
                "sampled_structural_path": [gap.gap_id, algorithm.name,
                                            *[m.mechanism_id for m in group],
                                            *[o.operator_id for o in chosen]],
                "mutation_steps": ["weighted mechanism order", "compatible operator sampling"],
                "selected_nodes": [algorithm.name, *[m.name for m in group], *[o.name for o in chosen]],
                "compatibility_checks": alignment.field_scores,
            }
            candidates.append(synthesize_candidate(
                purpose, gap, algorithm, group, chosen, alignment, scores, trace
            ))
    candidates.sort(key=lambda candidate: (-candidate.scores.total, candidate.candidate_id))
    return SearchResult(candidates[:limit], rejected)
