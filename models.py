"""Typed records shared by mining, search, synthesis, and persistence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass
class Paper:
    paper_id: str
    title: str
    abstract: str
    year: int
    source: str
    url: str = ""
    doi: str = ""
    arxiv_id: str = ""
    domain: str = "machine_learning"
    sections: dict[str, str] = field(default_factory=dict)
    citations: int = 0
    provenance: list[str] = field(default_factory=list)
    retrieval_origin: str = ""
    retrieved_at_utc: str = ""
    query_ids: list[str] = field(default_factory=list)
    source_request_id: str = ""
    cache_key: str = ""
    fixture_path: str = ""
    original_source: str = ""
    source_rank: int = 0
    sparse_score: float | None = None
    dense_score: float | None = None
    hybrid_score: float | None = None
    provenance_history: list[dict[str, Any]] = field(default_factory=list)
    estimated_relevance_score: float = 0.0
    estimated_relevance_label: str = "ESTIMATED_IRRELEVANT"
    reviewed_relevance_label: str = ""
    review_status: str = "UNREVIEWED"


@dataclass
class PurposeContract:
    purpose_id: str
    mode: Literal["user", "gap_radar"]
    use_case: str
    task: str
    data_type: str
    current_failure: str
    desired_improvement: str
    primary_metric: str
    secondary_metrics: list[str] = field(default_factory=list)
    must_not_degrade: list[str] = field(default_factory=list)
    compute_budget: str = "moderate"
    memory_budget: str = "moderate"
    latency_budget: str = "moderate"
    interpretability_requirement: str = "none"
    uncertainty_requirement: str = "none"
    online_requirement: bool = False
    available_training_information: list[str] = field(default_factory=list)
    available_inference_information: list[str] = field(default_factory=list)
    deployment_environment: str = "research"
    allowed_algorithm_families: list[str] = field(default_factory=list)
    excluded_algorithm_families: list[str] = field(default_factory=list)
    risk_tolerance: str = "medium"
    preferred_candidate_scale: str = "small"
    publication_window: tuple[int, int] = (2021, 2026)
    user_notes: str = ""


@dataclass
class GapSignature:
    gap_id: str
    title: str
    gap_type: Literal["explicit", "aggregated", "structural"]
    task: str
    application_context: str
    data_type: str
    affected_algorithm: str
    affected_algorithm_family: str
    failure_type: str
    affected_component: str
    current_method_pattern: str
    observable_failure_signal: str
    required_response: str
    unresolved_assumptions: list[str]
    constraints: list[str]
    must_preserve: list[str]
    primary_metric: str
    secondary_metrics: list[str]
    available_training_information: list[str]
    available_inference_information: list[str]
    evidence_sentences: list[str]
    evidence_sections: list[str]
    evidence_paper_ids: list[str]
    evidence_count: int
    source_diversity: int
    explicitness_score: float
    aggregation_score: float
    structural_gap_score: float
    trend_score: float
    practical_value_score: float
    testability_score: float
    confidence_score: float
    timescale: str = ""
    detection_method: str = "cue_rules"
    structural_gap_subtype: str = ""
    coverage_gap_id: str = ""
    mismatch_id: str = ""
    research_cluster_id: str = ""
    field_provenance: dict[str, str] = field(default_factory=dict)
    comparison_evidence: list[str] = field(default_factory=list)
    contradiction_evidence: list[str] = field(default_factory=list)
    missing_dimension: str = ""
    known_mitigations: list[str] = field(default_factory=list)
    unresolved_remainder: str = ""
    metadata_completeness: float = 0.0
    model_mode: str = "lightweight"
    classifier_version: str = "rules-v1"
    embedding_version: str = "tfidf-v1"
    evidence_strength_components: dict[str, float] = field(default_factory=dict)
    research_run_id: str = ""


@dataclass
class MechanismSignature:
    mechanism_id: str
    name: str
    source_domain: str
    original_problem: str
    entities: list[str]
    observed_signal: str
    internal_state: str
    response_rule: str
    feedback_type: str
    trigger_condition: str
    adaptation_timescale: str
    equilibrium_or_target: str
    resource_constraint: str
    memory_structure: str
    allocation_rule: str
    selection_rule: str
    failure_boundary: str
    transferable_operator: str
    compatible_slots: list[str]
    incompatible_slots: list[str]
    required_signal: list[str]
    evidence_sentences: list[str]
    evidence_sections: list[str]
    evidence_paper_ids: list[str]
    evidence_count: int
    confidence_score: float
    research_run_id: str = ""


@dataclass
class AlgorithmRecord:
    name: str
    aliases: list[str]
    family: str
    tasks: list[str]
    data_types: list[str]
    assumptions: list[str]
    objective: str
    update_rule: str
    state: str
    information_flow: str
    strengths: list[str]
    weaknesses: list[str]
    known_failure_conditions: list[str]
    modifiable_slots: list[str]
    runtime_complexity: str
    memory_complexity: str
    interpretability: str
    online_capability: str
    uncertainty_capability: str
    missing_data_capability: str
    canonical_baselines: list[str]
    related_methods: list[str]


@dataclass
class Operator:
    operator_id: str
    name: str
    required_inputs: list[str]
    produced_state: list[str]
    compatible_slots: list[str]
    incompatible_slots: list[str]
    formula_schema: str
    update_schema: str
    inference_requirements: list[str]
    training_requirements: list[str]
    complexity_effect: str
    memory_effect: str
    interpretability_effect: str
    known_equivalent_ml_patterns: list[str]
    failure_modes: list[str]


@dataclass
class AlignmentResult:
    gap_id: str
    mechanism_id: str
    field_scores: dict[str, float]
    matched_slots: list[str]
    conflicts: list[str]
    missing_information: list[str]
    score: float
    rejected: bool
    rejection_reasons: list[str]
    research_run_id: str = ""


@dataclass
class ScoreCard:
    components: dict[str, float]
    penalties: dict[str, float]
    total: float
    confidence: str
    rejection_flags: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)


@dataclass
class ExperimentPlan:
    hypothesis: str
    target_task: str
    application_context: str
    dataset: str
    stressor: str
    base_algorithm: str
    baselines: list[str]
    ablations: list[str]
    metrics: list[str]
    compute_reporting: list[str]
    seeds: list[int]
    success_rule: str
    failure_rule: str
    information_audit: dict[str, Any]
    expected_runtime_class: str
    reproducibility_notes: str


@dataclass
class AlgorithmModificationSpec:
    """Executable operator-to-algorithm translation used by promotion gates."""

    base_algorithm_family: str
    base_algorithm_variant: str
    modification_slot: str
    original_state: list[str]
    new_state_variables: list[str]
    variable_definitions: dict[str, str]
    trigger_condition: str
    update_rule: str
    action_rule: str
    initialization: str
    fallback_rule: str
    training_information: list[str]
    inference_information: list[str]
    delayed_information: list[str]
    compute_complexity: str
    memory_complexity: str
    protected_invariants: list[str]
    unresolved_implementation_choices: list[str]


@dataclass(frozen=True)
class PaperEvidenceRole:
    paper_id: str
    role: str
    automatic_relevance: str
    human_review_status: str
    supported_claim: str
    evidence_excerpt: str
    inclusion_reason: str


@dataclass
class AlgorithmCandidate:
    candidate_id: str
    candidate_name: str
    direction_family: str
    purpose_contract_id: str
    gap_id: str
    gap_summary: str
    evidence_paper_ids: list[str]
    base_algorithm: str
    base_algorithm_family: str
    affected_component: str
    borrowed_mechanisms: list[str]
    source_domains: list[str]
    structural_alignment: dict[str, float]
    selected_operators: list[str]
    new_state_variables: list[str]
    objective_delta: str
    update_rule_delta: str
    inference_delta: str
    initialization_delta: str
    memory_delta: str
    routing_delta: str
    aggregation_delta: str
    stopping_delta: str
    component_lifecycle_delta: str
    complexity_delta: str
    required_training_information: list[str]
    required_inference_information: list[str]
    expected_improvement: str
    primary_metric: str
    secondary_metrics: list[str]
    must_not_degrade: list[str]
    applicability_conditions: list[str]
    expected_failure_modes: list[str]
    trade_offs: list[str]
    falsification_tests: list[str]
    novelty_queries: list[str]
    nearest_known_method_patterns: list[str]
    minimal_experiment: ExperimentPlan
    scores: ScoreCard
    confidence: str
    stochastic_trace: dict[str, Any]
    structural_fingerprint: str = ""
    novelty_status: str = "insufficient evidence"
    strongest_rejection_reason: str = ""
    kill_criterion: str = ""
    research_run_id: str = ""
    alignment_id: str = ""
    alignment_acceptance: str = ""
    selected_gap_snapshot: dict[str, Any] = field(default_factory=dict)


@dataclass
class DirectionFamily:
    family_id: str
    name: str
    origin_gap_ids: list[str]
    source_domains: list[str]
    mechanism_ids: list[str]
    target_tasks: list[str]
    affected_algorithm_families: list[str]
    modification_slots: list[str]
    common_operators: list[str]
    intended_applications: list[str]
    expected_benefits: list[str]
    trade_offs: list[str]
    candidate_ids: list[str]
    risk_level: str
    evidence_strength: float
    novelty_status: str
    best_first_experiment: str = ""
    research_run_id: str = ""


def to_dict(record: Any) -> dict[str, Any]:
    """Convert a dataclass record to a JSON-safe dictionary."""
    return asdict(record)
