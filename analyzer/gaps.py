"""Research gap and open problem detection.

Analyzes paper abstracts to identify:
- Unsolved problems and challenges mentioned in the literature
- Future work directions suggested by researchers
- Limitations acknowledged by authors
- Emerging questions that don't yet have answers
"""

import json
import logging
import re
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)

# Patterns indicating research gaps, challenges, and open problems
GAP_PATTERNS = [
    # Explicit challenges
    (r"(?:remains?|still)\s+(?:a\s+)?(?:major\s+)?(?:challenge|difficult|unclear|unknown|unresolved|open\s+(?:question|problem))", "challenge"),
    (r"(?:key|major|significant|critical|important)\s+challenge", "challenge"),
    (r"challenging\s+(?:to|for|due\s+to)", "challenge"),
    # Limitations
    (r"(?:however|but|although),?\s+(?:the\s+)?(?:current|existing|previous)\s+(?:methods?|approaches?|techniques?|studies?)\s+(?:are|have|suffer|lack|fail)", "limitation"),
    (r"limit(?:ation|ed|ing)\s+(?:of|by|in|to)", "limitation"),
    (r"(?:poor|low|insufficient|inadequate)\s+(?:accuracy|resolution|coverage|performance|understanding)", "limitation"),
    # Future work
    (r"future\s+(?:work|research|studies?|investigations?|efforts?)\s+(?:should|could|will|may|might|is\s+needed)", "future_work"),
    (r"(?:further|additional|more)\s+(?:research|investigation|study|analysis|work)\s+is\s+(?:needed|required|necessary)", "future_work"),
    (r"(?:remains?\s+to\s+be\s+(?:determined|investigated|explored|understood))", "future_work"),
    # Knowledge gaps
    (r"(?:little|not\s+(?:well|fully|clearly))\s+(?:known|understood|explored|investigated|studied)", "knowledge_gap"),
    (r"gap\s+(?:in|between|exists?)", "knowledge_gap"),
    (r"lack\s+of\s+(?:understanding|knowledge|data|studies|research)", "knowledge_gap"),
    # Open questions
    (r"(?:open|unresolved|unanswered)\s+question", "open_question"),
    (r"(?:debate|controversy|disagreement)\s+(?:about|over|regarding|on)", "open_question"),
    (r"(?:unclear|uncertain)\s+(?:whether|how|why|what)", "open_question"),
    # Needs
    (r"(?:there\s+is\s+)?(?:a\s+)?(?:pressing|urgent|critical|growing)?\s*need\s+(?:for|to)", "need"),
    (r"(?:required|necessary|essential)\s+(?:for|to)\s+(?:improve|advance|develop|address)", "need"),
]


def _extract_context(text: str, match_start: int, match_end: int, window: int = 200) -> str:
    """Extract surrounding context for a pattern match."""
    # Find sentence boundaries
    start = max(0, match_start - window)
    end = min(len(text), match_end + window)

    # Try to snap to sentence boundaries
    snippet = text[start:end]

    # Find the sentence containing the match
    sentences = re.split(r'(?<=[.!?])\s+', snippet)
    match_pos_in_snippet = match_start - start

    current_pos = 0
    for sent in sentences:
        sent_end = current_pos + len(sent)
        if current_pos <= match_pos_in_snippet <= sent_end:
            return sent.strip()
        current_pos = sent_end + 1

    return snippet.strip()


def detect_gaps(papers: list[dict]) -> dict:
    """Detect research gaps and open problems from paper abstracts."""
    gap_instances = defaultdict(list)
    gap_type_counts = Counter()
    papers_with_gaps = 0

    compiled_patterns = [
        (re.compile(pattern, re.IGNORECASE), gap_type)
        for pattern, gap_type in GAP_PATTERNS
    ]

    for paper in papers:
        abstract = paper.get("abstract", "")
        if not abstract or len(abstract) < 50:
            continue

        title = paper.get("title", "")
        text = f"{title}. {abstract}"
        paper_has_gap = False

        for regex, gap_type in compiled_patterns:
            for match in regex.finditer(text):
                context = _extract_context(text, match.start(), match.end())
                if len(context) < 20:
                    continue

                paper_has_gap = True
                gap_type_counts[gap_type] += 1
                gap_instances[gap_type].append({
                    "paper_title": title,
                    "year": paper.get("year"),
                    "matched_text": match.group(),
                    "context": context,
                    "citations": paper.get("citation_count", 0),
                    "doi": paper.get("doi", ""),
                    "abstract": abstract,
                })

        if paper_has_gap:
            papers_with_gaps += 1

    # Sort each gap type by citations (most cited = most acknowledged gap)
    for gap_type in gap_instances:
        gap_instances[gap_type].sort(
            key=lambda x: x["citations"] or 0, reverse=True
        )

    # Cluster similar gaps by extracting key phrases
    gap_themes = _cluster_gap_themes(gap_instances)

    return {
        "total_papers_analyzed": len(papers),
        "papers_with_gaps": papers_with_gaps,
        "gap_type_counts": dict(gap_type_counts),
        "gap_instances": {
            gap_type: instances[:15]  # Top 15 per type
            for gap_type, instances in gap_instances.items()
        },
        "gap_themes": gap_themes,
    }


def _cluster_gap_themes(gap_instances: dict) -> list[dict]:
    """Group similar research gaps into themes."""
    all_contexts = []
    for gap_type, instances in gap_instances.items():
        for inst in instances:
            all_contexts.append({
                "context": inst["context"],
                "type": gap_type,
                "citations": inst["citations"],
                "title": inst["paper_title"],
            })

    if not all_contexts:
        return []

    # Simple keyword-based clustering
    theme_keywords = Counter()
    from analyzer.keywords import extract_ngrams

    for item in all_contexts:
        bigrams = extract_ngrams(item["context"], 2)
        theme_keywords.update(bigrams)

    # Top themes
    themes = []
    for phrase, count in theme_keywords.most_common(20):
        if count < 2:
            break
        related = [
            item for item in all_contexts
            if phrase in item["context"].lower()
        ]
        themes.append({
            "theme": phrase,
            "mention_count": count,
            "gap_types": list(set(r["type"] for r in related)),
            "example_papers": [r["title"] for r in related[:3]],
            "avg_citations": round(
                sum(r["citations"] or 0 for r in related) / len(related), 1
            ) if related else 0,
        })

    return themes
