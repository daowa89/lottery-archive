"""
Unit tests for update_all.py

Uses unittest.mock — no network requests or git commands are executed.
"""

import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from update_all import update_country, main


# ---------------------------------------------------------------------------
# update_country
# ---------------------------------------------------------------------------

def _make_draw(date: str):
    """Return a minimal mock draw with a .date attribute."""
    d = MagicMock()
    d.date = date
    return d


class TestUpdateCountry(unittest.TestCase):
    def test_returns_zero_when_no_draws(self):
        with contextlib.redirect_stdout(io.StringIO()):
            result = update_country("AT", "Lotto 6 aus 45", "/f.csv", "/f.json", [])
        self.assertEqual(result, 0)

    def test_returns_draw_count_when_committed(self):
        draws = [_make_draw("2025-01-04"), _make_draw("2025-01-08")]
        with patch("update_all.git_commit", return_value=True), \
             contextlib.redirect_stdout(io.StringIO()):
            result = update_country("AT", "Lotto 6 aus 45", "/f.csv", "/f.json", draws)
        self.assertEqual(result, 2)

    def test_returns_draw_count_even_when_file_unchanged(self):
        """Even if git_commit returns False (file unchanged), the count is returned."""
        draws = [_make_draw("2025-01-04")]
        with patch("update_all.git_commit", return_value=False), \
             contextlib.redirect_stdout(io.StringIO()):
            result = update_country("AT", "Lotto 6 aus 45", "/f.csv", "/f.json", draws)
        self.assertEqual(result, 1)

    def test_commit_message_contains_dates(self):
        draws = [_make_draw("2025-01-04"), _make_draw("2025-01-08")]
        with patch("update_all.git_commit") as mock_commit, \
             contextlib.redirect_stdout(io.StringIO()):
            mock_commit.return_value = True
            update_country("AT", "Lotto 6 aus 45", "/f.csv", "/f.json", draws)
        msg = mock_commit.call_args[0][1]
        self.assertIn("2025-01-04", msg)
        self.assertIn("2025-01-08", msg)

    def test_commit_message_contains_label_and_game(self):
        draws = [_make_draw("2025-01-04")]
        with patch("update_all.git_commit") as mock_commit, \
             contextlib.redirect_stdout(io.StringIO()):
            mock_commit.return_value = True
            update_country("AT", "Lotto 6 aus 45", "/f.csv", "/f.json", draws)
        msg = mock_commit.call_args[0][1]
        self.assertIn("AT", msg)
        self.assertIn("Lotto 6 aus 45", msg)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

class TestMain(unittest.TestCase):
    def _patch_fetchers(self, at_draws=None, de_draws=None, eu_draws=None,
                        at_exc=None, de_exc=None, eu_exc=None):
        """Return mock objects for all three fetch modules."""
        at_draws = at_draws or []
        de_draws = de_draws or []
        eu_draws = eu_draws or []

        at_mock = MagicMock()
        de_mock = MagicMock()
        eu_mock = MagicMock()

        if at_exc:
            at_mock.fetch_new_draws.side_effect = at_exc
        else:
            at_mock.fetch_new_draws.return_value = at_draws
        at_mock.RESULTS_CSV = Path("/tmp/at.csv")
        at_mock.RESULTS_JSON = Path("/tmp/at.json")
        at_mock.write_csv = MagicMock()
        at_mock.write_json = MagicMock()

        if de_exc:
            de_mock.fetch_new_draws.side_effect = de_exc
        else:
            de_mock.fetch_new_draws.return_value = de_draws
        de_mock.RESULTS_CSV = Path("/tmp/de.csv")
        de_mock.RESULTS_JSON = Path("/tmp/de.json")
        de_mock.write_csv = MagicMock()
        de_mock.write_json = MagicMock()

        if eu_exc:
            eu_mock.fetch_new_draws.side_effect = eu_exc
        else:
            eu_mock.fetch_new_draws.return_value = eu_draws
        eu_mock.RESULTS_CSV = Path("/tmp/eu.csv")
        eu_mock.RESULTS_JSON = Path("/tmp/eu.json")
        eu_mock.write_csv = MagicMock()
        eu_mock.write_json = MagicMock()

        return at_mock, de_mock, eu_mock

    def test_returns_total_draw_count(self):
        at_mock, de_mock, eu_mock = self._patch_fetchers(
            at_draws=[_make_draw("2025-01-04")],
            de_draws=[_make_draw("2025-01-08"), _make_draw("2025-01-11")],
            eu_draws=[_make_draw("2025-01-07")],
        )
        with patch("update_all.fetch_at", at_mock), \
             patch("update_all.fetch_de", de_mock), \
             patch("update_all.fetch_eu", eu_mock), \
             patch("update_all.git_commit", return_value=True), \
             contextlib.redirect_stdout(io.StringIO()):
            result = main()
        self.assertEqual(result, 4)

    def test_returns_zero_when_no_new_draws(self):
        at_mock, de_mock, eu_mock = self._patch_fetchers()
        with patch("update_all.fetch_at", at_mock), \
             patch("update_all.fetch_de", de_mock), \
             patch("update_all.fetch_eu", eu_mock), \
             patch("update_all.git_commit", return_value=False), \
             contextlib.redirect_stdout(io.StringIO()):
            result = main()
        self.assertEqual(result, 0)

    def test_at_failure_does_not_abort_de(self):
        """An exception in the AT fetch must not prevent the DE fetch."""
        at_mock, de_mock, eu_mock = self._patch_fetchers(
            at_exc=RuntimeError("AT network error"),
            de_draws=[_make_draw("2025-01-08")],
        )
        with patch("update_all.fetch_at", at_mock), \
             patch("update_all.fetch_de", de_mock), \
             patch("update_all.fetch_eu", eu_mock), \
             patch("update_all.git_commit", return_value=True), \
             contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            result = main()
        self.assertEqual(result, 1)
        de_mock.fetch_new_draws.assert_called_once()

    def test_de_failure_does_not_affect_at_count(self):
        """An exception in the DE fetch must not reduce the AT count."""
        at_mock, de_mock, eu_mock = self._patch_fetchers(
            at_draws=[_make_draw("2025-01-04")],
            de_exc=RuntimeError("DE network error"),
        )
        with patch("update_all.fetch_at", at_mock), \
             patch("update_all.fetch_de", de_mock), \
             patch("update_all.fetch_eu", eu_mock), \
             patch("update_all.git_commit", return_value=True), \
             contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            result = main()
        self.assertEqual(result, 1)

    def test_eu_failure_does_not_affect_at_de_count(self):
        """An exception in the EU fetch must not reduce the AT+DE count."""
        at_mock, de_mock, eu_mock = self._patch_fetchers(
            at_draws=[_make_draw("2025-01-04")],
            de_draws=[_make_draw("2025-01-08")],
            eu_exc=RuntimeError("EU network error"),
        )
        with patch("update_all.fetch_at", at_mock), \
             patch("update_all.fetch_de", de_mock), \
             patch("update_all.fetch_eu", eu_mock), \
             patch("update_all.git_commit", return_value=True), \
             contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            result = main()
        self.assertEqual(result, 2)

    def test_write_draws_called_only_when_new_draws(self):
        at_mock, de_mock, eu_mock = self._patch_fetchers(
            at_draws=[_make_draw("2025-01-04")],
            de_draws=[],
            eu_draws=[],
        )
        with patch("update_all.fetch_at", at_mock), \
             patch("update_all.fetch_de", de_mock), \
             patch("update_all.fetch_eu", eu_mock), \
             patch("update_all.git_commit", return_value=True), \
             contextlib.redirect_stdout(io.StringIO()):
            main()
        at_mock.write_csv.assert_called_once()
        at_mock.write_json.assert_called_once()
        de_mock.write_csv.assert_not_called()
        de_mock.write_json.assert_not_called()
        eu_mock.write_csv.assert_not_called()
        eu_mock.write_json.assert_not_called()


if __name__ == "__main__":
    unittest.main()
