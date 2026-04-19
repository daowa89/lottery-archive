#!/usr/bin/env python3
"""Shared HTTP utilities for lottery fetch scripts."""

import time
import requests
from requests import HTTPError, RequestException

__all__ = ["fetch_url", "BROWSER_HEADERS", "HTTPError", "RequestException"]

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}


def fetch_url(url: str, retries: int = 3, backoff: float = 2.0) -> str:
    """Fetch a URL with retry logic and exponential backoff."""
    last_exc: Exception | None = None
    session = requests.Session()
    session.headers.update(BROWSER_HEADERS)

    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "windows-1252"
            return resp.text
        except RequestException as exc:
            last_exc = exc
            if attempt < retries:
                wait = backoff ** attempt
                print(f"  Attempt {attempt} failed ({exc}). Retrying in {wait:.0f}s...")
                time.sleep(wait)

    raise last_exc  # type: ignore[misc]
