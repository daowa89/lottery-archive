"""
Unit tests for http_utils.py

Uses unittest.mock — no actual network requests are made.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests as req

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from http_utils import fetch_url, BROWSER_HEADERS


def _mock_response(text="data", encoding=None, apparent_encoding="utf-8"):
    resp = MagicMock()
    resp.text = text
    resp.encoding = encoding
    resp.apparent_encoding = apparent_encoding
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# fetch_url — success / retry behaviour
# ---------------------------------------------------------------------------

class TestFetchUrlRetries(unittest.TestCase):
    def test_returns_text_on_success(self):
        with patch("http_utils.requests.Session") as mock_cls:
            mock_cls.return_value.get.return_value = _mock_response(text="hello")
            self.assertEqual(fetch_url("http://example.com"), "hello")

    def test_retries_on_transient_error(self):
        with patch("http_utils.requests.Session") as mock_cls, \
             patch("http_utils.time.sleep"):
            session = mock_cls.return_value
            session.get.side_effect = [
                req.RequestException("timeout"),
                _mock_response(text="ok"),
            ]
            result = fetch_url("http://example.com", retries=2)
        self.assertEqual(result, "ok")
        self.assertEqual(session.get.call_count, 2)

    def test_raises_after_all_retries_exhausted(self):
        with patch("http_utils.requests.Session") as mock_cls, \
             patch("http_utils.time.sleep"):
            mock_cls.return_value.get.side_effect = req.RequestException("fail")
            with self.assertRaises(req.RequestException):
                fetch_url("http://example.com", retries=3)
        self.assertEqual(mock_cls.return_value.get.call_count, 3)

    def test_no_sleep_on_last_attempt(self):
        """time.sleep must not be called after the final failed attempt."""
        with patch("http_utils.requests.Session") as mock_cls, \
             patch("http_utils.time.sleep") as mock_sleep:
            mock_cls.return_value.get.side_effect = req.RequestException("fail")
            with self.assertRaises(req.RequestException):
                fetch_url("http://example.com", retries=2)
        self.assertEqual(mock_sleep.call_count, 1)  # only after attempt 1, not 2


# ---------------------------------------------------------------------------
# fetch_url — headers
# ---------------------------------------------------------------------------

class TestFetchUrlHeaders(unittest.TestCase):
    def test_headers_passed_to_session(self):
        with patch("http_utils.requests.Session") as mock_cls:
            session = mock_cls.return_value
            session.get.return_value = _mock_response()
            fetch_url("http://example.com", headers={"X-Test": "1"})
        session.headers.update.assert_called_once_with({"X-Test": "1"})

    def test_no_headers_skips_update(self):
        with patch("http_utils.requests.Session") as mock_cls:
            session = mock_cls.return_value
            session.get.return_value = _mock_response()
            fetch_url("http://example.com")
        session.headers.update.assert_not_called()


# ---------------------------------------------------------------------------
# fetch_url — encoding
# ---------------------------------------------------------------------------

class TestFetchUrlEncoding(unittest.TestCase):
    def test_encoding_auto_uses_apparent_encoding(self):
        with patch("http_utils.requests.Session") as mock_cls:
            resp = _mock_response(apparent_encoding="windows-1252")
            mock_cls.return_value.get.return_value = resp
            fetch_url("http://example.com", encoding="auto")
        self.assertEqual(resp.encoding, "windows-1252")

    def test_encoding_auto_falls_back_when_detection_fails(self):
        with patch("http_utils.requests.Session") as mock_cls:
            resp = _mock_response(apparent_encoding=None)
            mock_cls.return_value.get.return_value = resp
            fetch_url("http://example.com", encoding="auto")
        self.assertEqual(resp.encoding, "windows-1252")

    def test_explicit_encoding_is_set(self):
        with patch("http_utils.requests.Session") as mock_cls:
            resp = _mock_response()
            mock_cls.return_value.get.return_value = resp
            fetch_url("http://example.com", encoding="utf-8")
        self.assertEqual(resp.encoding, "utf-8")

    def test_no_encoding_leaves_response_unchanged(self):
        with patch("http_utils.requests.Session") as mock_cls:
            resp = _mock_response(encoding="iso-8859-1")
            mock_cls.return_value.get.return_value = resp
            fetch_url("http://example.com")
        self.assertEqual(resp.encoding, "iso-8859-1")


# ---------------------------------------------------------------------------
# BROWSER_HEADERS
# ---------------------------------------------------------------------------

class TestBrowserHeaders(unittest.TestCase):
    def test_user_agent_present(self):
        self.assertIn("User-Agent", BROWSER_HEADERS)

    def test_user_agent_is_non_empty_string(self):
        self.assertIsInstance(BROWSER_HEADERS["User-Agent"], str)
        self.assertTrue(BROWSER_HEADERS["User-Agent"])


if __name__ == "__main__":
    unittest.main()
