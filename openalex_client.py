"""Central, credential-safe OpenAlex client with budgets and a circuit breaker."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import os
import random
import threading
import time
from typing import Callable, Mapping

import requests


OPENALEX_URL = "https://api.openalex.org/works"
REDACTED = "[REDACTED]"


@dataclass
class QueryBudget:
    authentication_mode: str
    total_limit: int
    stage_limits: dict[str, int]
    total_used: int = 0
    stage_used: dict[str, int] = field(default_factory=dict)

    def available(self, stage: str) -> bool:
        return (
            self.total_used < self.total_limit
            and self.stage_used.get(stage, 0) < self.stage_limits.get(stage, 0)
        )

    def consume(self, stage: str) -> bool:
        if not self.available(stage):
            return False
        self.total_used += 1
        self.stage_used[stage] = self.stage_used.get(stage, 0) + 1
        return True


def default_query_budget(authentication_mode: str) -> QueryBudget:
    if authentication_mode == "API_KEY":
        return QueryBudget(authentication_mode, 30, {
            "broad_ml_retrieval": 8, "focused_ml_retrieval": 6,
            "known_solution_retrieval": 5, "external_retrieval": 8,
            "citation_support": 3,
        })
    return QueryBudget(authentication_mode, 12, {
        "broad_ml_retrieval": 5, "focused_ml_retrieval": 2,
        "known_solution_retrieval": 2, "external_retrieval": 3,
        "citation_support": 0,
    })


@dataclass
class OpenAlexRateLimitState:
    authentication_mode: str
    daily_limit: int | None = None
    daily_remaining: int | None = None
    credits_used: int | None = None
    reset_at: str = ""
    reset_in_seconds: int | None = None
    retry_after_seconds: float | None = None
    last_status_code: int | None = None
    last_checked_at: str = ""
    daily_limit_exhausted: bool = False
    short_term_rate_limited: bool = False
    circuit_state: str = "CLOSED"
    circuit_reason: str = ""
    requests_this_run: int = 0
    request_budget_this_run: int = 0
    retries_this_run: int = 0
    skipped_queries: int = 0

    def safe_dict(self) -> dict[str, object]:
        return asdict(self)


class OpenAlexRequestError(RuntimeError):
    def __init__(self, message: str, *, category: str, state: OpenAlexRateLimitState):
        super().__init__(message)
        self.category = category
        self.state = state


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _integer(headers: Mapping[str, str], name: str) -> int | None:
    try:
        return int(float(headers[name]))
    except (KeyError, TypeError, ValueError):
        return None


def _secret_from_streamlit() -> str:
    try:
        import streamlit as st
        return str(st.secrets.get("OPENALEX_API_KEY", "")).strip()
    except Exception:
        return ""


def load_openalex_api_key() -> str:
    """Return the runtime secret without logging, serializing, or caching it."""
    return os.environ.get("OPENALEX_API_KEY", "").strip() or _secret_from_streamlit()


def redact_url(value: str) -> str:
    """Remove credential-bearing query values from diagnostic text."""
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    try:
        parts = urlsplit(value)
        query = urlencode([
            (key, REDACTED if key.casefold() in {"api_key", "apikey", "key"} else item)
            for key, item in parse_qsl(parts.query, keep_blank_values=True)
        ])
        return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))
    except Exception:
        return value


class OpenAlexClient:
    """One process-level client; callers provide a run-scoped query budget."""

    def __init__(
        self, *, api_key: str | None = None, session: requests.Session | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        random_source: Callable[[], float] = random.random,
        keyed_requests_per_second: float = 5.0,
        anonymous_requests_per_second: float = 1.0,
    ):
        self._api_key = load_openalex_api_key() if api_key is None else api_key
        self.session = session or requests.Session()
        self.clock = clock
        self.sleeper = sleeper
        self.random_source = random_source
        self.requests_per_second = (
            keyed_requests_per_second if self._api_key
            else anonymous_requests_per_second
        )
        mode = "API_KEY" if self._api_key else "ANONYMOUS"
        self.state = OpenAlexRateLimitState(authentication_mode=mode)
        self._lock = threading.RLock()
        self._next_request_at = 0.0

    @property
    def authentication_mode(self) -> str:
        return self.state.authentication_mode

    def begin_run(self, budget: QueryBudget | None = None) -> QueryBudget:
        budget = budget or default_query_budget(self.authentication_mode)
        self.state.requests_this_run = 0
        self.state.request_budget_this_run = budget.total_limit
        self.state.retries_this_run = 0
        self.state.skipped_queries = 0
        return budget

    def _update_headers(self, response: requests.Response) -> None:
        headers = response.headers
        self.state.daily_limit = _integer(headers, "X-RateLimit-Limit")
        self.state.daily_remaining = _integer(headers, "X-RateLimit-Remaining")
        self.state.credits_used = _integer(headers, "X-RateLimit-Credits-Used")
        reset = _integer(headers, "X-RateLimit-Reset")
        self.state.reset_in_seconds = reset
        if reset is not None:
            self.state.reset_at = datetime.fromtimestamp(
                time.time() + max(0, reset), timezone.utc
            ).isoformat(timespec="seconds")
        retry = _integer(headers, "Retry-After")
        self.state.retry_after_seconds = float(retry) if retry is not None else None
        self.state.last_status_code = response.status_code
        self.state.last_checked_at = _utc_now()

    def _wait_for_slot(self) -> None:
        now = self.clock()
        wait = max(0.0, self._next_request_at - now)
        if wait:
            self.sleeper(wait)
        self._next_request_at = max(now, self._next_request_at) + (
            1.0 / max(self.requests_per_second, 0.01)
        )

    def get_works(
        self, params: dict[str, str | int], *, timeout: float,
        budget: QueryBudget, stage: str, max_retries: int = 3,
    ) -> requests.Response:
        if self.state.circuit_state == "OPEN":
            self.state.skipped_queries += 1
            raise OpenAlexRequestError(
                "OpenAlex request skipped because the source circuit is open.",
                category="CIRCUIT_OPEN", state=self.state,
            )
        if not budget.consume(stage):
            self.state.skipped_queries += 1
            raise OpenAlexRequestError(
                "OpenAlex request skipped because this run's query budget is exhausted.",
                category="QUERY_BUDGET", state=self.state,
            )
        safe_params = dict(params)
        if self._api_key:
            safe_params["api_key"] = self._api_key
        transient_failures = 0
        with self._lock:
            for attempt in range(max_retries + 1):
                self._wait_for_slot()
                self.state.requests_this_run += 1
                response = self.session.get(
                    OPENALEX_URL, params=safe_params, timeout=timeout,
                    headers={"User-Agent": "PurposeDrivenDiscovery/1.0"},
                )
                self._update_headers(response)
                if response.status_code != 429:
                    self.state.short_term_rate_limited = False
                    response.raise_for_status()
                    return response
                remaining = self.state.daily_remaining
                reset = self.state.reset_in_seconds
                daily = remaining == 0 and (reset is None or reset > 60)
                if daily:
                    self.state.daily_limit_exhausted = True
                    self.state.circuit_state = "OPEN"
                    self.state.circuit_reason = "DAILY_LIMIT_EXHAUSTED"
                    raise OpenAlexRequestError(
                        "OpenAlex daily request limit reached; remaining queries were skipped.",
                        category="DAILY_LIMIT", state=self.state,
                    )
                transient_failures += 1
                self.state.short_term_rate_limited = True
                if attempt >= max_retries:
                    self.state.circuit_state = "OPEN"
                    self.state.circuit_reason = "REPEATED_SHORT_TERM_429"
                    raise OpenAlexRequestError(
                        "OpenAlex remained temporarily rate limited; remaining queries were skipped.",
                        category="TRANSIENT_LIMIT", state=self.state,
                    )
                self.state.retries_this_run += 1
                delay = self.state.retry_after_seconds
                if delay is None:
                    delay = min(8.0, 0.5 * (2 ** attempt)) + self.random_source() * 0.25
                self.sleeper(delay)
                self.requests_per_second = max(0.5, self.requests_per_second / 2)
        raise AssertionError(f"unreachable after {transient_failures} failures")


_CLIENT: OpenAlexClient | None = None
_CLIENT_LOCK = threading.Lock()


def get_openalex_client() -> OpenAlexClient:
    global _CLIENT
    with _CLIENT_LOCK:
        if _CLIENT is None:
            _CLIENT = OpenAlexClient()
        return _CLIENT


def reset_openalex_client_for_tests() -> None:
    global _CLIENT
    with _CLIENT_LOCK:
        _CLIENT = None
