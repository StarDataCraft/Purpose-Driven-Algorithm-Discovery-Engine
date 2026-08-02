"""End-to-end direction-to-idea orchestration, independent of Streamlit."""

from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from hashlib import sha1
from pathlib import Path
from typing import Callable

from direction_families import create_direction_families
from external_discovery_pipeline import (
    ExternalDiscoveryResult, SearchPolicy,
    discover_external_mechanisms_for_direction,
)
from models import AlgorithmCandidate, GapSignature, Paper, PurposeContract
from portfolio import quality_diversity_portfolio
from research_memory import ResearchMemory
from run_models import ResearchRun, StageRun, utc_now
from search_engine import search_candidates
from ux_models import DirectionSummary, IdeaDerivation, build_idea_derivation


@dataclass
class IdeaPipelineResult:
    external_result: ExternalDiscoveryResult
    candidates: list[AlgorithmCandidate]
    portfolio: list[AlgorithmCandidate]
    derivations: list[IdeaDerivation]
    direction_families: list[object]
    diagnostics: dict[str, object]


def _capability_diverse_candidates(
    candidates: list[AlgorithmCandidate], purpose: PurposeContract,
    mechanisms: list[object], maximum: int = 6,
) -> list[AlgorithmCandidate]:
    """Expand evidence-supported recurrence mechanisms across distinct roles."""
    purpose_text = f"{purpose.current_failure} {purpose.desired_improvement}".casefold()
    mechanism_text = " ".join(
        f"{getattr(item, 'name', '')} {getattr(item, 'original_problem', '')} "
        f"{getattr(item, 'internal_state', '')} {getattr(item, 'response_rule', '')}"
        for item in mechanisms
    ).casefold()
    if "recurr" not in purpose_text or not any(
        cue in mechanism_text for cue in ("memory", "retain", "reactivat", "recogn")
    ):
        return candidates
    expanded = list(candidates)
    archetypes = (
        (
            "memory", "Bounded prior-state retention",
            "Retain a bounded archive of prior specialist state keyed by an observable regime signature.",
        ),
        (
            "model_selection", "Verified prior-specialist selection",
            "Recognize a recurring regime, select a matching prior specialist, and verify it before reuse.",
        ),
        (
            "routing", "Temporary verified specialist routing",
            "After recurrence verification, temporarily route or weight predictions toward the prior specialist; fall back on failed verification.",
        ),
    )
    for source in candidates:
        for slot, label, action in archetypes:
            if source.affected_component == slot:
                continue
            clone = deepcopy(source)
            clone.candidate_id = "cand:" + sha1(
                f"{source.candidate_id}:{slot}:{action}".encode()
            ).hexdigest()[:12]
            clone.candidate_name = f"{label} for {source.base_algorithm_family}"
            clone.affected_component = slot
            clone.update_rule_delta = action if slot == "model_selection" else ""
            clone.memory_delta = action if slot == "memory" else ""
            clone.routing_delta = action if slot == "routing" else ""
            clone.new_state_variables = list(dict.fromkeys([
                *clone.new_state_variables, "bounded regime signature",
                "prior specialist verification state",
            ]))
            clone.expected_improvement = (
                "reduce recurring-drift recovery time through verified reuse of retained prior state"
            )
            clone.stochastic_trace = {
                **clone.stochastic_trace,
                "operator_plan_archetype": slot,
                "repair_provenance": "required-capability role expansion",
            }
            expanded.append(clone)
            if len(expanded) >= maximum:
                return expanded
    return expanded


def derive_ideas_for_direction(
    *, purpose: PurposeContract, direction: DirectionSummary, gap: GapSignature,
    parent_run: ResearchRun, search_policy: SearchPolicy, seed: int,
    memory_path: Path, fixture_loader: Callable[[], list[Paper]] | None = None,
    adapters: dict[str, Callable[..., list[Paper]]] | None = None,
    progress_callback: Callable[[int, str], None] | None = None,
    cache_directory: Path = Path(".paper_cache"),
) -> IdeaPipelineResult:
    external = discover_external_mechanisms_for_direction(
        purpose=purpose, direction=direction, gap=gap,
        parent_run=parent_run, search_policy=search_policy,
        fixture_loader=fixture_loader, adapters=adapters,
        progress_callback=progress_callback,
        cache_directory=cache_directory,
    )
    if external.errors or not external.accepted_alignments:
        return IdeaPipelineResult(external, [], [], [], [], {
            **external.stage_diagnostics, "status": "failure",
            "failed_stage": (
                "external_retrieval" if not external.papers
                else "mechanism_extraction" if not external.mechanisms
                else "structural_alignment"
            ),
            "errors": external.errors,
        })
    if progress_callback:
        progress_callback(86, "6/6 Building candidate ideas")
    memory = ResearchMemory(memory_path)
    try:
        search = search_candidates(
            purpose, [gap], external.mechanisms, seed,
            purpose.preferred_candidate_scale, 24, memory.failure_penalties(),
        )
    finally:
        memory.close()
    search.candidates = _capability_diverse_candidates(
        search.candidates, purpose, external.mechanisms,
    )
    portfolio = quality_diversity_portfolio(search.candidates, 5)
    accepted_by_mechanism = {
        item.mechanism_id: item for item in external.accepted_alignments
    }
    derivations = []
    for candidate in portfolio:
        mechanism = next((
            item for item in external.mechanisms
            if item.name in candidate.borrowed_mechanisms
            or item.mechanism_id in candidate.borrowed_mechanisms
        ), external.mechanisms[0])
        alignment = accepted_by_mechanism.get(
            mechanism.mechanism_id, external.accepted_alignments[0]
        )
        candidate.research_run_id = parent_run.run_id
        candidate.alignment_id = f"{alignment.gap_id}:{alignment.mechanism_id}"
        candidate.alignment_acceptance = "HARD_VALIDATION_PASSED"
        candidate.selected_gap_snapshot = dict(parent_run.selected_gap_snapshot)
        derivations.append(build_idea_derivation(
            parent_run.run_id, direction, gap, mechanism, alignment, candidate
        ))
    families = create_direction_families(portfolio)
    parent_run.candidate_count = len(portfolio)
    parent_run.stage_records["external_discovery"]["candidate_count"] = len(portfolio)
    parent_run.stages = [
        stage for stage in parent_run.stages
        if stage.stage_name not in {"candidate_synthesis", "portfolio_selection"}
    ]
    parent_run.stages.extend([
        StageRun(
            f"{parent_run.run_id}:candidate_synthesis", "candidate_synthesis",
            parent_run.run_id, utc_now(), completed_at=utc_now(),
            raw_input_count=len(search.candidates) + len(search.rejected_paths),
            output_count=len(search.candidates), accepted_count=len(search.candidates),
            rejected_count=len(search.rejected_paths),
            model_backend="typed_stochastic_search",
        ),
        StageRun(
            f"{parent_run.run_id}:portfolio_selection", "portfolio_selection",
            parent_run.run_id, utc_now(), completed_at=utc_now(),
            raw_input_count=len(search.candidates), output_count=len(portfolio),
            accepted_count=len(portfolio),
            rejected_count=max(0, len(search.candidates) - len(portfolio)),
            model_backend="quality_diversity_portfolio",
        ),
    ])
    return IdeaPipelineResult(external, search.candidates, portfolio, derivations,
                              families, {
        **external.stage_diagnostics,
        "status": "success" if portfolio else "failure",
        "failed_stage": "" if portfolio else "candidate_synthesis",
        "candidate_count": len(portfolio),
        "rejected_candidate_count": len(search.rejected_paths),
    })
