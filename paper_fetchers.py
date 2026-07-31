"""Legal OpenAlex and arXiv adapters with retries, caching, and deduplication."""

from __future__ import annotations

import json
import time
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import requests

from app_settings import SETTINGS
from models import Paper
from text_processing import fingerprint, normalized_title


class PaperFetchError(RuntimeError):
    """Raised when one paper source fails after bounded retries."""


@dataclass
class FetchDiagnostics:
    """User-visible provenance for one paper retrieval run."""

    search_mode: str
    sources_queried: list[str]
    query_strings: list[str]
    retrieval_timestamp: str
    returned_by_source: dict[str, int]
    number_before_deduplication: int
    number_after_deduplication: int
    publication_date_range: tuple[int, int]
    source_failures: dict[str, str]
    fallback_occurred: bool = False
    fallback_reason: str = ""
    cache_lifetime_seconds: int = SETTINGS.cache_ttl_seconds
    cache_created_at: str = ""


def _timestamp(epoch: float | None = None) -> str:
    value = datetime.fromtimestamp(epoch, timezone.utc) if epoch else datetime.now(timezone.utc)
    return value.isoformat(timespec="seconds")


def _request(url: str, params: dict[str, str | int], timeout: float,
             session: requests.Session | None = None) -> requests.Response:
    client = session or requests.Session()
    error: Exception | None = None
    for attempt in range(SETTINGS.max_retries):
        try:
            response = client.get(url, params=params, timeout=timeout,
                                  headers={"User-Agent": "PurposeDrivenDiscovery/1.0"})
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            error = exc
            if attempt + 1 < SETTINGS.max_retries:
                time.sleep(min(2 ** attempt * .25, 2))
    raise PaperFetchError(f"request failed for {url}: {error}")


def _openalex_abstract(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    positioned = [(position, word) for word, positions in index.items() for position in positions]
    return " ".join(word for _, word in sorted(positioned))


def fetch_openalex(query: str, max_results: int = 20, start_year: int = 2021,
                   end_year: int = 2026, timeout: float = SETTINGS.request_timeout,
                   session: requests.Session | None = None) -> list[Paper]:
    params: dict[str, str | int] = {
        "search": query, "per-page": min(max_results, 50),
        "filter": f"from_publication_date:{start_year}-01-01,to_publication_date:{end_year}-12-31",
        "select": "id,title,publication_year,doi,primary_location,abstract_inverted_index,cited_by_count",
    }
    if SETTINGS.openalex_email:
        params["mailto"] = SETTINGS.openalex_email
    response = _request("https://api.openalex.org/works", params, timeout, session)
    papers = []
    for work in response.json().get("results", []):
        location = work.get("primary_location") or {}
        papers.append(Paper(
            paper_id=work["id"].rsplit("/", 1)[-1],
            title=work.get("title") or "",
            abstract=_openalex_abstract(work.get("abstract_inverted_index")),
            year=int(work.get("publication_year") or 0),
            source="openalex", url=location.get("landing_page_url") or work["id"],
            doi=(work.get("doi") or "").replace("https://doi.org/", ""),
            citations=int(work.get("cited_by_count") or 0), provenance=["openalex"],
        ))
    return papers


def fetch_arxiv(query: str, max_results: int = 20, start_year: int = 2021,
                end_year: int = 2026, timeout: float = SETTINGS.request_timeout,
                session: requests.Session | None = None) -> list[Paper]:
    response = _request("https://export.arxiv.org/api/query", {
        "search_query": f"all:{query}", "start": 0, "max_results": min(max_results, 50),
        "sortBy": "submittedDate", "sortOrder": "descending",
    }, timeout, session)
    root = ET.fromstring(response.text)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    papers = []
    for entry in root.findall("a:entry", ns):
        published = entry.findtext("a:published", "", ns)
        year = int(published[:4]) if published else 0
        if not start_year <= year <= end_year:
            continue
        url = entry.findtext("a:id", "", ns)
        arxiv_id = url.rsplit("/", 1)[-1].split("v")[0]
        papers.append(Paper(
            paper_id=f"arxiv:{arxiv_id}",
            title=" ".join(entry.findtext("a:title", "", ns).split()),
            abstract=" ".join(entry.findtext("a:summary", "", ns).split()),
            year=year, source="arxiv", url=url, arxiv_id=arxiv_id,
            provenance=["arxiv"],
        ))
    return papers


def deduplicate_papers(papers: list[Paper]) -> list[Paper]:
    """Deduplicate in DOI/arXiv/title/title-year/abstract priority order."""
    seen: dict[str, Paper] = {}
    for paper in papers:
        keys = [
            f"doi:{paper.doi.casefold()}" if paper.doi else "",
            f"arxiv:{paper.arxiv_id.casefold()}" if paper.arxiv_id else "",
            f"title:{normalized_title(paper.title)}",
            f"titleyear:{normalized_title(paper.title)}:{paper.year}",
            f"abstract:{fingerprint(paper.abstract)}" if paper.abstract else "",
        ]
        existing = next((seen[key] for key in keys if key and key in seen), None)
        if existing:
            existing.provenance = sorted(set(existing.provenance + paper.provenance))
            continue
        for key in keys:
            if key:
                seen[key] = paper
    unique: dict[str, Paper] = {}
    for paper in seen.values():
        unique[paper.paper_id] = paper
    return list(unique.values())


def fetch_papers(query: str, sources: list[str], max_results: int = 20,
                 start_year: int = 2021, end_year: int = 2026,
                 adapters: dict[str, Callable[..., list[Paper]]] | None = None
                 ) -> tuple[list[Paper], dict[str, str]]:
    """Fetch independently so one failed source still yields partial results."""
    papers, diagnostics = fetch_papers_detailed(
        query, sources, max_results, start_year, end_year, adapters
    )
    return papers, diagnostics.source_failures


def fetch_papers_detailed(
    query: str,
    sources: list[str],
    max_results: int = 20,
    start_year: int = 2021,
    end_year: int = 2026,
    adapters: dict[str, Callable[..., list[Paper]]] | None = None,
) -> tuple[list[Paper], FetchDiagnostics]:
    """Fetch live sources independently and report pre/post-deduplication counts."""
    adapters = adapters or {"openalex": fetch_openalex, "arxiv": fetch_arxiv}
    papers: list[Paper] = []
    failures: dict[str, str] = {}
    returned_by_source = {source: 0 for source in sources}
    per_source = max(1, max_results // max(1, len(sources)))
    for source in sources:
        try:
            fetched = adapters[source](query, per_source, start_year, end_year)
            returned_by_source[source] = len(fetched)
            papers.extend(fetched)
        except (PaperFetchError, KeyError, ValueError, ET.ParseError) as exc:
            failures[source] = str(exc)
        time.sleep(SETTINGS.rate_limit_seconds)
    deduplicated = deduplicate_papers(papers)[:max_results]
    diagnostics = FetchDiagnostics(
        search_mode="LIVE",
        sources_queried=list(sources),
        query_strings=[query],
        retrieval_timestamp=_timestamp(),
        returned_by_source=returned_by_source,
        number_before_deduplication=len(papers),
        number_after_deduplication=len(deduplicated),
        publication_date_range=(start_year, end_year),
        source_failures=failures,
    )
    return deduplicated, diagnostics


def fetch_papers_cached(query: str, sources: list[str], max_results: int = 20,
                        start_year: int = 2021, end_year: int = 2026,
                        cache_directory: Path = Path(".paper_cache"),
                        force_fresh: bool = False,
                        ) -> tuple[list[Paper], dict[str, str]]:
    """Use a local response cache before contacting public sources."""
    papers, diagnostics = fetch_papers_cached_detailed(
        query, sources, max_results, start_year, end_year,
        cache_directory, force_fresh,
    )
    return papers, diagnostics.source_failures


def fetch_papers_cached_detailed(
    query: str,
    sources: list[str],
    max_results: int = 20,
    start_year: int = 2021,
    end_year: int = 2026,
    cache_directory: Path = Path(".paper_cache"),
    force_fresh: bool = False,
) -> tuple[list[Paper], FetchDiagnostics]:
    """Return explicit LIVE/CACHE provenance and optionally bypass cache reads."""
    cache = PaperCache(cache_directory)
    key = json.dumps([query, sorted(sources), max_results, start_year, end_year])
    cached = None if force_fresh else cache.get_entry(key)
    if cached is not None:
        papers, metadata, created_at = cached
        counts = metadata.get("returned_by_source") or {
            source: sum(source in paper.provenance for paper in papers)
            for source in sources
        }
        diagnostics = FetchDiagnostics(
            search_mode="CACHE",
            sources_queried=list(sources),
            query_strings=[query],
            retrieval_timestamp=_timestamp(),
            returned_by_source={source: int(counts.get(source, 0)) for source in sources},
            number_before_deduplication=int(
                metadata.get("number_before_deduplication", len(papers))
            ),
            number_after_deduplication=len(papers),
            publication_date_range=(start_year, end_year),
            source_failures={},
            cache_created_at=_timestamp(created_at),
        )
        return papers, diagnostics
    papers, diagnostics = fetch_papers_detailed(
        query, sources, max_results, start_year, end_year
    )
    if papers:
        cache.put_entry(key, papers, asdict(diagnostics))
    return papers, diagnostics


class PaperCache:
    """Small JSON response cache; runtime directory is ignored by Git."""

    def __init__(self, directory: Path):
        self.directory = directory

    def get(self, key: str, max_age: int = SETTINGS.cache_ttl_seconds) -> list[Paper] | None:
        entry = self.get_entry(key, max_age)
        return entry[0] if entry else None

    def get_entry(
        self, key: str, max_age: int = SETTINGS.cache_ttl_seconds
    ) -> tuple[list[Paper], dict[str, object], float] | None:
        path = self.directory / f"{fingerprint(key)}.json"
        if not path.exists() or time.time() - path.stat().st_mtime > max_age:
            return None
        payload = json.loads(path.read_text())
        if isinstance(payload, list):
            return [Paper(**item) for item in payload], {}, path.stat().st_mtime
        return (
            [Paper(**item) for item in payload.get("papers", [])],
            payload.get("diagnostics", {}),
            path.stat().st_mtime,
        )

    def put(self, key: str, papers: list[Paper]) -> None:
        self.put_entry(key, papers, {})

    def put_entry(
        self, key: str, papers: list[Paper], diagnostics: dict[str, object]
    ) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / f"{fingerprint(key)}.json").write_text(
            json.dumps({
                "papers": [asdict(paper) for paper in papers],
                "diagnostics": diagnostics,
            }, indent=2)
        )
