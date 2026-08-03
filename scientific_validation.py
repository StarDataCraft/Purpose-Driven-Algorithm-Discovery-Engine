"""Pre-promotion scientific validity, evidence-role, and implementation gates."""

from __future__ import annotations

from collections import Counter
import re
from typing import Sequence

from idea_maturity import (
    AssessmentIssue, AssessmentSeverity, CapabilityOperatorPlan,
    IdeaMaturityLevel, OpenDesignChoice, RepairRecord, ScientificAssessment,
    issue, maturity_value,
)

from models import (
    AlgorithmCandidate, AlgorithmModificationSpec, GapSignature, Paper,
    PaperEvidenceRole, PurposeContract,
)
from ux_models import DirectionSummary, IdeaDerivation, candidate_modification


DIRECT_FAILURE_EVIDENCE = "DIRECT_FAILURE_EVIDENCE"
CONTEXTUAL_BACKGROUND = "CONTEXTUAL_BACKGROUND"
EXTERNAL_MECHANISM_EVIDENCE = "EXTERNAL_MECHANISM_EVIDENCE"
CURRENT_SOLUTION_EVIDENCE = "CURRENT_SOLUTION_EVIDENCE"
TRANSFER_EVIDENCE = "TRANSFER_EVIDENCE"
IMPLEMENTATION_EVIDENCE = "IMPLEMENTATION_EVIDENCE"
EXPERIMENT_EVIDENCE = "EXPERIMENT_EVIDENCE"
IRRELEVANT = "IRRELEVANT"


def _tokens(value: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]+", value.casefold())
        if len(token) > 2 and token not in {"with", "from", "under", "using", "that", "this"}
    }


def _failure_semantic_match(text_value: str, failure_value: str) -> bool:
    """Controlled scientific variants after hard task compatibility."""
    text = text_value.casefold()
    failure = failure_value.casefold()
    recurring = any(term in failure for term in ("recurr", "recurrent", "repeat"))
    slow_recovery = any(term in failure for term in ("recover", "adaptation", "reuse"))
    if slow_recovery and not any(term in text for term in (
        "recovery", "recover", "reuse", "reactivation", "relearn", "adaptation time",
    )):
        return False
    if recurring and any(term in text for term in (
        "recurring concept", "recurrent drift", "concept recurrence",
        "recurring regime", "repeated context", "model reuse after drift",
        "recovery following recurrence",
    )):
        return not slow_recovery or any(term in text for term in (
            "recovery", "reuse", "reactivation", "adaptation", "relearn",
        ))
    return len(_tokens(text) & _tokens(failure)) >= 2


def classify_paper_roles(
    papers: Sequence[Paper], purpose: PurposeContract, gap: GapSignature,
    candidate: AlgorithmCandidate,
) -> list[PaperEvidenceRole]:
    """Assign one conservative role; canonical-family proximity is never direct."""
    task_terms = _tokens(f"{purpose.task} {purpose.data_type}")
    purpose_text = f"{purpose.task} {purpose.data_type}".casefold()
    if any(term in purpose_text for term in ("online", "stream")):
        task_terms.update({"online", "stream", "streaming", "ensemble", "forest", "drift"})
    if "classif" in purpose_text:
        task_terms.update({"classification", "classifier", "predictor", "tabular"})
    if "cluster" in purpose_text:
        task_terms.update({"cluster", "clustering", "centroid", "density"})
    failure_terms = _tokens(f"{purpose.current_failure} {gap.failure_type}")
    mechanism_terms = _tokens(" ".join(candidate.borrowed_mechanisms))
    direct_ids = set(gap.evidence_paper_ids)
    candidate_ids = set(candidate.evidence_paper_ids)
    records = []
    for paper in papers:
        text = _tokens(f"{paper.title} {paper.abstract}")
        task_match = bool(text & task_terms)
        failure_match = _failure_semantic_match(
            f"{paper.title} {paper.abstract}", f"{purpose.current_failure} {gap.failure_type}"
        )
        reviewed = paper.reviewed_relevance_label or "NOT_REVIEWED"
        estimated = (paper.estimated_relevance_label or "unknown").upper()
        estimated_irrelevant = estimated in {"IRRELEVANT", "ESTIMATED_IRRELEVANT"}
        if paper.paper_id in direct_ids and task_match and failure_match and not estimated_irrelevant:
            role = DIRECT_FAILURE_EVIDENCE
            claim = f"Directly states evidence about {gap.failure_type}."
            reason = "Gap provenance plus hard task/failure compatibility."
        elif paper.paper_id in candidate_ids and bool(text & mechanism_terms) and not estimated_irrelevant:
            role = EXTERNAL_MECHANISM_EVIDENCE
            claim = "Supports the external mechanism, not the ML failure claim."
            reason = "Candidate mechanism evidence with no direct-gap promotion."
        elif task_match and not estimated_irrelevant:
            role = CONTEXTUAL_BACKGROUND
            claim = "Provides task context only."
            reason = "Task overlap without a direct failure-evidence path."
        else:
            role = IRRELEVANT
            claim = "No candidate claim is supported."
            reason = "Fails hard task/failure relevance or is estimated irrelevant."
        records.append(PaperEvidenceRole(
            paper.paper_id, role, estimated, reviewed, claim,
            (paper.abstract or paper.title)[:400], reason,
        ))
    return records


def evidence_count_invariants(roles: Sequence[PaperEvidenceRole]) -> dict[str, int]:
    candidate_count = len(roles)
    automatically_relevant = sum(item.role != IRRELEVANT for item in roles)
    evidence_bearing = sum(item.role in {
        DIRECT_FAILURE_EVIDENCE, EXTERNAL_MECHANISM_EVIDENCE,
    } for item in roles)
    direct = sum(item.role == DIRECT_FAILURE_EVIDENCE for item in roles)
    assert direct <= evidence_bearing <= automatically_relevant <= candidate_count
    return {
        "direct_support_count": direct,
        "evidence_bearing_paper_count": evidence_bearing,
        "automatically_relevant_paper_count": automatically_relevant,
        "candidate_paper_count": candidate_count,
    }


def build_modification_spec(
    candidate: AlgorithmCandidate, derivation: IdeaDerivation,
) -> AlgorithmModificationSpec:
    rule = candidate_modification(candidate)
    definitions = {
        name: f"Candidate-defined state variable: {name.replace('_', ' ')}"
        for name in candidate.new_state_variables if name.strip()
    }
    symbols = set(re.findall(r"\b[A-Za-z][A-Za-z0-9_]*\b", rule))
    mathematical = bool(re.search(r"=|\[[^]]+\]|\b[A-Za-z]\w*\s*[+*/]\s*[A-Za-z]\w*", rule))
    common = {"t", "if", "then", "and", "or", "using", "update", "rule"}
    unresolved = []
    if mathematical:
        unresolved.extend(
            f"undefined symbol: {symbol}" for symbol in sorted(symbols - set(definitions) - common)
        )
    action = next((value for value in (
        candidate.aggregation_delta, candidate.routing_delta,
        candidate.memory_delta, candidate.component_lifecycle_delta,
        candidate.inference_delta,
    ) if value.strip()), "")
    if not action and not re.search(r"[=\[\]]", rule) and len(rule.split()) >= 4:
        action = rule
    delayed = [item for item in candidate.required_inference_information
               if any(term in item.casefold() for term in ("label", "residual", "error feedback"))]
    return AlgorithmModificationSpec(
        candidate.base_algorithm_family, candidate.base_algorithm,
        derivation.modification_slot, [f"existing {derivation.modification_slot} state"],
        list(candidate.new_state_variables), definitions,
        derivation.mechanism_trigger, rule, action,
        candidate.initialization_delta, "retain the base algorithm update",
        list(candidate.required_training_information),
        [item for item in candidate.required_inference_information if item not in delayed],
        delayed, candidate.complexity_delta, candidate.memory_delta,
        list(candidate.must_not_degrade), unresolved,
    )


ScientificGateResult = ScientificAssessment


def _limiter(description: str, why: str, resolution: str,
             severity: str = "MAJOR_LIMITER") -> AssessmentIssue:
    return issue(
        re.sub(r"[^a-z0-9]+", "_", description.casefold()).strip("_")[:80],
        AssessmentSeverity(severity), description,
        consequence=why, repair_option=resolution,
    )


def _audit_severity(name: str, problems: str) -> AssessmentSeverity:
    text = f"{name} {problems}".casefold()
    if any(term in text for term in (
        "wrong task", "task mismatch", "metaphor-only", "unavailable information",
        "required inference", "provenance mismatch",
    )):
        return AssessmentSeverity.FATAL
    if any(term in text for term in ("evidence", "novelty", "structural_alignment")):
        return AssessmentSeverity.MAJOR_LIMITER
    return AssessmentSeverity.MINOR_LIMITER


def build_capability_operator_plan(
    candidate: AlgorithmCandidate, derivation: IdeaDerivation,
    purpose: PurposeContract | None = None,
) -> CapabilityOperatorPlan:
    """Expand a purpose capability into explicit compatible operator roles."""
    capability = derivation.required_capability.strip()
    text = (
        f"{capability} {derivation.problem_statement} {candidate.gap_summary} "
        f"{candidate.expected_improvement} {getattr(purpose, 'current_failure', '')}"
    ).casefold()
    recurring = any(term in text for term in ("recurr", "prior specialist", "historical"))
    if recurring:
        required_roles = (
            "recognize recurring regime", "retain prior specialist state",
            "select matching specialist", "verify recurrence match",
            "route or weight predictions", "fallback after failed verification",
        )
        candidates = (
            "regime_recognition", "bounded_memory", "model_selection",
            "verification", "routing", "aggregation_weights", "expert_lifecycle",
        )
        role_to_slot = {
            required_roles[0]: "regime_recognition",
            required_roles[1]: "bounded_memory",
            required_roles[2]: "model_selection",
            required_roles[3]: "verification",
            required_roles[4]: "routing+aggregation_weights",
            required_roles[5]: "routing_fallback",
        }
    else:
        required_roles = (
            "detect target condition", "retain required state", "apply algorithm action",
            "verify response", "fallback safely",
        )
        candidates = tuple(dict.fromkeys((
            candidate.affected_component, derivation.modification_slot,
            "state_estimation", "verification", "fallback",
        )))
        role_to_slot = dict(zip(required_roles, candidates[:len(required_roles)]))
    mechanism_text = " ".join((
        derivation.mechanism_name, derivation.original_external_problem,
        derivation.mechanism_signal, derivation.mechanism_state,
        derivation.mechanism_trigger, derivation.mechanism_response,
        candidate_modification(candidate), *derivation.structural_correspondences,
        *candidate.borrowed_mechanisms, *candidate.new_state_variables,
    )).casefold()
    cues = {
        "recognize recurring regime": ("recurr", "recogn", "regime", "match"),
        "retain prior specialist state": ("prior", "memory", "retain", "archive", "state"),
        "select matching specialist": ("select", "specialist", "expert", "model"),
        "verify recurrence match": ("verify", "confidence", "window", "test"),
        "route or weight predictions": ("route", "weight", "aggregation", "expert"),
        "fallback after failed verification": ("fallback", "base", "reject", "fail"),
    }
    covered = tuple(role for role in required_roles
                    if any(cue in mechanism_text for cue in cues.get(role, tuple(role.split()))))
    engineering = tuple(role for role in required_roles if role not in covered and role in {
        "verify recurrence match", "fallback after failed verification", "verify response", "fallback safely",
    })
    missing = tuple(role for role in required_roles if role not in covered and role not in engineering)
    selected = tuple(dict.fromkeys(role_to_slot[role] for role in required_roles
                                   if role in role_to_slot and role not in missing))
    choices = tuple(OpenDesignChoice(
        name=role, role="capability/operator role", possible_options=(role_to_slot.get(role, "operator"),),
        current_default="not fixed", information_needed="Evidence or an ablation identifying the compatible operator.",
        resolving_experiment="Disable this role and measure whether the claimed causal path survives.",
        effect_if_chosen_incorrectly="The capability path becomes incomplete.",
    ) for role in missing)
    fatal = ()
    if not selected or not any(slot not in {"update_rule", ""} for slot in selected):
        fatal = ("required capability collapses to a generic update rule",)
    return CapabilityOperatorPlan(
        capability, required_roles, candidate.base_algorithm_family, candidates,
        selected, role_to_slot, missing,
        round((len(required_roles) - len(missing)) / max(1, len(required_roles)), 3),
        fatal, choices, covered, engineering,
        ("Structural role coverage is inferred and requires discriminating ablation.",),
    )


def _open_choices(spec: AlgorithmModificationSpec) -> tuple[OpenDesignChoice, ...]:
    choices = []
    for unresolved in spec.unresolved_implementation_choices:
        choices.append(OpenDesignChoice(
            name=unresolved.replace("undefined symbol: ", "Define "),
            role="implementation parameter or state definition",
            possible_options=("derive from evidence", "tune on validation stream", "ablate"),
            current_default="not fixed",
            information_needed="A concrete operator specification and timing audit.",
            resolving_experiment="Run a bounded sensitivity analysis against a no-state baseline.",
            effect_if_chosen_incorrectly="The mechanism may become unstable or lose its causal advantage.",
        ))
    return tuple(choices)


def validate_candidate_for_promotion(
    *, candidate: AlgorithmCandidate, derivation: IdeaDerivation,
    direction: DirectionSummary, gap: GapSignature, purpose: PurposeContract,
    papers: Sequence[Paper], full_audit: object | None = None,
) -> ScientificAssessment:
    roles = classify_paper_roles(papers, purpose, gap, candidate)
    counts = evidence_count_invariants(roles)
    spec = build_modification_spec(candidate, derivation)
    capability_plan = build_capability_operator_plan(candidate, derivation, purpose)
    fatal_failures: list[str] = []
    limiters: list[AssessmentIssue] = []
    strengths: list[str] = []
    repairs: list[RepairRecord] = []
    combined = " ".join((candidate.gap_summary, candidate.expected_improvement,
                         candidate.primary_metric, direction.failure_condition)).casefold()
    if purpose.current_failure.casefold() not in combined and gap.failure_type.casefold() not in combined:
        fatal_failures.append("problem fit: target failure condition is not addressed")
    else:
        strengths.append("The candidate addresses the normalized user failure.")
    if candidate.primary_metric.casefold() != purpose.primary_metric.casefold():
        fatal_failures.append("problem fit: target metric changed")
    if counts["direct_support_count"] < 1:
        limiters.append(_limiter(
            "evidence validity: no directly relevant problem-evidence paper",
            "Research-worthy promotion requires direct evidence that the target failure exists.",
            "Retrieve and review a task-compatible paper describing the operating condition and failure.",
        ))
    else:
        strengths.append("At least one task-compatible paper directly supports the target problem.")
    novelty = candidate.novelty_status.upper().replace(" ", "_")
    if novelty in {"LIKELY_DUPLICATE", "KNOWN_METHOD_RENAMED"}:
        fatal_failures.append("known-solution validation: known duplicate with no meaningful difference")
    elif novelty in {"", "INSUFFICIENT_SEARCH", "INSUFFICIENT_EVIDENCE"}:
        limiters.append(_limiter(
            "known-solution validation: targeted prior-art coverage is incomplete",
            "The mechanism-slot combination cannot yet support a strong novelty claim.",
            "Search problem solutions, exact slot, mechanism-slot combination, and cross-task analogues.",
        ))
    if not all((derivation.mechanism_signal, derivation.mechanism_state,
                derivation.mechanism_trigger, derivation.mechanism_response)):
        fatal_failures.append("mechanism validation: signal, state, trigger, or response is missing")
    else:
        strengths.append("The external mechanism has an operational signal-state-trigger-response path.")
    alignment = candidate.alignment_acceptance.upper()
    correspondences = " ".join(derivation.structural_correspondences).casefold()
    if alignment not in {"HARD_VALIDATION_PASSED", "STRONG", "PLAUSIBLE_ACCEPTED"}:
        fatal_failures.append("structural alignment: invalid or no accepted mapping")
    elif "surface similarity" in correspondences or "word overlap" in correspondences:
        limiters.append(_limiter(
            "structural alignment: surface-only correspondence",
            "Vocabulary overlap does not establish a transferable causal mapping.",
            "Map and ablate the required signal, state, trigger, response, and fallback roles.",
        ))
    elif alignment == "PLAUSIBLE_ACCEPTED":
        limiters.append(_limiter(
            "structural alignment: plausible but not yet operator-verified",
            "The key roles map, but the causal transfer remains inferred.",
            "Run a discriminating ablation that removes or shuffles the transferred state/trigger.",
        ))
    else:
        strengths.append("Structural roles map beyond surface vocabulary.")
    if full_audit is not None:
        for item in full_audit.audit_dimensions:
            if item.passed:
                continue
            problems = "; ".join(getattr(item, "specific_problems", ()) or ())
            severity = _audit_severity(item.name, problems)
            message = f"full audit: {item.name}" + (f" — {problems}" if problems else "")
            if severity == AssessmentSeverity.FATAL:
                fatal_failures.append(message)
            else:
                limiters.append(_limiter(
                    message, "This audit dimension remains unresolved.",
                    getattr(item, "recommended_action", "Resolve the recorded audit uncertainty."),
                    severity.value,
                ))
    online_drift = "drift" in purpose.current_failure.casefold() and any(
        term in purpose.task.casefold() for term in ("online", "stream")
    )
    if online_drift and candidate.base_algorithm.casefold() == "random forest":
        repairs.append(RepairRecord(
            "Rebound generic Random Forest to the online tree ensemble family.",
            "Deterministic task-compatible family repair; no exact variant is inferred.",
            "Exact online ensemble variant remains an open implementation choice.",
        ))
        limiters.append(_limiter(
            "algorithm binding: exact online tree ensemble variant remains open",
            "The family is defensible, but Random Forest is not itself an online drift algorithm.",
            "Compare adaptive random forest and streaming ensemble baselines under matched compute.",
        ))
    if capability_plan.fatal_conflicts:
        fatal_failures.extend(
            f"capability/operator plan: {item}" for item in capability_plan.fatal_conflicts
        )
    elif derivation.modification_slot == "update_rule" and len(capability_plan.selected_slot_bundle) > 1:
        repairs.append(RepairRecord(
            "Expanded generic update_rule into an explicit capability/operator slot bundle.",
            "Deterministic required-role to compatible-slot mapping.",
            ", ".join(capability_plan.selected_slot_bundle),
        ))
        if capability_plan.missing_roles:
            limiters.append(_limiter(
                "operator plan: some capability roles remain open",
                "A multi-role capability cannot be represented honestly by one generic update location.",
                "Implement and ablate the selected recognition, memory, verification, and routing/aggregation roles.",
            ))
    if spec.unresolved_implementation_choices:
        limiters.append(_limiter(
            "implementation completeness: schematic operator has undefined variables",
            "The action is interpretable, but the equation is not an exact executable algorithm.",
            "Define each state and parameter, or retain a prose schematic and ablate candidate definitions.",
        ))
    if not spec.action_rule:
        fatal_failures.append("implementation completeness: no identifiable algorithm action")
    inference = " ".join(candidate.required_inference_information).casefold()
    available = " ".join(purpose.available_inference_information).casefold()
    if any(term in inference for term in ("true label", "prediction residual", "labeled error")) and not any(
        term in available for term in ("label", "delayed feedback")
    ):
        delayed = any(term in " ".join((*candidate.required_training_information, *purpose.available_inference_information)).casefold()
                      for term in ("delayed", "feedback"))
        if delayed:
            repairs.append(RepairRecord(
                "Reformulated immediate residual use as a delayed-feedback update.",
                "Purpose/candidate information contract explicitly permits delayed feedback.",
                "The update cannot affect the prediction that generated the label.",
            ))
            limiters.append(_limiter(
                "information timing: residual update is delayed",
                "Benefit can begin only after labeled feedback arrives.",
                "Report recovery time from feedback arrival and compare multiple label delays.",
            ))
        else:
            fatal_failures.append("information availability: required true-label residual has no delayed/proxy formulation")
    if online_drift:
        causal = " ".join((candidate.expected_improvement, candidate.update_rule_delta,
                           candidate.memory_delta, candidate.routing_delta,
                           derivation.mechanism_response)).casefold()
        if "recurr" not in causal or not any(term in causal for term in (
            "prior", "histor", "archive", "regime", "reuse", "reactivat",
        )):
            limiters.append(_limiter(
                "causal path: recurrence-specific reactivation path is unresolved",
                "The current mechanism may address generic drift without explaining faster recurrence recovery.",
                "Test retained-state recognition/reactivation against memory-free and shuffled-history controls.",
            ))
    metrics = {item.casefold() for item in candidate.minimal_experiment.metrics}
    candidate_text = " ".join((candidate.candidate_name, candidate_modification(candidate),
                               *candidate.new_state_variables)).casefold()
    if "expert activation accuracy" in metrics and "expert" not in candidate_text:
        fatal_failures.append("experiment consistency: expert activation metric has no expert mechanism")
    if not candidate.kill_criterion and not candidate.minimal_experiment.failure_rule:
        limiters.append(_limiter(
            "falsification validation: kill criterion is missing",
            "The hypothesis cannot yet be rejected decisively.",
            "Specify a matched-compute failure threshold before implementation.",
        ))

    fatal_failures = list(dict.fromkeys(fatal_failures))
    unique_limiters = list({item.issue: item for item in limiters}.values())
    major = sum(item.severity == AssessmentSeverity.MAJOR_LIMITER for item in unique_limiters)
    experiment_complete = all((candidate.minimal_experiment.hypothesis,
                               candidate.minimal_experiment.success_rule,
                               candidate.minimal_experiment.failure_rule))
    family_bound = _tokens(candidate.base_algorithm_family) not in (set(), {"unknown"})
    if fatal_failures:
        maturity = IdeaMaturityLevel.REJECTED
        reason = "Fundamental coherence or feasibility gate failed."
    elif counts["direct_support_count"] < 1 or not family_bound or major >= 3:
        maturity = IdeaMaturityLevel.EXPLORATORY_HYPOTHESIS
        reason = "The hypothesis is coherent, but a major evidence or design link remains unresolved."
    elif not unique_limiters and experiment_complete and not spec.unresolved_implementation_choices:
        maturity = IdeaMaturityLevel.TEST_READY_PROPOSAL
        reason = "The mechanism, implementation, information timing, and experiment are fully specified."
    else:
        maturity = IdeaMaturityLevel.RESEARCH_WORTHY_HYPOTHESIS
        reason = "The problem, mechanism, structural translation, family, action, and resolving experiment are defensible."
    confidence = {
        "problem_evidence": min(1.0, counts["direct_support_count"] / 2),
        "mechanism_evidence": 1.0 if all((derivation.mechanism_signal, derivation.mechanism_state,
                                         derivation.mechanism_trigger, derivation.mechanism_response)) else 0.0,
        "structural_alignment": 0.7 if alignment == "PLAUSIBLE_ACCEPTED" else 0.9 if alignment else 0.0,
        "implementation": 0.9 if not spec.unresolved_implementation_choices else 0.55,
        "experiment": 0.9 if experiment_complete else 0.4,
    }
    fatal_issues = tuple(issue(
        re.sub(r"[^a-z0-9]+", "_", description.casefold()).strip("_")[:80],
        AssessmentSeverity.FATAL, description, evidence=(candidate.candidate_id,),
        consequence="The hypothesis is scientifically incoherent or infeasible.",
        repair_option="Repair the fatal contradiction before reassessment.",
    ) for description in fatal_failures)
    novelty_level = "CONFIRMED_DUPLICATE" if any("duplicate" in item for item in fatal_failures) else (
        "INCOMPLETE_SEARCH" if any("prior-art" in item.issue for item in unique_limiters) else "NO_DUPLICATE_FOUND"
    )
    return ScientificAssessment(
        candidate_id=candidate.candidate_id, maturity_level=maturity,
        issues=(*fatal_issues, *unique_limiters), strengths=tuple(strengths),
        paper_roles=tuple(roles), paper_counts=counts, modification_spec=spec,
        capability_slot_assessment=capability_plan,
        problem_evidence_level="DIRECT" if counts["direct_support_count"] else "CONTEXT_ONLY",
        mechanism_evidence_level="OPERATIONAL" if not any("mechanism validation" in item for item in fatal_failures) else "NON_OPERATIONAL",
        alignment_level=("SURFACE_ONLY" if any("surface-only" in item.issue for item in unique_limiters)
                         else "METAPHOR_ONLY" if any("metaphor-only" in item for item in fatal_failures)
                         else "PLAUSIBLE_STRUCTURAL" if alignment == "PLAUSIBLE_ACCEPTED"
                         else "STRONG_STRUCTURAL"),
        prior_art_level=novelty_level,
        implementation_level="SCHEMATIC" if spec.unresolved_implementation_choices else "CONCRETE_ACTION",
        information_feasibility_level="IMPOSSIBLE" if any("information availability" in item for item in fatal_failures)
        else "DELAYED" if any("delayed-feedback" in item.repair for item in repairs) else "AVAILABLE",
        experiment_level="COMPLETE" if experiment_complete else "INCOMPLETE",
        maturity_reason=reason,
        repair_options=tuple(item.repair_option for item in unique_limiters),
        repairs_applied=tuple(repairs),
        open_design_choices=tuple((*_open_choices(spec), *capability_plan.open_design_choices)),
        confidence_by_dimension=confidence,
    )


def grouped_gate_failures(results: Sequence[ScientificAssessment]) -> dict[str, int]:
    return dict(Counter(item.code for result in results for item in result.fatal_failures))
