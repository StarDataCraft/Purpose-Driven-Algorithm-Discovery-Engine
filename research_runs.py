"""Canonical provenance models shared by every research workflow stage."""

from __future__ import annotations

from dataclasses import dataclass, field
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
    paper_ids: list[str] = field(default_factory=list)
    source_count: int = 0
    query_count: int = 0
    truncation_applied: bool = False
    truncation_reason: str = ""
    retrieval_duration_seconds: float = 0.0
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
        self.relevant_paper_count = len(papers)
        self.paper_ids = [paper.paper_id for paper in papers]
        self.source_count = len({
            paper.original_source or paper.source for paper in papers
        })
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
