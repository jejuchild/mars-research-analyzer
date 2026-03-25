"""NASA ADS API collector."""

import time
import logging
from typing import Generator

from config import KEYWORDS, CROSS_FIELD_QUERIES, YEAR_START, YEAR_END, NASA_ADS_API_KEY
from collector.retry import request_with_retry

logger = logging.getLogger(__name__)

BASE_URL = "https://api.adsabs.harvard.edu/v1/search/query"

BETWEEN_PAGES_DELAY = 3.0
BETWEEN_QUERIES_DELAY = 5.0


def _search(query: str, year_start: int, year_end: int) -> list[dict]:
    """Search NASA ADS."""
    if not NASA_ADS_API_KEY:
        logger.warning("[ADS] No API key set (NASA_ADS_API_KEY). Skipping.")
        return []

    papers = []
    start = 0
    max_results = 500

    headers = {
        "Authorization": f"Bearer {NASA_ADS_API_KEY}",
        "Accept": "application/json",
    }

    while start < max_results:
        params = {
            "q": query,
            "fq": f"year:[{year_start} TO {year_end}]",
            "fl": "bibcode,title,abstract,author,year,pub,doi,citation_count,property",
            "rows": 100,
            "start": start,
            "sort": "citation_count desc",
        }

        resp = request_with_retry(
            "GET", BASE_URL,
            params=params,
            headers=headers,
            base_delay=5.0,
            max_retries=5,
        )

        if resp is None:
            logger.error(f"ADS request failed for '{query}'")
            break

        if resp.status_code == 401:
            logger.error("[ADS] Invalid API key")
            return []

        if resp.status_code != 200:
            logger.error(f"ADS returned {resp.status_code} for '{query}'")
            break

        try:
            data = resp.json()
        except Exception:
            logger.error(f"Failed to parse JSON for '{query}'")
            break

        response = data.get("response", {})
        docs = response.get("docs", [])
        if not docs:
            break

        papers.extend(docs)
        num_found = response.get("numFound", 0)
        start += len(docs)

        if start >= num_found:
            break

        time.sleep(BETWEEN_PAGES_DELAY)

    return papers


def _normalize(paper: dict) -> dict:
    """Normalize ADS paper to common format."""
    bibcode = paper.get("bibcode", "")
    dois = paper.get("doi") or []
    doi = dois[0] if dois else ""

    titles = paper.get("title") or []
    title = titles[0] if titles else ""

    props = paper.get("property") or []
    pdf_url = ""
    if "OPENACCESS" in props and bibcode:
        pdf_url = f"https://ui.adsabs.harvard.edu/link_gateway/{bibcode}/EPRINT_PDF"

    return {
        "id": f"ads_{bibcode}",
        "title": title,
        "abstract": paper.get("abstract", "") or "",
        "authors": paper.get("author", []),
        "year": int(paper["year"]) if paper.get("year") else None,
        "venue": paper.get("pub", ""),
        "doi": doi,
        "source": "nasa_ads",
        "fields": [],
        "citation_count": paper.get("citation_count", 0) or 0,
        "pdf_url": pdf_url,
    }


def collect() -> Generator[dict, None, None]:
    """Collect papers from NASA ADS."""
    if not NASA_ADS_API_KEY:
        logger.warning("[ADS] Skipping — no API key. Set NASA_ADS_API_KEY env var.")
        logger.warning("[ADS] Get one at: https://ui.adsabs.harvard.edu/user/settings/token")
        return

    seen_ids = set()

    for field, keywords in KEYWORDS.items():
        for kw in keywords:
            ads_query = f'abs:"{kw}" OR title:"{kw}"'
            logger.info(f"[ADS] Searching: {kw}")
            papers = _search(ads_query, YEAR_START, YEAR_END)
            for p in papers:
                bib = p.get("bibcode", "")
                if bib in seen_ids:
                    continue
                seen_ids.add(bib)
                normalized = _normalize(p)
                normalized["fields"].append(field)
                yield normalized

            time.sleep(BETWEEN_QUERIES_DELAY)

    for query in CROSS_FIELD_QUERIES:
        ads_query = f'abs:"{query}" OR title:"{query}"'
        logger.info(f"[ADS] Cross-field: {query}")
        papers = _search(ads_query, YEAR_START, YEAR_END)
        for p in papers:
            bib = p.get("bibcode", "")
            if bib in seen_ids:
                continue
            seen_ids.add(bib)
            normalized = _normalize(p)
            normalized["fields"].append("cross_field")
            yield normalized

        time.sleep(BETWEEN_QUERIES_DELAY)
