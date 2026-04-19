"""
Unit tests for fetch_euromillions.py

All tests are offline — no network requests are made.
"""

import contextlib
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import fetch_euromillions as fetch_eu
from fetch_euromillions import Draw


# ---------------------------------------------------------------------------
# CSV fixtures — yearly format (2017–present, semicolon-delimited)
# ---------------------------------------------------------------------------

# Header + two draw rows + one prize-detail row (empty col[0])
YEARLY_VALID = (
    "Ziehungstag;Zahl1;Zahl2;Zahl3;Zahl4;Zahl5;Stern1;Stern2;Rang;Zahlen;Sterne;Europa;Österreich;Quoten;\n"
    "Fr. 03.01.2025;3;19;29;35;37;1;9;1;5;2;JP;JP;29139978,90;\n"
    ";;;;;;;;;2;5;2;100000,00;60000,00;\n"   # prize row — no date
    "Di. 07.01.2025;12;17;27;44;50;4;11;1;5;2;JP;JP;31000000,00;\n"
)

YEARLY_EMPTY = (
    "Ziehungstag;Zahl1;Zahl2;Zahl3;Zahl4;Zahl5;Stern1;Stern2;\n"
)

YEARLY_INVALID_RANGE = (
    "Ziehungstag;Zahl1;Zahl2;Zahl3;Zahl4;Zahl5;Stern1;Stern2;\n"
    "Fr. 10.01.2025;0;2;3;4;5;1;2;\n"   # n1=0 — out of range
)

YEARLY_INVALID_STAR = (
    "Ziehungstag;Zahl1;Zahl2;Zahl3;Zahl4;Zahl5;Stern1;Stern2;\n"
    "Fr. 10.01.2025;1;2;3;4;5;1;13;\n"  # s2=13 — out of range
)

YEARLY_DUPLICATE_MAIN = (
    "Ziehungstag;Zahl1;Zahl2;Zahl3;Zahl4;Zahl5;Stern1;Stern2;\n"
    "Fr. 10.01.2025;1;1;3;4;5;1;2;\n"   # n1=n2=1
)

YEARLY_DUPLICATE_STAR = (
    "Ziehungstag;Zahl1;Zahl2;Zahl3;Zahl4;Zahl5;Stern1;Stern2;\n"
    "Fr. 10.01.2025;1;2;3;4;5;3;3;\n"   # s1=s2=3
)


# ---------------------------------------------------------------------------
# CSV fixtures — historical format (2004–2016, sideways, semicolon-delimited)
# ---------------------------------------------------------------------------

# Two draws per block: date in Runde row, numbers in the next row
HIST_TWO_DRAWS = (
    ";Ergebnisse:;;;;;;;;Runde;1;13.02.2004;;Ergebnisse:;;;;;;;;Runde;2;20.02.2004;;;\n"
    ";aufsteigende Reihenfolge:;;;;;Sterne;;;;;;;aufsteigende Reihenfolge:;;;;;Sterne;;;;;\n"
    ";16;29;32;36;41;7;9;;;;;;7;13;39;47;50;2;5;;;\n"
)

# Only one draw in block (second Runde absent)
HIST_ONE_DRAW = (
    ";Ergebnisse:;;;;;;;;Runde;1;27.02.2004;;;;;;;;;;;;;;\n"
    ";aufsteigende Reihenfolge:;;;;;Sterne;;;;;;;;;;;;;;\n"
    ";8;11;23;34;48;3;6;;;;;;;;;;;;;;;\n"
)

# Block with invalid number (n1=0 in first draw)
HIST_INVALID = (
    ";Ergebnisse:;;;;;;;;Runde;1;06.03.2004;;Ergebnisse:;;;;;;;;Runde;2;13.03.2004;;;\n"
    ";aufsteigende Reihenfolge:;;;;;Sterne;;;;;;;aufsteigende Reihenfolge:;;;;;Sterne;;;;;\n"
    ";0;2;3;4;5;1;2;;;;;;7;13;39;47;50;2;5;;;\n"  # first draw has n1=0
)


# ---------------------------------------------------------------------------
# parse_yearly_file
# ---------------------------------------------------------------------------

class TestParseYearlyFile(unittest.TestCase):
    def test_returns_two_draws(self):
        draws = fetch_eu.parse_yearly_file(YEARLY_VALID)
        self.assertEqual(len(draws), 2)

    def test_prize_row_skipped(self):
        # YEARLY_VALID has one prize row; only 2 draw rows must survive
        draws = fetch_eu.parse_yearly_file(YEARLY_VALID)
        self.assertEqual(len(draws), 2)

    def test_first_draw_date(self):
        draws = fetch_eu.parse_yearly_file(YEARLY_VALID)
        self.assertEqual(draws[0].date, "2025-01-03")

    def test_first_draw_numbers(self):
        draws = fetch_eu.parse_yearly_file(YEARLY_VALID)
        d = draws[0]
        self.assertEqual((d.n1, d.n2, d.n3, d.n4, d.n5), (3, 19, 29, 35, 37))

    def test_first_draw_stars(self):
        draws = fetch_eu.parse_yearly_file(YEARLY_VALID)
        d = draws[0]
        self.assertEqual((d.s1, d.s2), (1, 9))

    def test_second_draw_date(self):
        draws = fetch_eu.parse_yearly_file(YEARLY_VALID)
        self.assertEqual(draws[1].date, "2025-01-07")

    def test_empty_file_returns_empty_list(self):
        draws = fetch_eu.parse_yearly_file(YEARLY_EMPTY)
        self.assertEqual(draws, [])

    def test_out_of_range_main_number_skipped(self):
        with contextlib.redirect_stderr(io.StringIO()):
            draws = fetch_eu.parse_yearly_file(YEARLY_INVALID_RANGE)
        self.assertEqual(draws, [])

    def test_out_of_range_star_skipped(self):
        with contextlib.redirect_stderr(io.StringIO()):
            draws = fetch_eu.parse_yearly_file(YEARLY_INVALID_STAR)
        self.assertEqual(draws, [])

    def test_duplicate_main_numbers_skipped(self):
        with contextlib.redirect_stderr(io.StringIO()):
            draws = fetch_eu.parse_yearly_file(YEARLY_DUPLICATE_MAIN)
        self.assertEqual(draws, [])

    def test_duplicate_star_numbers_skipped(self):
        with contextlib.redirect_stderr(io.StringIO()):
            draws = fetch_eu.parse_yearly_file(YEARLY_DUPLICATE_STAR)
        self.assertEqual(draws, [])


# ---------------------------------------------------------------------------
# parse_historical_file
# ---------------------------------------------------------------------------

class TestParseHistoricalFile(unittest.TestCase):
    def test_two_draws_parsed(self):
        draws = fetch_eu.parse_historical_file(HIST_TWO_DRAWS)
        self.assertEqual(len(draws), 2)

    def test_first_draw_date(self):
        draws = fetch_eu.parse_historical_file(HIST_TWO_DRAWS)
        self.assertEqual(draws[0].date, "2004-02-13")

    def test_first_draw_numbers(self):
        draws = fetch_eu.parse_historical_file(HIST_TWO_DRAWS)
        d = draws[0]
        self.assertEqual((d.n1, d.n2, d.n3, d.n4, d.n5), (16, 29, 32, 36, 41))

    def test_first_draw_stars(self):
        draws = fetch_eu.parse_historical_file(HIST_TWO_DRAWS)
        d = draws[0]
        self.assertEqual((d.s1, d.s2), (7, 9))

    def test_second_draw_date(self):
        draws = fetch_eu.parse_historical_file(HIST_TWO_DRAWS)
        self.assertEqual(draws[1].date, "2004-02-20")

    def test_second_draw_numbers(self):
        draws = fetch_eu.parse_historical_file(HIST_TWO_DRAWS)
        d = draws[1]
        self.assertEqual((d.n1, d.n2, d.n3, d.n4, d.n5), (7, 13, 39, 47, 50))

    def test_one_draw_block(self):
        draws = fetch_eu.parse_historical_file(HIST_ONE_DRAW)
        self.assertEqual(len(draws), 1)
        self.assertEqual(draws[0].date, "2004-02-27")

    def test_invalid_draw_in_block_skipped(self):
        """First draw is invalid (n1=0), second draw is valid — only second survives."""
        with contextlib.redirect_stderr(io.StringIO()):
            draws = fetch_eu.parse_historical_file(HIST_INVALID)
        self.assertEqual(len(draws), 1)
        self.assertEqual(draws[0].date, "2004-03-13")

    def test_empty_content_returns_empty_list(self):
        draws = fetch_eu.parse_historical_file("")
        self.assertEqual(draws, [])


# ---------------------------------------------------------------------------
# validate_draw
# ---------------------------------------------------------------------------

class TestValidateDraw(unittest.TestCase):
    def _make(self, numbers=(1, 2, 3, 4, 5), stars=(1, 2)):
        return Draw("2025-01-01", *numbers, *stars)

    def test_valid_draw_passes(self):
        valid, reason = fetch_eu.validate_draw(self._make())
        self.assertTrue(valid)
        self.assertEqual(reason, "")

    def test_boundary_numbers_pass(self):
        valid, _ = fetch_eu.validate_draw(self._make(numbers=(1, 2, 3, 4, 50)))
        self.assertTrue(valid)

    def test_boundary_stars_pass(self):
        valid, _ = fetch_eu.validate_draw(self._make(stars=(1, 12)))
        self.assertTrue(valid)

    def test_duplicate_main_numbers_fail(self):
        valid, reason = fetch_eu.validate_draw(self._make(numbers=(1, 1, 3, 4, 5)))
        self.assertFalse(valid)
        self.assertIn("duplicate", reason)

    def test_main_number_zero_fails(self):
        valid, reason = fetch_eu.validate_draw(self._make(numbers=(0, 2, 3, 4, 5)))
        self.assertFalse(valid)
        self.assertIn("out of range", reason)

    def test_main_number_51_fails(self):
        valid, reason = fetch_eu.validate_draw(self._make(numbers=(1, 2, 3, 4, 51)))
        self.assertFalse(valid)
        self.assertIn("out of range", reason)

    def test_duplicate_stars_fail(self):
        valid, reason = fetch_eu.validate_draw(self._make(stars=(5, 5)))
        self.assertFalse(valid)
        self.assertIn("duplicate", reason)

    def test_star_zero_fails(self):
        valid, reason = fetch_eu.validate_draw(self._make(stars=(0, 2)))
        self.assertFalse(valid)
        self.assertIn("out of range", reason)

    def test_star_13_fails(self):
        valid, reason = fetch_eu.validate_draw(self._make(stars=(1, 13)))
        self.assertFalse(valid)
        self.assertIn("out of range", reason)


# ---------------------------------------------------------------------------
# CSV I/O
# ---------------------------------------------------------------------------

class TestCsvIO(unittest.TestCase):
    def _draw(self, date="2025-01-03", numbers=(3, 19, 29, 35, 37), stars=(1, 9)):
        return Draw(date, *numbers, *stars)

    def test_load_existing_draws_missing_file_returns_empty(self):
        result = fetch_eu.load_existing_draws(Path("/nonexistent/path.csv"))
        self.assertEqual(result, [])

    def test_load_existing_dates_missing_file_returns_empty(self):
        result = fetch_eu.load_existing_dates(Path("/nonexistent/path.csv"))
        self.assertEqual(result, set())

    def test_write_and_reload_roundtrip(self):
        import tempfile, pathlib
        draw = self._draw()
        with tempfile.TemporaryDirectory() as tmp:
            real_path = pathlib.Path(tmp) / "results.csv"
            original = fetch_eu.RESULTS_CSV
            fetch_eu.RESULTS_CSV = real_path
            try:
                fetch_eu.write_draws([draw])
                loaded = fetch_eu.load_existing_draws(real_path)
            finally:
                fetch_eu.RESULTS_CSV = original

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].date, "2025-01-03")
        self.assertEqual(loaded[0].n1, 3)
        self.assertEqual(loaded[0].s1, 1)
        self.assertEqual(loaded[0].s2, 9)

    def test_write_draws_merges_with_existing(self):
        import tempfile, pathlib
        draw1 = self._draw(date="2025-01-03")
        draw2 = self._draw(date="2025-01-07", numbers=(12, 17, 27, 44, 50), stars=(4, 11))
        with tempfile.TemporaryDirectory() as tmp:
            real_path = pathlib.Path(tmp) / "results.csv"
            original = fetch_eu.RESULTS_CSV
            fetch_eu.RESULTS_CSV = real_path
            try:
                fetch_eu.write_draws([draw1])
                fetch_eu.write_draws([draw2])
                loaded = fetch_eu.load_existing_draws(real_path)
            finally:
                fetch_eu.RESULTS_CSV = original

        self.assertEqual(len(loaded), 2)

    def test_write_draws_sorted_by_date(self):
        import tempfile, pathlib
        draw_late = self._draw(date="2025-01-07")
        draw_early = self._draw(date="2025-01-03", numbers=(1, 2, 3, 4, 5))
        with tempfile.TemporaryDirectory() as tmp:
            real_path = pathlib.Path(tmp) / "results.csv"
            original = fetch_eu.RESULTS_CSV
            fetch_eu.RESULTS_CSV = real_path
            try:
                fetch_eu.write_draws([draw_late, draw_early])
                loaded = fetch_eu.load_existing_draws(real_path)
            finally:
                fetch_eu.RESULTS_CSV = original

        self.assertEqual(loaded[0].date, "2025-01-03")
        self.assertEqual(loaded[1].date, "2025-01-07")

    def test_write_draws_overwrites_on_date_collision(self):
        """Writing a draw for an existing date replaces the old draw."""
        import tempfile, pathlib
        original_draw = self._draw(date="2025-01-03", numbers=(1, 2, 3, 4, 5))
        updated_draw = self._draw(date="2025-01-03", numbers=(3, 19, 29, 35, 37))
        with tempfile.TemporaryDirectory() as tmp:
            real_path = pathlib.Path(tmp) / "results.csv"
            original = fetch_eu.RESULTS_CSV
            fetch_eu.RESULTS_CSV = real_path
            try:
                fetch_eu.write_draws([original_draw])
                fetch_eu.write_draws([updated_draw])
                loaded = fetch_eu.load_existing_draws(real_path)
            finally:
                fetch_eu.RESULTS_CSV = original

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].n1, 3)
        self.assertEqual(loaded[0].n2, 19)


# ---------------------------------------------------------------------------
# fetch_new_draws deduplication
# ---------------------------------------------------------------------------

class TestFetchNewDraws(unittest.TestCase):
    def test_existing_dates_are_excluded(self):
        """Draws whose date is already in results.csv must not be returned."""
        from unittest.mock import patch

        # YEARLY_VALID has draws for 2025-01-03 and 2025-01-07.
        # fetch_new_draws (init=False) fetches current and previous year.
        pre_existing = {"2025-01-03"}

        with patch("fetch_euromillions.load_existing_dates",
                   return_value=set(pre_existing)), \
             patch("fetch_euromillions.fetch_url", return_value=YEARLY_VALID):
            draws = fetch_eu.fetch_new_draws(init=False)

        self.assertFalse(any(d.date in pre_existing for d in draws))


if __name__ == "__main__":
    unittest.main()
