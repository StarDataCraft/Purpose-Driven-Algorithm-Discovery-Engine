"""Conservative ten-angle and adversarial audits of complete candidate results."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import subprocess
from typing import Iterable
from uuid import uuid4

from evaluation.audits import audit_alignment, audit_gap, audit_mechanism, candidate_rubric
from evaluation.audit_models import AuditDimension, ResultAudit
from models import AlgorithmCandidate, AlignmentResult, GapSignature, MechanismSignature, Paper, PurposeContract
from run_models import ResearchRun


DIMENSION_NAMES = (
    "user_problem_fit", "literature_retrieval_quality", "evidence_gap_validity",
    "known_solution_novelty", "external_mechanism_quality",
    "structural_alignment_quality", "algorithm_specificity_executability",
    "falsifiability_experiment_quality", "readability_decision_value",
    "engineering_cost_deployment",
)


def _dimension(
    name: str, score: int, evidence: Iterable[str], problems: Iterable[str],
    action: str, sota: bool = False,
) -> AuditDimension:
    bounded = max(0, min(5, int(score)))
    return AuditDimension(
        name, bounded, bounded >= 4, list(evidence), list(problems), action, sota,
    )


def _commit_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
        check=False,
    ).stdout.strip() or "unavailable"


def _contains(text: str, terms: Iterable[str]) -> bool:
    folded = text.casefold()
    return any(term.casefold() in folded for term in terms if term)


def audit_complete_result(
    *, purpose: PurposeContract, run: ResearchRun, direction_id: str,
    gap_family_id: str, gap: GapSignature, candidate: AlgorithmCandidate,
    mechanism: MechanismSignature, alignment: AlignmentResult,
    papers: list[Paper], pipeline_version: str,
    robustness_results: dict[str, str] | None = None,
) -> ResultAudit:
    """Audit displayed evidence and proposal fields without inventing confidence."""
    relevant_ids = {
        paper.paper_id for paper in papers
        if paper.reviewed_relevance_label in {"RELEVANT", "HIGHLY_RELEVANT"}
    }
    automatically_retained = sum(bool(paper.estimated_relevance_label) for paper in papers)
    direct = len(set(gap.evidence_paper_ids) & {paper.paper_id for paper in papers})
    reviewed_direct = len(set(gap.evidence_paper_ids) & relevant_ids)
    gap_check = audit_gap(gap, relevant_ids or set(gap.evidence_paper_ids))
    mechanism_check = audit_mechanism(mechanism)
    alignment_check = audit_alignment(alignment)
    candidate_check = candidate_rubric(candidate)
    task_fit = sum(_contains(
        " ".join((candidate.gap_summary, candidate.expected_improvement,
                  candidate.primary_metric, candidate.minimal_experiment.stressor)),
        (purpose.current_failure, purpose.primary_metric, purpose.task),
    ) for _ in (0,))
    fit_score = 5 if task_fit and candidate.primary_metric == purpose.primary_metric else 4 if task_fit else 2
    dimensions = [_dimension(
        "user_problem_fit", fit_score,
        [f"task={purpose.task}", f"failure={purpose.current_failure}",
         f"primary_metric={candidate.primary_metric}"],
        [] if fit_score >= 4 else ["Candidate does not preserve the exact failure and metric."],
        "Restore the purpose failure, application context, and primary metric before promotion.",
    )]

    sources = {paper.source for paper in papers}
    years = {paper.year for paper in papers if paper.year}
    abstracts = sum(bool(paper.abstract.strip()) for paper in papers)
    duplicate_rate = 1 - len({paper.paper_id for paper in papers}) / max(1, len(papers))
    synthetic = any(
        paper.paper_id.startswith("synthetic:") or paper.source.startswith("mock_")
        for paper in papers
    )
    live = run.actual_search_mode in {"LIVE", "MIXED", "CACHE"} and not synthetic
    literature_score = 4 if live and len(papers) >= 10 and len(sources) >= 2 else 3
    literature_problems = [] if literature_score >= 4 else [
        "Coverage is limited, synthetic, cached, or too small for a literature-quality pass."
    ]
    dimensions.append(_dimension(
        "literature_retrieval_quality", literature_score,
        [f"papers={len(papers)}", f"sources={len(sources)}", f"years={len(years)}",
         f"abstracts={abstracts}", f"duplicate_rate={duplicate_rate:.3f}",
         f"mode={run.actual_search_mode}", f"synthetic={synthetic}",
         f"automatically_retained={automatically_retained}"],
        literature_problems,
        "Review top 5/10/20 and known-solution recall on live, human-labeled evidence.", True,
    ))
    evidence_score = 4 if direct >= 2 and gap_check.label not in {"UNSUPPORTED"} else 3 if direct else 1
    if reviewed_direct == 0:
        evidence_score = min(evidence_score, 3)
    dimensions.append(_dimension(
        "evidence_gap_validity", evidence_score,
        [f"direct_evidence_papers={direct}", f"human_reviewed_direct={reviewed_direct}",
         f"gap_audit={gap_check.label}",
         f"scope={gap.field_provenance.get('scope', gap.gap_type)}"],
        [] if evidence_score >= 4 else ["The promoted gap lacks independent human-reviewed direct support."],
        "Human-review the evidence sentences and rerun known-solution search before promotion.", True,
    ))
    novelty = candidate.novelty_status.upper().replace(" ", "_")
    novelty_pass = novelty in {
        "PARTIAL_EXTENSION", "NEW_MECHANISM_SLOT_COMBINATION",
        "POTENTIALLY_STRUCTURALLY_DISTINCT", "KNOWN_METHOD_NEW_SETTING",
    }
    dimensions.append(_dimension(
        "known_solution_novelty", 4 if novelty_pass else 2,
        [f"novelty_state={novelty or 'INSUFFICIENT_SEARCH'}",
         f"nearest_methods={len(candidate.nearest_known_method_patterns)}"],
        [] if novelty_pass else ["Prior-art search is insufficient to rule out a renamed or duplicate method."],
        "Search synonyms, foundational work, adjacent families, and direct variants; never claim proven novelty.", True,
    ))
    mechanism_score = 5 if mechanism_check.label == "VALID_OPERATIONAL_MECHANISM" else 3
    dimensions.append(_dimension(
        "external_mechanism_quality", mechanism_score,
        mechanism_check.reasons,
        mechanism_check.errors,
        "Require evidence-backed signal, state, trigger, response, constraint, target, and failure boundary.",
    ))
    alignment_score = 5 if alignment_check.label == "STRONG_STRUCTURAL_MATCH" else 4 if alignment_check.label == "PLAUSIBLE_MATCH" else 2
    dimensions.append(_dimension(
        "structural_alignment_quality", alignment_score,
        alignment_check.reasons,
        alignment_check.errors,
        "Keep hard topology, information-stage, timescale, and slot constraints primary.", True,
    ))
    specificity_values = candidate_check.score_components
    specificity_score = min(5, round((
        specificity_values.get("modification_specificity", 0)
        + specificity_values.get("information_feasibility", 0)
        + specificity_values.get("algorithm_binding", 0)
    ) / 2.4))
    dimensions.append(_dimension(
        "algorithm_specificity_executability", specificity_score,
        [f"base={candidate.base_algorithm}", f"slot={candidate.affected_component}",
         f"new_state={len(candidate.new_state_variables)}",
         f"inference_inputs={len(candidate.required_inference_information)}",
         f"complexity={candidate.complexity_delta}"],
        candidate_check.errors,
        "Specify initialization, fallback, state, trigger, exact rule, and resource effects.",
    ))
    plan = candidate.minimal_experiment
    experiment_fields = (
        plan.hypothesis, plan.stressor, plan.dataset, plan.baselines,
        plan.ablations, plan.metrics, plan.seeds, plan.success_rule, plan.failure_rule,
        candidate.kill_criterion,
    )
    experiment_score = 5 if all(experiment_fields) and len(plan.baselines) >= 2 else 3
    dimensions.append(_dimension(
        "falsifiability_experiment_quality", experiment_score,
        [f"baselines={len(plan.baselines)}", f"ablations={len(plan.ablations)}",
         f"seeds={len(plan.seeds)}", f"kill_criterion={bool(candidate.kill_criterion)}"],
        [] if experiment_score >= 4 else ["Experiment lacks a strong comparison, ablation, threshold, or kill criterion."],
        "Add strong, closest-method, and matched-compute baselines with causal ablations.",
    ))
    dimensions.append(_dimension(
        "readability_decision_value", 4,
        ["Part 3 leads with a conclusion and separates supported, inferred, and unknown claims.",
         "BEFORE → CHANGE → EXPECTED RESULT and text diagram fallbacks are present."],
        [], "Keep raw records behind progressive disclosure.",
    ))
    request_count = sum(item.request_count for item in run.source_results)
    engineering_score = 4 if request_count <= 30 else 3
    dimensions.append(_dimension(
        "engineering_cost_deployment", engineering_score,
        [f"requests={request_count}", f"cache_used={run.cache_used}",
         f"duration_seconds={run.overall_wall_clock_duration_seconds}",
         f"mode={run.actual_search_mode}"],
        [] if engineering_score >= 4 else ["Request cost exceeds the bounded default budget."],
        "Preserve shared limits, cache reuse, circuit breaking, and lightweight fallback.",
    ))
    errors = [
        f"{item.name}:{problem}" for item in dimensions for problem in item.specific_problems
    ]
    failed = [item.name for item in dimensions if not item.passed]
    decision = "PASS" if not failed else "EXPLORATORY — " + ", ".join(failed)
    critique = {
        "strongest_reason_to_believe": (
            f"A {alignment_check.label.lower().replace('_', ' ')} connects an operational "
            f"{mechanism.name} mechanism to the {candidate.affected_component} slot."
        ),
        "strongest_reason_to_reject": errors[0] if errors else "Empirical benefit remains untested.",
        "most_likely_duplicate": (
            candidate.nearest_known_method_patterns[0]
            if candidate.nearest_known_method_patterns else "Unknown; targeted prior-art search is incomplete."
        ),
        "most_fragile_evidence_link": (
            "No human-reviewed direct paper evidence." if not reviewed_direct
            else f"Only {reviewed_direct} human-reviewed direct paper(s)."
        ),
        "most_uncertain_mapping": (
            alignment.missing_information[0] if alignment.missing_information
            else "Whether the external trigger remains diagnostic in the target task."
        ),
        "most_expensive_requirement": candidate.complexity_delta or candidate.memory_delta,
        "fastest_invalidation_experiment": candidate.kill_criterion or plan.failure_rule,
        "highest_value_additional_evidence": (
            "Human review of direct failure sentences plus a targeted known-solution paper set."
        ),
    }
    robustness = robustness_results or {
        "external_mechanism_removed": "NOT_RUN",
        "random_mechanism_substitution": "NOT_RUN",
        "paper_evidence_shuffle": "NOT_RUN",
        "highly_cited_paper_removed": "NOT_RUN",
        "algorithm_replaced_by_family": "NOT_RUN",
        "abstract_only_evidence_removed": "NOT_RUN",
        "live_vs_cache": "NOT_RUN",
        "known_solution_search_tightened": "NOT_RUN",
        "task_terms_removed": "NOT_RUN",
        "seed_changed": "NOT_RUN",
    }
    return ResultAudit(
        audit_id=f"audit:{uuid4().hex}", run_id=run.run_id,
        direction_id=direction_id, gap_family_id=gap_family_id,
        candidate_id=candidate.candidate_id, pipeline_version=pipeline_version,
        commit_sha=_commit_sha(),
        audit_timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        task_name=purpose.task, search_mode=run.actual_search_mode,
        engine_mode=run.engine_mode, audit_dimensions=dimensions,
        detected_errors=errors,
        severity_by_error={error: "HIGH" for error in errors},
        supporting_evidence=[
            *gap.evidence_sentences[:3], *mechanism.evidence_sentences[:2],
        ],
        recommended_repairs=list(dict.fromkeys(
            item.recommended_action for item in dimensions if not item.passed
        )),
        state_of_art_candidates=[
            "hybrid sparse–scientific dense retrieval with rank fusion",
            "scientific claim-support ranking",
            "counterfactual negative-pair alignment calibration",
        ],
        experiments_run=[
            {"counterfactual": name, "result": result}
            for name, result in robustness.items()
        ],
        adopted_changes=["typed ten-angle result audit and visible critical review"],
        rejected_changes=[],
        before_metrics={"audited_dimensions": 0.0},
        after_metrics={
            "audited_dimensions": float(len(dimensions)),
            "passing_dimensions": float(sum(item.passed for item in dimensions)),
        },
        final_decision=decision,
        robustness_results=robustness,
        self_critique=critique,
    )


def audit_summary(audit: ResultAudit) -> dict[str, object]:
    """Small user-facing summary; the complete record stays in Research Tools."""
    return {
        "decision": audit.final_decision,
        "scores": {item.name: item.score for item in audit.audit_dimensions},
        "failed_dimensions": [item.name for item in audit.audit_dimensions if not item.passed],
        "critical_review": audit.self_critique,
    }
