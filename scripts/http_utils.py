#!/usr/bin/env python3
"""Shared HTTP utilities for lottery fetch scripts."""

import time

import requests
from requests import HTTPError, RequestException

__all__ = ["fetch_url", "BROWSER_HEADERS", "HTTPError", "RequestException"]

# Browser-like User-Agent used by scripts that scrape HTML pages.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}


def fetch_url(
    url: str,
    retries: int = 3,
    backoff: float = 2.0,
    headers: dict | None = None,
    encoding: str | None = None,
) -> str:
    """
    Download a URL and return the text content.
    Retries up to `retries` times with exponential backoff on transient errors.

    Args:
        headers:  Optional HTTP headers to include in the request.
        encoding: If set, overrides the response encoding. Pass ``"auto"`` to
                  detect encoding from the response content (falls back to
                  ``"windows-1252"`` when detection fails).
    """
    last_exc: Exception | None = None
    session = requests.Session()
    if headers:
        session.headers.update(headers)

    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            if encoding == "auto":
                resp.encoding = resp.apparent_encoding or "windows-1252"
            elif encoding:
                resp.encoding = encoding
            return resp.text
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < retries:
                wait = backoff ** attempt
                print(f"  Attempt {attempt} failed ({exc}). Retrying in {wait:.0f}s...")
                time.sleep(wait)

    raise last_exc  # type: ignore[misc]
