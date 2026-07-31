"""Dependency-neutral canonical models for research-run provenance."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from models import Paper

ACTUAL_SEARCH_MODES = {
    "LIVE", "CACHE", "MIXED", "OFFLINE_FIXTURE", "FAILED",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class SourceRetrievalResult:
    source: str
    source_type: str
    queries_attempted: list[str] = field(default_factory=list)
    request_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    raw_returned_count: int = 0
    unique_returned_count: int = 0
    api_status: str = ""
    failure_messages: list[str] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""
    duration_seconds: float = 0.0
    rate_limit_wait_seconds: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    fallback_contribution: int = 0
    actual_origin: str = ""
    cache_age_seconds: list[float] = field(default_factory=list)
    paper_ids: list[str] = field(default_factory=list)
    domain: str = ""
    mechanism_bearing_paper_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SourceRetrievalResult":
        return cls(**value)


@dataclass
class StageRun:
    stage_id: str
    stage_name: str
    parent_run_id: str
    started_at: str
    completed_at: str = ""
    wall_clock_duration_seconds: float = 0.0
    requested_mode: str = ""
    actual_mode: str = ""
    query_count: int = 0
    queries: list[str] = field(default_factory=list)
    source_results: list[SourceRetrievalResult] = field(default_factory=list)
    raw_input_count: int = 0
    output_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    truncation: str = ""
    model_backend: str = ""
    model_version: str = ""
    threshold_version: str = "quality-thresholds-v1"
    sum_source_request_duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "StageRun":
        payload = dict(value)
        payload["source_results"] = [
            item if isinstance(item, SourceRetrievalResult)
            else SourceRetrievalResult.from_dict(item)
            for item in payload.get("source_results", [])
        ]
        return cls(**payload)


@dataclass
class QualityWarning:
    warning_id: str
    severity: str
    stage: str
    code: str
    title: str
    explanation: str
    observed_value: str
    expected_range: str
    recommended_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "QualityWarning":
        return cls(**value)


@dataclass(frozen=True)
class SelectedGapSnapshot:
    gap_id: str
    title: str
    plain_language_statement: str
    gap_type: str
    affected_task: str
    affected_algorithm_family: str
    binding_granularity: str
    failure_condition: str
    affected_metric: str
    evidence_papers: tuple[str, ...]
    known_solutions: tuple[str, ...]
    unresolved_remainder: str
    confidence: float
    selected_timestamp: str
    parent_run_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SelectedGapSnapshot":
        payload = dict(value)
        payload["evidence_papers"] = tuple(payload.get("evidence_papers", ()))
        payload["known_solutions"] = tuple(payload.get("known_solutions", ()))
        return cls(**payload)


@dataclass
class ResearchRun:
    run_id: str
    created_at_utc: str
    purpose_contract_id: str
    requested_search_mode: str
    actual_search_mode: str
    engine_mode: str
    publication_window_requested: tuple[int, int]
    actual_publication_year_min: int = 0
    actual_publication_year_max: int = 0
    ml_queries: list[str] = field(default_factory=list)
    focused_algorithm_queries: list[str] = field(default_factory=list)
    external_queries_by_domain: dict[str, list[str]] = field(default_factory=dict)
    sources_attempted: list[str] = field(default_factory=list)
    source_results: list[SourceRetrievalResult] = field(default_factory=list)
    source_failures: dict[str, str] = field(default_factory=dict)
    live_request_attempted: bool = False
    live_request_succeeded: bool = False
    cache_used: bool = False
    cache_keys: list[str] = field(default_factory=list)
    cache_created_at: str = ""
    cache_age_seconds: float = 0.0
    cache_ttl_seconds: int = 0
    fallback_occurred: bool = False
    fallback_reason: str = ""
    fixture_paths: list[str] = field(default_factory=list)
    fixture_version: str = ""
    raw_paper_count: int = 0
    deduplicated_paper_count: int = 0
    relevant_paper_count: int = 0
    candidate_paper_count: int = 0
    automatically_relevant_paper_count: int = 0
    human_reviewed_paper_count: int = 0
    human_confirmed_relevant_paper_count: int = 0
    evidence_bearing_paper_count: int = 0
    papers_used_for_gap_generation: int = 0
    papers_used_for_known_solution_search: int = 0
    paper_ids: list[str] = field(default_factory=list)
    source_count: int = 0
    query_count: int = 0
    broad_query_count: int = 0
    focused_query_count: int = 0
    external_query_count: int = 0
    total_query_count: int = 0
    unique_source_count: int = 0
    source_stage_result_count: int = 0
    truncation_applied: bool = False
    truncation_reason: str = ""
    retrieval_duration_seconds: float = 0.0
    overall_wall_clock_duration_seconds: float = 0.0
    sum_source_request_duration_seconds: float = 0.0
    newest_cache_age_seconds: float = 0.0
    oldest_cache_age_seconds: float = 0.0
    median_cache_age_seconds: float = 0.0
    expired_cache_count: int = 0
    fresh_cache_count: int = 0
    structural_gap_count: int = 0
    mechanism_count: int = 0
    candidate_count: int = 0
    selected_gap_id: str = ""
    parent_run_id: str = ""
    query_profile_version: str = "problem-query-v2"
    translation_profile_version: str = "domain-translation-v1"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    stage_records: dict[str, dict[str, Any]] = field(default_factory=dict)
    stages: list[StageRun] = field(default_factory=list)
    quality_warnings: list[QualityWarning] = field(default_factory=list)
    evidence_event_count: int = 0
    raw_gap_instance_count: int = 0
    canonical_gap_family_count: int = 0
    promoted_gap_count: int = 0
    exploratory_gap_count: int = 0
    selected_gap_snapshot: dict[str, Any] = field(default_factory=dict)
    alignment_funnel: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ResearchRun":
        """Load current or legacy JSON records using dataclass defaults."""
        payload = dict(value)
        fields = cls.__dataclass_fields__
        payload = {key: item for key, item in payload.items() if key in fields}
        payload["publication_window_requested"] = tuple(
            payload.get("publication_window_requested", (2021, 2026))
        )
        payload["source_results"] = [
            item if isinstance(item, SourceRetrievalResult)
            else SourceRetrievalResult.from_dict(item)
            for item in payload.get("source_results", [])
        ]
        payload["stages"] = [
            item if isinstance(item, StageRun) else StageRun.from_dict(item)
            for item in payload.get("stages", [])
        ]
        payload["quality_warnings"] = [
            item if isinstance(item, QualityWarning)
            else QualityWarning.from_dict(item)
            for item in payload.get("quality_warnings", [])
        ]
        return cls(**payload)

    @classmethod
    def create(
        cls, purpose_contract_id: str, requested_search_mode: str,
        engine_mode: str, publication_window: tuple[int, int],
    ) -> "ResearchRun":
        return cls(
            run_id=f"run:{uuid4().hex[:12]}",
            created_at_utc=utc_now(),
            purpose_contract_id=purpose_contract_id,
            requested_search_mode=requested_search_mode,
            actual_search_mode="FAILED",
            engine_mode=engine_mode,
            publication_window_requested=publication_window,
        )

    def finalize_from_papers(self, papers: list[Paper]) -> None:
        # The actual mode describes this retrieval run. Historical origins are
        # retained for audit but must not make a cache replay appear MIXED.
        origins = {paper.retrieval_origin for paper in papers if paper.retrieval_origin}
        has_live = any(origin.startswith("live_") for origin in origins)
        has_cache = any(origin.startswith("cache_") for origin in origins)
        has_fixture = "offline_fixture" in origins
        if not papers:
            mode = "FAILED"
        elif sum((has_live, has_cache, has_fixture)) > 1:
            mode = "MIXED"
        elif has_live:
            mode = "LIVE"
        elif has_cache:
            mode = "CACHE"
        elif has_fixture:
            mode = "OFFLINE_FIXTURE"
        else:
            mode = "FAILED"
            self.warnings.append("Papers lacked recognized retrieval provenance.")
        self.actual_search_mode = mode
        years = [paper.year for paper in papers if paper.year]
        self.actual_publication_year_min = min(years) if years else 0
        self.actual_publication_year_max = max(years) if years else 0
        self.deduplicated_paper_count = len(papers)
        self.candidate_paper_count = len(papers)
        self.automatically_relevant_paper_count = sum(
            paper.estimated_relevance_label in {
                "ESTIMATED_HIGH", "ESTIMATED_MEDIUM"
            } for paper in papers
        )
        self.human_reviewed_paper_count = sum(
            paper.review_status == "REVIEWED" for paper in papers
        )
        self.human_confirmed_relevant_paper_count = sum(
            paper.reviewed_relevance_label in {"HIGHLY_RELEVANT", "RELEVANT"}
            for paper in papers
        )
        # Backward-compatible field: now explicitly mirrors automatic relevance.
        self.relevant_paper_count = self.automatically_relevant_paper_count
        self.paper_ids = [paper.paper_id for paper in papers]
        self.source_count = len({
            paper.original_source or paper.source for paper in papers
        })
        self.unique_source_count = self.source_count
        self.source_stage_result_count = len(self.source_results)
        ages = [
            age for result in self.source_results
            for age in result.cache_age_seconds
        ]
        if ages:
            ordered = sorted(ages)
            self.newest_cache_age_seconds = ordered[0]
            self.oldest_cache_age_seconds = ordered[-1]
            middle = len(ordered) // 2
            self.median_cache_age_seconds = (
                ordered[middle] if len(ordered) % 2
                else (ordered[middle - 1] + ordered[middle]) / 2
            )
            self.fresh_cache_count = sum(
                age <= self.cache_ttl_seconds for age in ages
            )
            self.expired_cache_count = len(ages) - self.fresh_cache_count
        self.cache_used = has_cache
        self.live_request_succeeded = has_live


def paper_provenance(
    paper: Paper, retrieval_origin: str, query_id: str,
    request_id: str, *, cache_key: str = "", fixture_path: str = "",
    rank: int = 0,
) -> Paper:
    """Attach one immutable retrieval event to a paper."""
    event = {
        "retrieval_origin": retrieval_origin,
        "retrieved_at_utc": utc_now(),
        "query_ids": [query_id] if query_id else [],
        "source_request_id": request_id,
        "cache_key": cache_key,
        "fixture_path": fixture_path,
        "original_source": paper.original_source or paper.source,
        "source_rank": rank,
    }
    paper.retrieval_origin = retrieval_origin
    paper.retrieved_at_utc = event["retrieved_at_utc"]
    paper.query_ids = sorted(set(paper.query_ids + event["query_ids"]))
    paper.source_request_id = request_id
    paper.cache_key = cache_key
    paper.fixture_path = fixture_path
    paper.original_source = event["original_source"]
    paper.source_rank = rank
    paper.provenance_history.append(event)
    return paper
