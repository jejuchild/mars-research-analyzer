"""SQLite database manager for paper storage."""

import json
import sqlite3
from contextlib import contextmanager
from typing import Optional

from config import DB_PATH


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
        # Check DOI duplicate first
        if paper.get("doi"):
            existing = self.find_by_doi(paper["doi"])
            if existing:
                return False

        with self._conn() as conn:
            try:
                cursor = conn.execute(
                    """INSERT OR IGNORE INTO papers
                    (id, title, abstract, authors, year, venue, doi, source, fields, citation_count, pdf_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                    ),
                )
                return cursor.rowcount > 0
            except sqlite3.IntegrityError:
                return False

    def find_by_doi(self, doi: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM papers WHERE doi = ?", (doi,)
            ).fetchone()
            return dict(row) if row else None

    def get_all_papers(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM papers ORDER BY year DESC, citation_count DESC").fetchall()
            return [dict(r) for r in rows]

    def get_papers_with_abstracts(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM papers WHERE abstract IS NOT NULL AND abstract != '' ORDER BY year DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def count(self) -> int:
        with self._conn() as conn:
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
                WHERE pdf_url != '' AND pdf_downloaded = 0
                ORDER BY citation_count DESC
                LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
