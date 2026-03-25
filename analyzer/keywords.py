"""Keyword extraction and frequency analysis."""

import json
import logging
import re
from collections import Counter

logger = logging.getLogger(__name__)

# Stop words to filter out
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "this", "that",
    "these", "those", "it", "its", "we", "our", "they", "their", "them",
    "which", "who", "whom", "what", "where", "when", "how", "than",
    "not", "no", "nor", "as", "if", "then", "so", "up", "out", "about",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "each", "all", "both", "few", "more", "most", "other",
    "some", "such", "only", "own", "same", "also", "very", "just",
    "over", "under", "again", "further", "here", "there", "once",
    "using", "used", "based", "show", "shown", "shows", "study",
    "results", "paper", "however", "thus", "therefore", "et", "al",
    "fig", "figure", "table", "data", "method", "methods", "approach",
    "two", "one", "new", "first", "well", "also", "can", "may",
}

# Noise tokens to strip (MathML remnants, markup artifacts)
NOISE_TOKENS = {
    "mml", "mrow", "msup", "msub", "mtext", "mfrac", "xmlns", "mathml",
    "http", "https", "www", "org", "com", "doi", "sub", "sup",
    "alttext", "altimg", "mathvariant", "stretchy", "false", "true",
    "crossref", "pdf", "html", "xml", "href", "xlink",
}


def clean_text(text: str) -> str:
    """Clean text by removing HTML tags, MathML, URLs, and markup artifacts."""
    # Remove HTML/XML tags (including MathML like <mml:mrow>, <sub>, <sup>)
    text = re.sub(r'<[^>]+>', ' ', text)
    # Remove URLs
    text = re.sub(r'https?://\S+', ' ', text)
    # Remove xmlns and namespace declarations
    text = re.sub(r'xmlns[:\w]*="[^"]*"', ' ', text)
    # Remove leftover XML/HTML entities
    text = re.sub(r'&[a-z]+;', ' ', text)
    # Remove standalone numbers and math symbols
    text = re.sub(r'\b\d+\.?\d*\b', ' ', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_ngrams(text: str, n: int = 2) -> list[str]:
    """Extract n-grams from cleaned text."""
    text = clean_text(text)
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    words = [w for w in words if w not in STOP_WORDS and w not in NOISE_TOKENS]

    if n == 1:
        return words

    ngrams = []
    for i in range(len(words) - n + 1):
        ngram = " ".join(words[i:i + n])
        ngrams.append(ngram)
    return ngrams


def analyze_keywords(papers: list[dict]) -> dict:
    """Analyze keyword frequencies across papers."""
    unigram_counter = Counter()
    bigram_counter = Counter()
    trigram_counter = Counter()

    yearly_keywords = {}

    for paper in papers:
        text = f"{paper.get('title', '')} {paper.get('abstract', '')}"
        if not text.strip():
            continue

        year = paper.get("year")

        unigrams = extract_ngrams(text, 1)
        bigrams = extract_ngrams(text, 2)
        trigrams = extract_ngrams(text, 3)

        unigram_counter.update(unigrams)
        bigram_counter.update(bigrams)
        trigram_counter.update(trigrams)

        if year:
            if year not in yearly_keywords:
                yearly_keywords[year] = Counter()
            yearly_keywords[year].update(bigrams)

    return {
        "unigrams": unigram_counter.most_common(50),
        "bigrams": bigram_counter.most_common(50),
        "trigrams": trigram_counter.most_common(50),
        "yearly_top_bigrams": {
            year: counter.most_common(20)
            for year, counter in sorted(yearly_keywords.items())
        },
    }


def analyze_field_keywords(papers: list[dict]) -> dict:
    """Analyze keywords by field category."""
    field_counters = {}

    for paper in papers:
        text = f"{paper.get('title', '')} {paper.get('abstract', '')}"
        fields_raw = paper.get("fields", "[]")
        if isinstance(fields_raw, str):
            fields = json.loads(fields_raw)
        else:
            fields = fields_raw

        bigrams = extract_ngrams(text, 2)

        for field in fields:
            if field not in field_counters:
                field_counters[field] = Counter()
            field_counters[field].update(bigrams)

    return {
        field: counter.most_common(30)
        for field, counter in field_counters.items()
    }
