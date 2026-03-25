"""OpenAlex API collector."""

import time
import logging
from typing import Generator

from config import KEYWORDS, CROSS_FIELD_QUERIES, YEAR_START, YEAR_END, CONTACT_EMAIL
from collector.retry import request_with_retry

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openalex.org/works"

# OpenAlex is generous but let's be polite
BETWEEN_PAGES_DELAY = 1.0
BETWEEN_QUERIES_DELAY = 2.0


def _search(query: str, year_start: int, year_end: int) -> list[dict]:
    """Search OpenAlex for papers."""
    papers = []
    cursor = "*"
    max_results = 500

    while len(papers) < max_results:
        params = {
            "search": query,
            "filter": f"publication_year:{year_start}-{year_end},type:article",
            "select": "id,title,doi,publication_year,cited_by_count,authorships,primary_location,abstract_inverted_index",
            "per_page": 100,
            "cursor": cursor,
            "mailto": CONTACT_EMAIL,
        }

        resp = request_with_retry(
            "GET", BASE_URL,
            params=params,
            base_delay=3.0,
            max_retries=5,
        )

        if resp is None or resp.status_code != 200:
            logger.error(f"OpenAlex failed for '{query}'")
            break

        try:
            data = resp.json()
        except Exception:
            logger.error(f"Failed to parse JSON for '{query}'")
            break

        results = data.get("results", [])
        if not results:
            break

        papers.extend(results)

        meta = data.get("meta", {})
        cursor = meta.get("next_cursor")
        if not cursor:
            break

        time.sleep(BETWEEN_PAGES_DELAY)

    return papers


def _reconstruct_abstract(inverted_index: dict) -> str:
    """Reconstruct abstract from OpenAlex inverted index format."""
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort()
    return " ".join(w for _, w in word_positions)


def _normalize(paper: dict) -> dict:
    """Normalize OpenAlex paper to common format."""
    doi_raw = paper.get("doi", "") or ""
    doi = doi_raw.replace("https://doi.org/", "") if doi_raw else ""

    authors = []
    for authorship in (paper.get("authorships") or []):
        author_info = authorship.get("author", {})
        name = author_info.get("display_name", "")
        if name:
            authors.append(name)

    venue = ""
    primary = paper.get("primary_location") or {}
    source = primary.get("source") or {}
    venue = source.get("display_name", "")

    pdf_url = ""
    if primary.get("is_oa"):
        pdf_url = primary.get("pdf_url", "") or ""

    abstract = _reconstruct_abstract(paper.get("abstract_inverted_index"))
    openalex_id = paper.get("id", "").split("/")[-1]

    return {
        "id": f"oa_{openalex_id}",
        "title": paper.get("title", "") or "",
        "abstract": abstract,
        "authors": authors,
        "year": paper.get("publication_year"),
        "venue": venue,
        "doi": doi,
        "source": "openalex",
        "fields": [],
        "citation_count": paper.get("cited_by_count", 0),
        "pdf_url": pdf_url,
    }


def collect() -> Generator[dict, None, None]:
    """Collect papers from OpenAlex."""
    seen_ids = set()

    for field, keywords in KEYWORDS.items():
        for kw in keywords:
            logger.info(f"[OpenAlex] Searching: {kw}")
            papers = _search(kw, YEAR_START, YEAR_END)
            for p in papers:
                oa_id = p.get("id", "")
                if oa_id in seen_ids:
                    continue
                seen_ids.add(oa_id)
                normalized = _normalize(p)
                normalized["fields"].append(field)
                yield normalized

            time.sleep(BETWEEN_QUERIES_DELAY)

    for query in CROSS_FIELD_QUERIES:
        logger.info(f"[OpenAlex] Cross-field: {query}")
        papers = _search(query, YEAR_START, YEAR_END)
        for p in papers:
            oa_id = p.get("id", "")
            if oa_id in seen_ids:
                continue
            seen_ids.add(oa_id)
            normalized = _normalize(p)
            normalized["fields"].append("cross_field")
            yield normalized

        time.sleep(BETWEEN_QUERIES_DELAY)
