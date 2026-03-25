"""PDF downloader with SNU proxy support."""

import logging
import time
from pathlib import Path
from urllib.parse import quote

import requests

from config import SNU_PROXY_PREFIX, PDF_DIR, RATE_LIMITS

logger = logging.getLogger(__name__)


class PDFDownloader:
    def __init__(self, use_proxy: bool = True, cookies_file: str = None):
        self.use_proxy = use_proxy
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        })

        if cookies_file:
            self._load_cookies(cookies_file)

    def _load_cookies(self, path: str):
        """Load cookies from a Netscape-format cookies file."""
        try:
            from http.cookiejar import MozillaCookieJar
            jar = MozillaCookieJar(path)
            jar.load(ignore_discard=True)
            self.session.cookies = jar
            logger.info(f"Loaded cookies from {path}")
        except Exception as e:
            logger.warning(f"Failed to load cookies: {e}")

    def _proxy_url(self, url: str) -> str:
        """Wrap URL with SNU proxy prefix."""
        if self.use_proxy and not url.startswith(SNU_PROXY_PREFIX):
            return f"{SNU_PROXY_PREFIX}{quote(url, safe='')}"
        return url

    def download(self, paper: dict, output_dir: Path = None) -> bool:
        """Download PDF for a paper. Returns True on success."""
        pdf_url = paper.get("pdf_url", "")
        if not pdf_url:
            return False

        output_dir = output_dir or PDF_DIR
        paper_id = paper["id"].replace("/", "_")
        output_path = output_dir / f"{paper_id}.pdf"

        if output_path.exists():
            logger.debug(f"Already downloaded: {paper_id}")
            return True

        # Try direct URL first (for open access)
        urls_to_try = [pdf_url]

        # If we have DOI, try Sci-Hub alternatives via proxy
        doi = paper.get("doi", "")
        if doi and self.use_proxy:
            urls_to_try.append(f"https://doi.org/{doi}")

        for url in urls_to_try:
            final_url = self._proxy_url(url) if self.use_proxy else url
            try:
                resp = self.session.get(final_url, timeout=60, stream=True)
                if resp.status_code == 200 and "pdf" in resp.headers.get("content-type", "").lower():
                    with open(output_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            f.write(chunk)
                    logger.info(f"Downloaded: {paper['title'][:60]}...")
                    return True
            except requests.RequestException as e:
                logger.debug(f"Download failed for {url}: {e}")
                continue

        return False

    def batch_download(self, papers: list[dict], limit: int = 50) -> int:
        """Download PDFs for a batch of papers. Returns count of successful downloads."""
        downloaded = 0
        for paper in papers[:limit]:
            if self.download(paper):
                downloaded += 1
            time.sleep(2)  # Be respectful
        return downloaded
