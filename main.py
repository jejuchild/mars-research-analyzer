"""Mars Research Analyzer — main pipeline entry point.

Usage:
    python main.py                  # Run full pipeline
    python main.py --collect-only   # Only collect papers
    python main.py --analyze-only   # Only analyze (skip collection)
    python main.py --download-pdfs  # Download PDFs for top papers
"""

import argparse
import json
import logging
import os
import sys

# Ensure project root is in path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import REPORT_DIR
from storage.database import PaperDB
from collector import semantic_scholar, openalex, nasa_ads
from analyzer.keywords import analyze_keywords, analyze_field_keywords
from analyzer.topics import analyze_topics
from analyzer.network import analyze_authors, analyze_venues
from analyzer.trends import analyze_trends, find_emerging_topics
from analyzer.crossfield import analyze_crossfield
from analyzer.gaps import detect_gaps
from report.generator import generate_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("mars_analyzer.log"),
    ],
)
logger = logging.getLogger(__name__)


def collect_papers(db: PaperDB):
    """Collect papers from all sources."""
    total_new = 0
    total_skipped = 0

    collectors = [
        ("OpenAlex", openalex.collect),           # most generous rate limits
        ("NASA ADS", nasa_ads.collect),            # needs API key
        ("Semantic Scholar", semantic_scholar.collect),  # strictest rate limits, last
    ]

    for name, collect_fn in collectors:
        logger.info(f"=== Collecting from {name} ===")
        new = 0
        skipped = 0
        try:
            for paper in collect_fn():
                if db.insert_paper(paper):
                    new += 1
                else:
                    skipped += 1

                if (new + skipped) % 100 == 0:
                    logger.info(f"  [{name}] Progress: {new} new, {skipped} duplicates")
        except Exception as e:
            logger.error(f"Error collecting from {name}: {e}")

        logger.info(f"  [{name}] Done: {new} new papers, {skipped} duplicates")
        total_new += new
        total_skipped += skipped

    logger.info(f"=== Collection complete: {total_new} new, {total_skipped} duplicates ===")
    logger.info(f"Total papers in DB: {db.count()}")
    logger.info(f"By source: {db.count_by_source()}")


def analyze_papers(db: PaperDB) -> dict:
    """Run all analyses and return results."""
    all_papers = db.get_all_papers()
    papers_with_abs = db.get_papers_with_abstracts()

    logger.info(f"Analyzing {len(all_papers)} papers ({len(papers_with_abs)} with abstracts)")

    if not all_papers:
        logger.error("No papers in database. Run collection first.")
        return {}

    logger.info("Running keyword analysis...")
    keywords = analyze_keywords(papers_with_abs)
    field_keywords = analyze_field_keywords(papers_with_abs)

    logger.info("Running topic modeling...")
    topics = analyze_topics(papers_with_abs)

    logger.info("Running author/venue analysis...")
    authors = analyze_authors(all_papers)
    venues = analyze_venues(all_papers)

    logger.info("Running trend analysis...")
    trends = analyze_trends(all_papers)
    emerging = find_emerging_topics(papers_with_abs)

    logger.info("Running cross-field analysis...")
    crossfield = analyze_crossfield(papers_with_abs)

    logger.info("Detecting research gaps...")
    gaps = detect_gaps(papers_with_abs)

    # Summary
    summary = {
        "total_papers": len(all_papers),
        "papers_with_abstracts": len(papers_with_abs),
        "total_authors": authors["total_unique_authors"],
        "total_venues": venues["total_venues"],
        "crossfield_papers": crossfield["multi_field_papers_count"],
        "triple_intersection": crossfield["triple_intersection_count"],
        "source_counts": db.count_by_source(),
    }

    return {
        "summary": summary,
        "keywords": keywords,
        "field_keywords": field_keywords,
        "topics": topics,
        "authors": authors,
        "venues": venues,
        "trends": trends,
        "emerging_topics": emerging,
        "crossfield": crossfield,
        "gaps": gaps,
    }


def download_pdfs(db: PaperDB, limit: int = 50):
    """Download PDFs for top papers."""
    from storage.downloader import PDFDownloader

    papers = db.get_papers_for_download(limit=limit)
    logger.info(f"Downloading PDFs for {len(papers)} papers...")

    downloader = PDFDownloader(use_proxy=True)
    downloaded = downloader.batch_download(papers)

    for paper in papers:
        from config import PDF_DIR
        pdf_path = PDF_DIR / f"{paper['id'].replace('/', '_')}.pdf"
        if pdf_path.exists():
            db.mark_pdf_downloaded(paper["id"])

    logger.info(f"Downloaded {downloaded} PDFs")


def main():
    parser = argparse.ArgumentParser(description="Mars Research Analyzer")
    parser.add_argument("--collect-only", action="store_true", help="Only collect papers")
    parser.add_argument("--analyze-only", action="store_true", help="Only run analysis")
    parser.add_argument("--download-pdfs", action="store_true", help="Download PDFs")
    parser.add_argument("--pdf-limit", type=int, default=50, help="Max PDFs to download")
    args = parser.parse_args()

    db = PaperDB()

    if args.download_pdfs:
        download_pdfs(db, limit=args.pdf_limit)
        return

    if not args.analyze_only:
        collect_papers(db)

    if not args.collect_only:
        results = analyze_papers(db)
        if results:
            report_path = generate_report(results)
            logger.info(f"\n{'='*60}")
            logger.info(f"Report generated: {report_path}")
            logger.info(f"{'='*60}")

            # Also save raw results as JSON
            json_path = REPORT_DIR / "analysis_results.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"Raw results saved: {json_path}")


if __name__ == "__main__":
    main()
