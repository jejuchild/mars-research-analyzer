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

# Search keywords by field — focused on Mars-specific terms
KEYWORDS = {
    "planetary_science": [
        "Mars subsurface ice detection",
        "Martian surface geology",
        "Martian periglacial landforms",
        "Mars thermal inertia",
        "Arcadia Planitia",
        "Mars water ice",
        "Mars habitability",
        "Jezero crater Mars",
    ],
    "satellite": [
        "Mars remote sensing",
        "CRISM mineral classification Mars",
        "HiRISE Mars terrain",
        "SHARAD radar Mars",
        "Mars SAR synthetic aperture radar",
        "Mars reconnaissance orbiter",
        "THEMIS Mars",
        "MOLA Mars topography",
    ],
    "computer_science": [
        "machine learning Mars surface",
        "deep learning Mars crater",
        "Mars terrain classification neural network",
        "Mars image segmentation",
        "autonomous navigation Mars rover",
        "computer vision Mars",
        "Mars spectral analysis machine learning",
        "crater detection deep learning",
    ],
}

# Combined search queries (cross-field)
CROSS_FIELD_QUERIES = [
    "CRISM machine learning mineral classification",
    "HiRISE deep learning terrain",
    "Mars rover autonomous navigation AI",
    "Mars surface classification deep learning",
    "SHARAD subsurface radar machine learning",
    "Mars spectral unmixing neural network",
    "Mars thermal inertia remote sensing mapping",
    "Perseverance rover image analysis",
]

# Relevance filter — paper must mention at least one of these in title or abstract
RELEVANCE_KEYWORDS = [
    "mars", "martian", "perseverance", "curiosity rover", "ingenuity",
    "jezero", "arcadia planitia", "crism", "hirise", "sharad", "mola",
    "themis", "mons", "maven", "insight lander",
]

# Rate limits are now managed per-collector with exponential backoff.
# See collector/retry.py and each collector's BETWEEN_*_DELAY constants.

# BERTopic minimum documents for modeling
MIN_DOCS_FOR_TOPIC_MODEL = 100
