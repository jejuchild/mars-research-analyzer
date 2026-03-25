"""Semantic Scholar API collector."""

import time
import logging
from typing import Generator

from config import (
    KEYWORDS,
    CROSS_FIELD_QUERIES,
    YEAR_START,
    YEAR_END,
    SEMANTIC_SCHOLAR_API_KEY,
)
from collector.retry import request_with_retry

logger = logging.getLogger(__name__)

BASE_URL = "https://api.semanticscholar.org/graph/v1"
FIELDS = "paperId,title,abstract,authors,year,venue,externalIds,citationCount,openAccessPdf"

# S2 free tier: very strict. Must space out heavily.
BETWEEN_PAGES_DELAY = 10.0
BETWEEN_QUERIES_DELAY = 15.0
PAGE_LIMIT = 50  # smaller pages to reduce burst


def _headers():
    h = {"Accept": "application/json"}
    if SEMANTIC_SCHOLAR_API_KEY:
        h["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY
    return h


def _search(query: str, year_range: str) -> list[dict]:
    """Search Semantic Scholar for papers matching query."""
    papers = []
    offset = 0
    max_results = 200  # reduced cap to avoid sustained rate limiting

    while offset < max_results:
        batch = min(PAGE_LIMIT, max_results - offset)
        params = {
            "query": query,
            "year": year_range,
            "fields": FIELDS,
            "offset": offset,
            "limit": batch,
        }

        resp = request_with_retry(
            "GET",
            f"{BASE_URL}/paper/search",
            params=params,
            headers=_headers(),
            base_delay=30.0,
            max_retries=6,
            max_delay=300.0,
        )

        if resp is None:
            logger.error(f"Failed to fetch results for '{query}' at offset {offset}")
            break

        if resp.status_code != 200:
            logger.error(f"S2 returned {resp.status_code} for '{query}'")
            break

        try:
            data = resp.json()
        except Exception:
            logger.error(f"Failed to parse JSON for '{query}'")
            break

        results = data.get("data", [])
        if not results:
            break

        papers.extend(results)
        total = data.get("total", 0)
        offset += len(results)

        if offset >= total:
            break

        time.sleep(BETWEEN_PAGES_DELAY)

    return papers


def _normalize(paper: dict) -> dict:
    """Normalize Semantic Scholar paper to common format."""
    ext_ids = paper.get("externalIds") or {}
    pdf_info = paper.get("openAccessPdf") or {}

    authors = []
    for a in (paper.get("authors") or []):
        authors.append(a.get("name", ""))

    return {
        "id": f"s2_{paper['paperId']}",
        "title": paper.get("title", ""),
        "abstract": paper.get("abstract", ""),
        "authors": authors,
        "year": paper.get("year"),
        "venue": paper.get("venue", ""),
        "doi": ext_ids.get("DOI", ""),
        "source": "semantic_scholar",
        "fields": [],
        "citation_count": paper.get("citationCount", 0),
        "pdf_url": pdf_info.get("url", ""),
    }


def collect() -> Generator[dict, None, None]:
    """Collect papers from Semantic Scholar."""
    year_range = f"{YEAR_START}-{YEAR_END}"
    seen_ids = set()

    # Search by field keywords
    for field, keywords in KEYWORDS.items():
        for kw in keywords:
            logger.info(f"[S2] Searching: {kw}")
            papers = _search(kw, year_range)
            for p in papers:
                pid = p["paperId"]
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)
                normalized = _normalize(p)
                normalized["fields"].append(field)
                yield normalized

            time.sleep(BETWEEN_QUERIES_DELAY)

    # Cross-field queries
    for query in CROSS_FIELD_QUERIES:
        logger.info(f"[S2] Cross-field search: {query}")
        papers = _search(query, year_range)
        for p in papers:
            pid = p["paperId"]
            if pid in seen_ids:
                continue
            seen_ids.add(pid)
            normalized = _normalize(p)
            normalized["fields"].append("cross_field")
            yield normalized

        time.sleep(BETWEEN_QUERIES_DELAY)
