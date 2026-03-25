"""Author and institution co-authorship network analysis."""

import json
import logging
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)


def analyze_authors(papers: list[dict]) -> dict:
    """Analyze author productivity and collaboration patterns."""
    author_papers = defaultdict(list)
    author_citations = Counter()
    coauthor_pairs = Counter()

    for paper in papers:
        authors_raw = paper.get("authors", "[]")
        if isinstance(authors_raw, str):
            authors = json.loads(authors_raw)
        else:
            authors = authors_raw

        if not authors:
            continue

        for author in authors:
            author_papers[author].append(paper.get("title", ""))
            author_citations[author] += paper.get("citation_count", 0) or 0

        # Co-authorship pairs
        for i in range(len(authors)):
            for j in range(i + 1, len(authors)):
                pair = tuple(sorted([authors[i], authors[j]]))
                coauthor_pairs[pair] += 1

    # Top authors by paper count
    top_authors_by_count = sorted(
        author_papers.items(),
        key=lambda x: len(x[1]),
        reverse=True,
    )[:30]

    # Top authors by citation
    top_authors_by_citation = author_citations.most_common(30)

    # Top co-author pairs
    top_coauthor_pairs = coauthor_pairs.most_common(30)

    return {
        "top_authors_by_count": [
            {"name": name, "paper_count": len(titles), "sample_titles": titles[:3]}
            for name, titles in top_authors_by_count
        ],
        "top_authors_by_citation": [
            {"name": name, "total_citations": count}
            for name, count in top_authors_by_citation
        ],
        "top_coauthor_pairs": [
            {"authors": list(pair), "collaborations": count}
            for pair, count in top_coauthor_pairs
        ],
        "total_unique_authors": len(author_papers),
    }


def analyze_venues(papers: list[dict]) -> dict:
    """Analyze publication venues."""
    venue_counter = Counter()
    venue_citations = defaultdict(int)

    for paper in papers:
        venue = paper.get("venue", "")
        if venue:
            venue_counter[venue] += 1
            venue_citations[venue] += paper.get("citation_count", 0) or 0

    top_venues = venue_counter.most_common(30)

    return {
        "top_venues": [
            {
                "name": name,
                "paper_count": count,
                "total_citations": venue_citations[name],
                "avg_citations": round(venue_citations[name] / count, 1) if count else 0,
            }
            for name, count in top_venues
        ],
        "total_venues": len(venue_counter),
    }
