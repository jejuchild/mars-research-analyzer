"""Configuration for Mars Research Analyzer."""

import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
PDF_DIR = DATA_DIR / "pdfs"
DB_PATH = DATA_DIR / "papers.db"
REPORT_DIR = PROJECT_ROOT / "reports"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
PDF_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)

# Date range
YEAR_START = 2023
YEAR_END = 2026

# SNU Library Proxy
SNU_PROXY_PREFIX = "https://libproxy.snu.ac.kr/link.n2s?url="

# Contact email for polite API access
CONTACT_EMAIL = "research@snu.ac.kr"

# API Keys
NASA_ADS_API_KEY = os.environ.get("NASA_ADS_API_KEY", "")
SEMANTIC_SCHOLAR_API_KEY = os.environ.get("S2_API_KEY", "")

# Search keywords by field
KEYWORDS = {
    "planetary_science": [
        "Mars exploration",
        "Mars rover",
        "Mars surface",
        "Martian atmosphere",
        "Mars geology",
        "Mars mineralogy",
        "Mars water",
        "Mars habitability",
    ],
    "satellite": [
        "Mars orbiter",
        "Mars reconnaissance orbiter",
        "satellite remote sensing Mars",
        "Mars spacecraft",
        "Mars mission",
        "Mars Express",
        "MAVEN Mars",
        "Tianwen Mars",
    ],
    "computer_science": [
        "machine learning Mars",
        "deep learning planetary",
        "autonomous navigation Mars",
        "computer vision Mars",
        "AI space exploration",
        "neural network crater",
        "image classification Mars",
        "terrain analysis Mars",
    ],
}

# Combined search queries (cross-field)
CROSS_FIELD_QUERIES = [
    "Mars machine learning remote sensing",
    "Mars rover autonomous navigation AI",
    "Mars surface classification deep learning",
    "crater detection neural network",
    "Mars spectral analysis machine learning",
    "planetary data science Mars",
    "Mars image segmentation",
    "Mars terrain mapping computer vision",
]

# Rate limits are now managed per-collector with exponential backoff.
# See collector/retry.py and each collector's BETWEEN_*_DELAY constants.

# BERTopic minimum documents for modeling
MIN_DOCS_FOR_TOPIC_MODEL = 100
