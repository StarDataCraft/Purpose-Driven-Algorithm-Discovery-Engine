from __future__ import annotations

import re
from pathlib import Path

import pytest
import requests

from openalex_client import (
    OpenAlexClient, OpenAlexRequestError, default_query_budget, redact_url,
)
from retrieval_service import retrieve_corpus


class Response:
    def __init__(self, status=200, headers=None, payload=None):
        self.status_code = status
        self.headers = headers or {}
        self._payload = payload or {"results": []}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(f"HTTP {self.status_code}")
            error.response = self
            raise error


class Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def client(responses, api_key=""):
    waits = []
    value = OpenAlexClient(
        api_key=api_key, session=Session(responses), clock=lambda: 0.0,
        sleeper=waits.append, random_source=lambda: 0.0,
    )
    return value, waits


def test_daily_limit_opens_circuit_without_retrying_or_exposing_key():
    value, waits = client([Response(429, {
        "X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "3600",
    })], api_key="unit-test-secret")
    budget = value.begin_run(default_query_budget("API_KEY"))
    with pytest.raises(OpenAlexRequestError) as caught:
        value.get_works({"search": "drift"}, timeout=1, budget=budget,
                        stage="external_retrieval")
    assert caught.value.category == "DAILY_LIMIT"
    assert value.state.circuit_state == "OPEN"
    assert len(value.session.calls) == 1
    assert waits == []
    assert "unit-test-secret" not in str(caught.value)
    assert value.session.calls[0][1]["params"]["api_key"] == "unit-test-secret"


def test_transient_limit_honors_retry_after_then_succeeds():
    value, waits = client([
        Response(429, {"Retry-After": "2", "X-RateLimit-Remaining": "50"}),
        Response(200),
    ])
    budget = value.begin_run(default_query_budget("ANONYMOUS"))
    response = value.get_works(
        {"search": "drift"}, timeout=1, budget=budget,
        stage="broad_ml_retrieval",
    )
    assert response.status_code == 200
    assert value.state.retries_this_run == 1
    assert 2.0 in waits
    assert value.state.circuit_state == "CLOSED"


def test_repeated_transient_limits_open_circuit_after_three_retries():
    value, _ = client([
        Response(429, {"Retry-After": "0", "X-RateLimit-Remaining": "10"})
        for _ in range(4)
    ])
    budget = value.begin_run(default_query_budget("ANONYMOUS"))
    with pytest.raises(OpenAlexRequestError) as caught:
        value.get_works(
            {"search": "drift"}, timeout=1, budget=budget,
            stage="broad_ml_retrieval",
        )
    assert caught.value.category == "TRANSIENT_LIMIT"
    assert value.state.circuit_reason == "REPEATED_SHORT_TERM_429"
    assert len(value.session.calls) == 4


def test_anonymous_budget_is_conservative_and_stage_scoped():
    budget = default_query_budget("ANONYMOUS")
    assert budget.total_limit == 12
    assert budget.stage_limits["broad_ml_retrieval"] == 5
    assert budget.stage_limits["external_retrieval"] == 3
    assert budget.stage_limits["citation_support"] == 0


def test_retrieval_stops_openalex_after_daily_limit_but_arxiv_continues(
    monkeypatch, tmp_path, purpose,
):
    value, _ = client([Response(429, {
        "X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "3600",
    })])
    monkeypatch.setattr("retrieval_service.get_openalex_client", lambda: value)
    from models import Paper
    monkeypatch.setattr(
        "retrieval_service.fetch_arxiv",
        lambda *args: [Paper(
            "arxiv:ok", "Recurring drift evidence", "recovery evidence",
            2025, "arxiv",
        )],
    )
    papers, run = retrieve_corpus(
        purpose, ["q1", "q2", "q3"], cache_directory=tmp_path,
        adapters=None, sources=["openalex", "arxiv"],
    )
    assert len(value.session.calls) == 1
    assert run.source_results[0].api_status == "DAILY_LIMIT"
    assert any(paper.source == "arxiv" for paper in papers)
    assert run.source_results[1].success_count == 3


def test_redaction_and_tracked_source_secret_scan():
    redacted = redact_url(
        "https://api.openalex.org/works?search=x&api_key=sensitive-value"
    )
    assert "sensitive-value" not in redacted
    assert "%5BREDACTED%5D" in redacted
    root = Path(__file__).resolve().parents[1]
    assignment = re.compile(
        r"OPENALEX_API_KEY\s*=\s*['\"][^'\"]+['\"]"
    )
    offenders = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.suffix not in {
            ".py", ".md", ".toml", ".yaml", ".yml", ".json",
        }:
            continue
        text = path.read_text(errors="ignore")
        if assignment.search(text):
            offenders.append(str(path.relative_to(root)))
    assert offenders == []
