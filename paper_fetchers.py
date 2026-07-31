"""Legal OpenAlex and arXiv adapters with retries, caching, and deduplication."""

from __future__ import annotations

import json
import time
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path
from typing import Callable

import requests

from config import SETTINGS
from models import Paper
from text_processing import fingerprint, normalized_title


class PaperFetchError(RuntimeError):
    """Raised when one paper source fails after bounded retries."""


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
    adapters = adapters or {"openalex": fetch_openalex, "arxiv": fetch_arxiv}
    papers: list[Paper] = []
    failures: dict[str, str] = {}
    per_source = max(1, max_results // max(1, len(sources)))
    for source in sources:
        try:
            papers.extend(adapters[source](query, per_source, start_year, end_year))
        except (PaperFetchError, KeyError, ValueError, ET.ParseError) as exc:
            failures[source] = str(exc)
        time.sleep(SETTINGS.rate_limit_seconds)
    return deduplicate_papers(papers)[:max_results], failures


def fetch_papers_cached(query: str, sources: list[str], max_results: int = 20,
                        start_year: int = 2021, end_year: int = 2026,
                        cache_directory: Path = Path(".paper_cache")
                        ) -> tuple[list[Paper], dict[str, str]]:
    """Use a local response cache before contacting public sources."""
    cache = PaperCache(cache_directory)
    key = json.dumps([query, sorted(sources), max_results, start_year, end_year])
    cached = cache.get(key)
    if cached is not None:
        return cached, {}
    papers, failures = fetch_papers(query, sources, max_results, start_year, end_year)
    if papers:
        cache.put(key, papers)
    return papers, failures


class PaperCache:
    """Small JSON response cache; runtime directory is ignored by Git."""

    def __init__(self, directory: Path):
        self.directory = directory

    def get(self, key: str, max_age: int = SETTINGS.cache_ttl_seconds) -> list[Paper] | None:
        path = self.directory / f"{fingerprint(key)}.json"
        if not path.exists() or time.time() - path.stat().st_mtime > max_age:
            return None
        return [Paper(**item) for item in json.loads(path.read_text())]

    def put(self, key: str, papers: list[Paper]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / f"{fingerprint(key)}.json").write_text(
            json.dumps([asdict(paper) for paper in papers], indent=2)
        )
