"""SQLite database manager for paper storage."""

import json
import re
import sqlite3
from contextlib import contextmanager
from typing import Optional

from config import DB_PATH, RELEVANCE_KEYWORDS

# Pre-compile word-boundary regex for each keyword
_RELEVANCE_PATTERNS = [
    re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
    for kw in RELEVANCE_KEYWORDS
]


def _is_relevant(title: str, abstract: str) -> bool:
    """Check if a paper is relevant to Mars research (word-boundary matching)."""
    text = f"{title} {abstract}"
    return any(pat.search(text) for pat in _RELEVANCE_PATTERNS)


class PaperDB:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    abstract TEXT,
                    authors TEXT,
                    year INTEGER,
                    venue TEXT,
                    doi TEXT,
                    source TEXT,
                    fields TEXT,
                    citation_count INTEGER DEFAULT 0,
                    pdf_url TEXT,
                    pdf_downloaded INTEGER DEFAULT 0,
                    is_relevant INTEGER DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_papers_source ON papers(source)
            """)
            # Add is_relevant column if missing (migration for existing DB)
            try:
                conn.execute("SELECT is_relevant FROM papers LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE papers ADD COLUMN is_relevant INTEGER DEFAULT NULL")

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def insert_paper(self, paper: dict) -> bool:
        """Insert a paper, skip if duplicate (by DOI or ID). Returns True if inserted."""
        if paper.get("doi"):
            existing = self.find_by_doi(paper["doi"])
            if existing:
                return False

        relevant = _is_relevant(paper.get("title", ""), paper.get("abstract", ""))

        with self._conn() as conn:
            try:
                cursor = conn.execute(
                    """INSERT OR IGNORE INTO papers
                    (id, title, abstract, authors, year, venue, doi, source, fields,
                     citation_count, pdf_url, is_relevant)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        paper["id"],
                        paper["title"],
                        paper.get("abstract", ""),
                        json.dumps(paper.get("authors", []), ensure_ascii=False),
                        paper.get("year"),
                        paper.get("venue", ""),
                        paper.get("doi", ""),
                        paper.get("source", ""),
                        json.dumps(paper.get("fields", []), ensure_ascii=False),
                        paper.get("citation_count", 0),
                        paper.get("pdf_url", ""),
                        1 if relevant else 0,
                    ),
                )
                return cursor.rowcount > 0
            except sqlite3.IntegrityError:
                return False

    def backfill_relevance(self) -> dict:
        """Tag existing papers with is_relevant flag. Returns counts."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, title, abstract FROM papers WHERE is_relevant IS NULL"
            ).fetchall()

            tagged = 0
            relevant = 0
            for row in rows:
                is_rel = _is_relevant(row["title"] or "", row["abstract"] or "")
                conn.execute(
                    "UPDATE papers SET is_relevant = ? WHERE id = ?",
                    (1 if is_rel else 0, row["id"]),
                )
                tagged += 1
                if is_rel:
                    relevant += 1

            return {"tagged": tagged, "relevant": relevant, "irrelevant": tagged - relevant}

    def find_by_doi(self, doi: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM papers WHERE doi = ?", (doi,)
            ).fetchone()
            return dict(row) if row else None

    def get_all_papers(self, relevant_only: bool = True) -> list[dict]:
        with self._conn() as conn:
            if relevant_only:
                rows = conn.execute(
                    "SELECT * FROM papers WHERE is_relevant = 1 ORDER BY year DESC, citation_count DESC"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM papers ORDER BY year DESC, citation_count DESC"
                ).fetchall()
            return [dict(r) for r in rows]

    def get_papers_with_abstracts(self, relevant_only: bool = True) -> list[dict]:
        with self._conn() as conn:
            base = "SELECT * FROM papers WHERE abstract IS NOT NULL AND abstract != ''"
            if relevant_only:
                base += " AND is_relevant = 1"
            base += " ORDER BY year DESC"
            rows = conn.execute(base).fetchall()
            return [dict(r) for r in rows]

    def count(self, relevant_only: bool = False) -> int:
        with self._conn() as conn:
            if relevant_only:
                return conn.execute("SELECT COUNT(*) FROM papers WHERE is_relevant = 1").fetchone()[0]
            return conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]

    def count_by_source(self) -> dict:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT source, COUNT(*) as cnt FROM papers GROUP BY source"
            ).fetchall()
            return {r["source"]: r["cnt"] for r in rows}

    def mark_pdf_downloaded(self, paper_id: str):
        with self._conn() as conn:
            conn.execute(
                "UPDATE papers SET pdf_downloaded = 1 WHERE id = ?", (paper_id,)
            )

    def get_papers_for_download(self, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT * FROM papers
                WHERE pdf_url != '' AND pdf_downloaded = 0 AND is_relevant = 1
                ORDER BY citation_count DESC
                LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
