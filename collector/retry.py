"""Shared retry logic with exponential backoff for API calls."""

import time
import logging

import requests

logger = logging.getLogger(__name__)


def request_with_retry(
    method: str,
    url: str,
    max_retries: int = 6,
    base_delay: float = 10.0,
    max_delay: float = 300.0,
    **kwargs,
) -> requests.Response | None:
    """Make an HTTP request with exponential backoff on rate limits and errors.

    Returns Response on success, None if all retries exhausted.
    """
    kwargs.setdefault("timeout", 30)

    for attempt in range(max_retries):
        try:
            resp = requests.request(method, url, **kwargs)

            if resp.status_code == 429:
                # Check Retry-After header
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    delay = min(float(retry_after) + 1, max_delay)
                else:
                    delay = min(base_delay * (2 ** attempt), max_delay)

                logger.warning(
                    f"Rate limited (429). Attempt {attempt + 1}/{max_retries}. "
                    f"Waiting {delay:.0f}s..."
                )
                time.sleep(delay)
                continue

            if resp.status_code >= 500:
                delay = min(base_delay * (2 ** attempt), max_delay)
                logger.warning(
                    f"Server error ({resp.status_code}). Attempt {attempt + 1}/{max_retries}. "
                    f"Waiting {delay:.0f}s..."
                )
                time.sleep(delay)
                continue

            return resp

        except requests.exceptions.Timeout:
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(f"Timeout. Attempt {attempt + 1}/{max_retries}. Waiting {delay:.0f}s...")
            time.sleep(delay)

        except requests.exceptions.ConnectionError:
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(f"Connection error. Attempt {attempt + 1}/{max_retries}. Waiting {delay:.0f}s...")
            time.sleep(delay)

        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
            return None

    logger.error(f"All {max_retries} retries exhausted for {url}")
    return None
