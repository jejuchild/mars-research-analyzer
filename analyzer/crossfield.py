"""Cross-field intersection analysis: planetary science × satellite × CS."""

import json
import logging
import re
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)

# Venue-based field classification (priority over keyword-based)
VENUE_FIELDS = {
    "planetary_science": [
        "journal of geophysical research planets",
        "journal of geophysical research: planets",
        "icarus",
        "the planetary science journal",
        "planetary science journal",
        "astrobiology",
        "earth and planetary science letters",
        "geophysical research letters",
        "meteoritics and planetary science",
        "meteoritics & planetary science",
        "the astrophysical journal",
        "astrophysical journal",
        "astronomy & astrophysics",
        "astronomy and astrophysics",
        "planetary and space science",
        "journal of geophysical research space physics",
        "space science reviews",
        "nature geoscience",
        "nature astronomy",
    ],
    "satellite": [
        "ieee transactions on geoscience and remote sensing",
        "remote sensing",
        "remote sensing of environment",
        "international journal of remote sensing",
        "isprs journal of photogrammetry and remote sensing",
        "acta astronautica",
        "journal of spacecraft and rockets",
        "ieee geoscience and remote sensing letters",
        "advances in space research",
        "journal of applied remote sensing",
        "giscience & remote sensing",
        "sensors",
    ],
    "computer_science": [
        "ieee transactions on pattern analysis and machine intelligence",
        "ieee transactions on neural networks and learning systems",
        "neurips",
        "cvpr",
        "iccv",
        "eccv",
        "icml",
        "iclr",
        "acm computing surveys",
        "artificial intelligence",
        "pattern recognition",
        "neural networks",
        "ieee transactions on image processing",
        "computer vision and image understanding",
        "machine learning",
        "journal of machine learning research",
    ],
}

# Keyword-based field detection (fallback when venue doesn't match)
FIELD_INDICATORS = {
    "planetary_science": [
        "mars", "martian", "crater", "mineral", "geology", "atmosphere",
        "regolith", "dust", "olivine", "basalt", "phyllosilicate",
        "habitability", "astrobiology", "meteorite", "volcanism",
        "jezero", "gale crater", "arcadia", "olympus",
    ],
    "satellite": [
        "orbiter", "satellite", "remote sensing", "hirise", "crism",
        "themis", "mro", "maven", "spacecraft", "lander", "rover",
        "perseverance", "curiosity", "zhurong", "tianwen", "ingenuity",
        "sharad", "mola", "insight",
    ],
    "computer_science": [
        "machine learning", "deep learning", "neural network", "cnn",
        "transformer", "classification", "segmentation", "detection",
        "autonomous", "reinforcement learning", "computer vision",
        "convolutional", "generative", "artificial intelligence",
        "random forest", "support vector", "clustering", "autoencoder",
    ],
}


def _detect_fields_by_venue(venue: str) -> list[str]:
    """Detect fields based on publication venue."""
    if not venue:
        return []
    venue_lower = venue.lower().strip()
    detected = []
    for field, venues in VENUE_FIELDS.items():
        for v in venues:
            if v in venue_lower or venue_lower in v:
                detected.append(field)
                break
    return detected


def _detect_fields_by_keywords(paper: dict) -> list[str]:
    """Detect fields based on title/abstract keywords."""
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    detected = []
    for field, indicators in FIELD_INDICATORS.items():
        for indicator in indicators:
            if indicator in text:
                detected.append(field)
                break
    return detected


def _detect_fields(paper: dict) -> list[str]:
    """Detect fields: venue-based first, then keyword-based fallback."""
    venue = paper.get("venue", "")
    venue_fields = _detect_fields_by_venue(venue)
    keyword_fields = _detect_fields_by_keywords(paper)

    # Merge: venue fields take priority, add keyword fields not already present
    all_fields = list(venue_fields)
    for f in keyword_fields:
        if f not in all_fields:
            all_fields.append(f)

    return all_fields


def analyze_crossfield(papers: list[dict]) -> dict:
    """Analyze intersection of fields across papers."""
    field_papers = defaultdict(list)
    multi_field_papers = []
    field_combos = Counter()

    for paper in papers:
        fields = _detect_fields(paper)
        if not fields:
            continue

        for field in fields:
            field_papers[field].append(paper)

        if len(fields) >= 2:
            multi_field_papers.append({
                "title": paper.get("title", ""),
                "year": paper.get("year"),
                "fields": fields,
                "citations": paper.get("citation_count", 0),
                "doi": paper.get("doi", ""),
                "venue": paper.get("venue", ""),
            })
            combo = tuple(sorted(fields))
            field_combos[combo] += 1

    multi_field_papers.sort(key=lambda x: x["citations"] or 0, reverse=True)

    triple_intersection = [
        p for p in multi_field_papers
        if len(p["fields"]) == 3
    ]

    pairwise = {}
    pairs = [
        ("planetary_science", "computer_science"),
        ("planetary_science", "satellite"),
        ("satellite", "computer_science"),
    ]
    for f1, f2 in pairs:
        pairwise[f"{f1} × {f2}"] = [
            p for p in multi_field_papers
            if f1 in p["fields"] and f2 in p["fields"]
        ]

    return {
        "field_counts": {f: len(ps) for f, ps in field_papers.items()},
        "field_combinations": {
            str(combo): count for combo, count in field_combos.most_common()
        },
        "multi_field_papers_count": len(multi_field_papers),
        "triple_intersection_count": len(triple_intersection),
        "triple_intersection_papers": triple_intersection[:20],
        "pairwise_intersections": {
            key: {"count": len(ps), "top_papers": ps[:10]}
            for key, ps in pairwise.items()
        },
        "top_crossfield_papers": multi_field_papers[:20],
    }
