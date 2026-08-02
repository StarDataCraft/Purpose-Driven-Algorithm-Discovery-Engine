"""Dependency-neutral contracts for hypothesis maturity and operator planning."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class IdeaMaturityLevel(str, Enum):
    REJECTED = "REJECTED"
    EXPLORATORY_HYPOTHESIS = "EXPLORATORY_HYPOTHESIS"
    RESEARCH_WORTHY_HYPOTHESIS = "RESEARCH_WORTHY_HYPOTHESIS"
    TEST_READY_PROPOSAL = "TEST_READY_PROPOSAL"


MATURITY_ORDER = {
    IdeaMaturityLevel.REJECTED: 0,
    IdeaMaturityLevel.EXPLORATORY_HYPOTHESIS: 1,
    IdeaMaturityLevel.RESEARCH_WORTHY_HYPOTHESIS: 2,
    IdeaMaturityLevel.TEST_READY_PROPOSAL: 3,
}


class AssessmentSeverity(str, Enum):
    FATAL = "FATAL"
    MAJOR_LIMITER = "MAJOR_LIMITER"
    MINOR_LIMITER = "MINOR_LIMITER"
    INFORMATIONAL = "INFORMATIONAL"


@dataclass(frozen=True)
class AssessmentIssue:
    code: str
    severity: AssessmentSeverity
    issue: str
    evidence: tuple[str, ...]
    consequence: str
    repair_option: str

    def __contains__(self, value: str) -> bool:
        """Compatibility for legacy tests/display code using substring checks."""
        return value in self.issue


@dataclass(frozen=True)
class OpenDesignChoice:
    name: str
    role: str
    possible_options: tuple[str, ...]
    current_default: str
    information_needed: str
    resolving_experiment: str
    effect_if_chosen_incorrectly: str


@dataclass(frozen=True)
class RepairRecord:
    repair: str
    provenance: str
    effect: str


@dataclass(frozen=True)
class CapabilityOperatorPlan:
    required_capability: str
    required_roles: tuple[str, ...]
    algorithm_family: str
    candidate_slots: tuple[str, ...]
    selected_slot_bundle: tuple[str, ...]
    role_to_slot_mapping: Mapping[str, str]
    missing_roles: tuple[str, ...]
    compatibility_score: float
    fatal_conflicts: tuple[str, ...]
    open_design_choices: tuple[OpenDesignChoice, ...]
    covered_mechanism_roles: tuple[str, ...] = ()
    ml_engineering_roles: tuple[str, ...] = ()
    analogy_risks: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScientificAssessment:
    candidate_id: str
    maturity_level: IdeaMaturityLevel
    issues: tuple[AssessmentIssue, ...]
    strengths: tuple[str, ...]
    paper_roles: tuple[Any, ...]
    paper_counts: Mapping[str, int]
    modification_spec: Any
    capability_slot_assessment: CapabilityOperatorPlan
    problem_evidence_level: str
    mechanism_evidence_level: str
    alignment_level: str
    prior_art_level: str
    implementation_level: str
    information_feasibility_level: str
    experiment_level: str
    maturity_reason: str
    repair_options: tuple[str, ...]
    repairs_applied: tuple[RepairRecord, ...]
    open_design_choices: tuple[OpenDesignChoice, ...]
    confidence_by_dimension: Mapping[str, float]

    def by_severity(self, severity: AssessmentSeverity) -> tuple[AssessmentIssue, ...]:
        return tuple(item for item in self.issues if item.severity == severity)

    @property
    def fatal_failures(self) -> tuple[AssessmentIssue, ...]:
        return self.by_severity(AssessmentSeverity.FATAL)

    @property
    def major_limiters(self) -> tuple[AssessmentIssue, ...]:
        return self.by_severity(AssessmentSeverity.MAJOR_LIMITER)

    @property
    def minor_limiters(self) -> tuple[AssessmentIssue, ...]:
        return self.by_severity(AssessmentSeverity.MINOR_LIMITER)

    @property
    def maturity_limiters(self) -> tuple[AssessmentIssue, ...]:
        """Compatibility view over typed major and minor limiters."""
        return (*self.major_limiters, *self.minor_limiters)

    @property
    def informational_notes(self) -> tuple[AssessmentIssue, ...]:
        return self.by_severity(AssessmentSeverity.INFORMATIONAL)

    @property
    def passed(self) -> bool:
        return MATURITY_ORDER[self.maturity_level] >= 2

    @property
    def failures(self) -> tuple[str, ...]:
        """Legacy display view; never use this property for maturity decisions."""
        return tuple(item.issue for item in self.issues)


def issue(
    code: str, severity: AssessmentSeverity, description: str,
    *, evidence: Sequence[str] = (), consequence: str, repair_option: str,
) -> AssessmentIssue:
    return AssessmentIssue(
        code, severity, description, tuple(evidence), consequence, repair_option,
    )


def maturity_value(level: IdeaMaturityLevel) -> int:
    return MATURITY_ORDER[level]
