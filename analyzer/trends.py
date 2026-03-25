"""Yearly trend analysis."""

import json
import logging
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)


def analyze_trends(papers: list[dict]) -> dict:
    """Analyze publication trends over time."""
    yearly_count = Counter()
    yearly_citations = defaultdict(int)
    yearly_fields = defaultdict(lambda: Counter())
    yearly_venues = defaultdict(lambda: Counter())

    for paper in papers:
        year = paper.get("year")
        if not year:
            continue

        yearly_count[year] += 1
        yearly_citations[year] += paper.get("citation_count", 0) or 0

        # Field distribution per year
        fields_raw = paper.get("fields", "[]")
        if isinstance(fields_raw, str):
            fields = json.loads(fields_raw)
        else:
            fields = fields_raw

        for field in fields:
            yearly_fields[year][field] += 1

        venue = paper.get("venue", "")
        if venue:
            yearly_venues[year][venue] += 1

    # Growth rates
    years_sorted = sorted(yearly_count.keys())
    growth = {}
    for i in range(1, len(years_sorted)):
        prev_year = years_sorted[i - 1]
        curr_year = years_sorted[i]
        prev_count = yearly_count[prev_year]
        curr_count = yearly_count[curr_year]
        if prev_count > 0:
            rate = round((curr_count - prev_count) / prev_count * 100, 1)
            growth[curr_year] = rate

    return {
        "yearly_papers": dict(sorted(yearly_count.items())),
        "yearly_citations": dict(sorted(yearly_citations.items())),
        "yearly_avg_citations": {
            year: round(yearly_citations[year] / yearly_count[year], 1)
            if yearly_count[year] > 0 else 0
            for year in years_sorted
        },
        "growth_rates": growth,
        "yearly_field_distribution": {
            year: dict(counter.most_common())
            for year, counter in sorted(yearly_fields.items())
        },
        "yearly_top_venues": {
            year: counter.most_common(5)
            for year, counter in sorted(yearly_venues.items())
        },
    }


def find_emerging_topics(papers: list[dict]) -> list[dict]:
    """Find topics that are growing in recent years compared to earlier."""
    from analyzer.keywords import extract_ngrams

    # Split into early and recent
    early_bigrams = Counter()
    recent_bigrams = Counter()
    early_count = 0
    recent_count = 0

    for paper in papers:
        year = paper.get("year")
        if not year:
            continue
        text = f"{paper.get('title', '')} {paper.get('abstract', '')}"
        bigrams = extract_ngrams(text, 2)

        if year <= 2024:
            early_bigrams.update(bigrams)
            early_count += 1
        else:
            recent_bigrams.update(bigrams)
            recent_count += 1

    if early_count == 0 or recent_count == 0:
        return []

    # Normalize by document count
    emerging = []
    for bigram, recent_freq in recent_bigrams.most_common(200):
        early_freq = early_bigrams.get(bigram, 0)
        recent_norm = recent_freq / recent_count
        early_norm = early_freq / early_count if early_count else 0

        if early_norm > 0:
            growth = (recent_norm - early_norm) / early_norm
        elif recent_freq >= 3:
            growth = float("inf")
        else:
            continue

        if growth > 0.5 and recent_freq >= 3:
            emerging.append({
                "term": bigram,
                "recent_freq": recent_freq,
                "early_freq": early_freq,
                "growth_ratio": round(growth, 2) if growth != float("inf") else "new",
            })

    emerging.sort(key=lambda x: x["recent_freq"], reverse=True)
    return emerging[:30]
