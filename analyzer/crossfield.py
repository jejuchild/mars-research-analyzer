"""Cross-field intersection analysis: planetary science × satellite × CS."""

import json
import logging
import re
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)

# Field detection keywords (used to tag papers that weren't pre-tagged)
FIELD_INDICATORS = {
    "planetary_science": [
        "mars", "martian", "crater", "mineral", "geology", "atmosphere",
        "regolith", "dust", "olivine", "basalt", "phyllosilicate",
        "habitability", "astrobiology", "meteorite", "volcanism",
    ],
    "satellite": [
        "orbiter", "satellite", "remote sensing", "hirise", "crism",
        "themis", "mro", "maven", "spacecraft", "lander", "rover",
        "perseverance", "curiosity", "zhurong", "tianwen", "ingenuity",
    ],
    "computer_science": [
        "machine learning", "deep learning", "neural network", "cnn",
        "transformer", "classification", "segmentation", "detection",
        "autonomous", "reinforcement learning", "computer vision",
        "convolutional", "generative", "artificial intelligence",
        "random forest", "support vector", "clustering", "autoencoder",
    ],
}


def _detect_fields(paper: dict) -> list[str]:
    """Detect which fields a paper belongs to based on content."""
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    detected = []
    for field, indicators in FIELD_INDICATORS.items():
        for indicator in indicators:
            if indicator in text:
                detected.append(field)
                break
    return detected


def analyze_crossfield(papers: list[dict]) -> dict:
    """Analyze intersection of fields across papers."""
    # Re-tag all papers by content
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

    # Sort multi-field papers by citations
    multi_field_papers.sort(key=lambda x: x["citations"] or 0, reverse=True)

    # Find the triple intersection (all 3 fields)
    triple_intersection = [
        p for p in multi_field_papers
        if len(p["fields"]) == 3
    ]

    # Pairwise intersections
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
