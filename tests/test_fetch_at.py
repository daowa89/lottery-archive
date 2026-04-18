"""
Unit tests for fetch_lotto_at_6aus45.py

All tests are offline — no network requests are made.
"""

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import fetch_lotto_at_6aus45 as fetch_at
from fetch_lotto_at_6aus45 import Draw


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

YEARLY_CSV = (
    "Datum;Reihenfolge;Zahl1;Zahl2;Zahl3;Zahl4;Zahl5;Zahl6;ZZ;Zusatzzahl;"
    "Rang_1_5;Anzahl_1_5;a_1_5;Quote_1_5\n"
    "04.01.;aufsteigend;1;4;15;16;22;38;ZZ;11;6er;1;€;1.200.000,00\n"
    "04.01.;;;;;;;;;;4er;3.027;€;62,70\n"          # prize-only row, must be skipped
    "07.01.;aufsteigend;4;5;16;21;35;45;ZZ;33;6er;JP;;690.345,70\n"
    "07.01.;;;;;;;;;;4er;2.907;€;56,50\n"
)

HISTORICAL_CSV = (
    ";;;;\n"
    "2010 Lotto - Beträge in EUR;;;;\n"
    ";;;;\n"
    " Datum;;Reihenfolge;Zahlen;;;;;\n"
    "Mi;08.9.;aufsteigend;4;30;31;32;34;38;Zz;33;6er;JP;;877.301,90\n"
    ";;gezogen;32;30;38;4;34;31;Zz;33;4er;4.161\n"  # skipped
    "So;12.9.;aufsteigend;1;9;19;34;39;43;Zz;8;6er;1;;2.205.765,30\n"
    "2011 Lotto - Beträge in EUR;;;;\n"
    "Mi;05.1.;aufsteigend;2;7;12;20;28;44;Zz;15;6er;1;;1.400.000,00\n"
)

# Format B: 1986-2010 style — weekday has trailing ".", no "aufsteigend" column
HISTORICAL_CSV_FORMAT_B = (
    ";;;;\n"
    "1986 Lotto - Beträge in ATS;;;;\n"
    ";;;;\n"
    "So.;07.09.;1;20;22;24;27;40;Zz:;12;1;à;6.542.159,00\n"
    "So.;14.09.;9;10;20;30;32;36;Zz:;25;3;à;2.290.274,00\n"
    "1987 Lotto - Beträge in ATS;;;;\n"
    "So.;04.01.;3;8;15;22;31;44;Zz:;7;1;à;5.000.000,00\n"
)


# ---------------------------------------------------------------------------
# parse_yearly_file
# ---------------------------------------------------------------------------

class TestParseYearlyFile(unittest.TestCase):
    def setUp(self):
        self.draws = fetch_at.parse_yearly_file(YEARLY_CSV, 2026)

    def test_returns_two_draws(self):
        self.assertEqual(len(self.draws), 2)

    def test_first_draw_date(self):
        self.assertEqual(self.draws[0].date, "2026-01-04")

    def test_first_draw_numbers(self):
        d = self.draws[0]
        self.assertEqual((d.n1, d.n2, d.n3, d.n4, d.n5, d.n6), (1, 4, 15, 16, 22, 38))

    def test_first_draw_zusatzzahl(self):
        self.assertEqual(self.draws[0].zusatzzahl, 11)

    def test_prize_only_rows_skipped(self):
        self.assertEqual(len(self.draws), 2)

    def test_empty_content_returns_empty_list(self):
        self.assertEqual(fetch_at.parse_yearly_file("", 2026), [])


# ---------------------------------------------------------------------------
# parse_historical_file
# ---------------------------------------------------------------------------

class TestParseHistoricalFile(unittest.TestCase):
    def setUp(self):
        self.draws = fetch_at.parse_historical_file(HISTORICAL_CSV)

    def test_returns_three_draws(self):
        self.assertEqual(len(self.draws), 3)

    def test_year_parsed_from_header_2010(self):
        self.assertEqual(self.draws[0].date, "2010-09-08")

    def test_year_parsed_from_header_2011(self):
        self.assertEqual(self.draws[2].date, "2011-01-05")

    def test_numbers_correct(self):
        d = self.draws[0]
        self.assertEqual((d.n1, d.n2, d.n3, d.n4, d.n5, d.n6), (4, 30, 31, 32, 34, 38))
        self.assertEqual(d.zusatzzahl, 33)

    def test_gezogen_rows_skipped(self):
        self.assertEqual(len(self.draws), 3)

    def test_no_year_header_returns_empty(self):
        content = "Mi;08.9.;aufsteigend;4;30;31;32;34;38;Zz;33\n"
        self.assertEqual(fetch_at.parse_historical_file(content), [])


class TestParseHistoricalFileFormatB(unittest.TestCase):
    """Tests for the 1986-2010 format (no 'aufsteigend' column, weekday with '.')."""

    def setUp(self):
        self.draws = fetch_at.parse_historical_file(HISTORICAL_CSV_FORMAT_B)

    def test_returns_three_draws(self):
        self.assertEqual(len(self.draws), 3)

    def test_first_draw_date(self):
        self.assertEqual(self.draws[0].date, "1986-09-07")

    def test_first_draw_numbers(self):
        d = self.draws[0]
        self.assertEqual((d.n1, d.n2, d.n3, d.n4, d.n5, d.n6), (1, 20, 22, 24, 27, 40))

    def test_first_draw_zusatzzahl(self):
        self.assertEqual(self.draws[0].zusatzzahl, 12)

    def test_year_boundary_parsed(self):
        self.assertEqual(self.draws[2].date, "1987-01-04")


# ---------------------------------------------------------------------------
# validate_draw
# ---------------------------------------------------------------------------

class TestValidateDraw(unittest.TestCase):
    def _make(self, numbers=(1, 2, 3, 4, 5, 6), zusatzzahl=7):
        return Draw("2025-01-01", *numbers, zusatzzahl)

    def test_valid_draw_passes(self):
        valid, reason = fetch_at.validate_draw(self._make())
        self.assertTrue(valid)
        self.assertEqual(reason, "")

    def test_boundary_numbers_pass(self):
        valid, _ = fetch_at.validate_draw(self._make(numbers=(1, 2, 3, 4, 5, 45)))
        self.assertTrue(valid)

    def test_duplicate_numbers_fail(self):
        valid, reason = fetch_at.validate_draw(self._make(numbers=(1, 1, 3, 4, 5, 6)))
        self.assertFalse(valid)
        self.assertIn("duplicate", reason)

    def test_number_zero_fails(self):
        valid, reason = fetch_at.validate_draw(self._make(numbers=(0, 2, 3, 4, 5, 6)))
        self.assertFalse(valid)
        self.assertIn("out of range", reason)

    def test_number_46_fails(self):
        valid, reason = fetch_at.validate_draw(self._make(numbers=(1, 2, 3, 4, 5, 46)))
        self.assertFalse(valid)
        self.assertIn("out of range", reason)

    def test_zusatzzahl_zero_fails(self):
        valid, reason = fetch_at.validate_draw(self._make(zusatzzahl=0))
        self.assertFalse(valid)
        self.assertIn("zusatzzahl", reason)

    def test_zusatzzahl_46_fails(self):
        valid, reason = fetch_at.validate_draw(self._make(zusatzzahl=46))
        self.assertFalse(valid)
        self.assertIn("zusatzzahl", reason)


# ---------------------------------------------------------------------------
# parse_date_str
# ---------------------------------------------------------------------------

class TestParseDateStr(unittest.TestCase):
    def test_standard_format(self):
        self.assertEqual(fetch_at.parse_date_str("04.01.", 2026), date(2026, 1, 4))

    def test_single_digit_month(self):
        self.assertEqual(fetch_at.parse_date_str("08.9.", 2010), date(2010, 9, 8))

    def test_invalid_returns_none(self):
        self.assertIsNone(fetch_at.parse_date_str("not-a-date", 2026))

    def test_empty_returns_none(self):
        self.assertIsNone(fetch_at.parse_date_str("", 2026))


# ---------------------------------------------------------------------------
# CSV I/O: load_existing_draws / write_csv
# ---------------------------------------------------------------------------

class TestCsvIO(unittest.TestCase):
    def _draw(self, date="2025-01-04", numbers=(1, 4, 15, 16, 22, 38), zusatzzahl=11):
        return Draw(date, *numbers, zusatzzahl)

    def test_load_existing_draws_missing_file_returns_empty(self):
        result = fetch_at.load_existing_draws(Path("/nonexistent/path.csv"))
        self.assertEqual(result, [])

    def test_load_existing_dates_missing_file_returns_empty(self):
        result = fetch_at.load_existing_dates(Path("/nonexistent/path.csv"))
        self.assertEqual(result, set())

    def test_write_and_reload_roundtrip(self):
        import tempfile, pathlib
        draw = self._draw()
        with tempfile.TemporaryDirectory() as tmp:
            real_path = pathlib.Path(tmp) / "results.csv"
            original = fetch_at.RESULTS_CSV
            fetch_at.RESULTS_CSV = real_path
            try:
                fetch_at.write_csv([draw])
                loaded = fetch_at.load_existing_draws(real_path)
            finally:
                fetch_at.RESULTS_CSV = original
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].date, "2025-01-04")
        self.assertEqual(loaded[0].n1, 1)
        self.assertEqual(loaded[0].zusatzzahl, 11)

    def test_write_csv_merges_with_existing(self):
        import tempfile, pathlib
        draw1 = self._draw(date="2025-01-04")
        draw2 = self._draw(date="2025-01-07", numbers=(2, 5, 10, 20, 30, 40), zusatzzahl=3)
        with tempfile.TemporaryDirectory() as tmp:
            real_path = pathlib.Path(tmp) / "results.csv"
            original = fetch_at.RESULTS_CSV
            fetch_at.RESULTS_CSV = real_path
            try:
                fetch_at.write_csv([draw1])
                fetch_at.write_csv([draw2])
                loaded = fetch_at.load_existing_draws(real_path)
            finally:
                fetch_at.RESULTS_CSV = original
        self.assertEqual(len(loaded), 2)

    def test_write_csv_sorted_by_date(self):
        import tempfile, pathlib
        draw_late = self._draw(date="2025-01-07")
        draw_early = self._draw(date="2025-01-04", numbers=(2, 5, 10, 20, 30, 40))
        with tempfile.TemporaryDirectory() as tmp:
            real_path = pathlib.Path(tmp) / "results.csv"
            original = fetch_at.RESULTS_CSV
            fetch_at.RESULTS_CSV = real_path
            try:
                fetch_at.write_csv([draw_late, draw_early])
                loaded = fetch_at.load_existing_draws(real_path)
            finally:
                fetch_at.RESULTS_CSV = original
        self.assertEqual(loaded[0].date, "2025-01-04")
        self.assertEqual(loaded[1].date, "2025-01-07")


# ---------------------------------------------------------------------------
# JSON I/O: write_json
# ---------------------------------------------------------------------------

from helpers import write_and_load_json


class TestLoadExistingDrawsJson(unittest.TestCase):
    def _draw(self, date="2025-01-04", numbers=(1, 4, 15, 16, 22, 38), zusatzzahl=11):
        return Draw(date, *numbers, zusatzzahl)

    def test_missing_file_returns_empty(self):
        result = fetch_at.load_existing_draws_json(Path("/nonexistent/results.json"))
        self.assertEqual(result, [])

    def test_roundtrip(self):
        import tempfile, pathlib
        draw = self._draw()
        with tempfile.TemporaryDirectory() as tmp:
            json_path = pathlib.Path(tmp) / "results.json"
            original = fetch_at.RESULTS_JSON
            fetch_at.RESULTS_JSON = json_path
            try:
                fetch_at.write_json([draw])
            finally:
                fetch_at.RESULTS_JSON = original
            loaded = fetch_at.load_existing_draws_json(json_path)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].date, "2025-01-04")
        self.assertEqual(loaded[0].n1, 1)
        self.assertEqual(loaded[0].zusatzzahl, 11)

    def test_malformed_entry_skipped(self):
        import tempfile, pathlib, json
        with tempfile.TemporaryDirectory() as tmp:
            json_path = pathlib.Path(tmp) / "results.json"
            data = [
                {"date": "2025-01-04", "numbers": [1, 4, 15, 16, 22, 38], "zusatzzahl": 11},
                {"date": "bad-entry"},
                {"date": "2025-01-07", "numbers": [2, 5, 10, 20, 30, 40], "zusatzzahl": 3},
            ]
            json_path.write_text(json.dumps(data), encoding="utf-8")
            loaded = fetch_at.load_existing_draws_json(json_path)
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].date, "2025-01-04")
        self.assertEqual(loaded[1].date, "2025-01-07")


class TestJsonIO(unittest.TestCase):
    def _draw(self, date="2025-01-04", numbers=(1, 4, 15, 16, 22, 38), zusatzzahl=11):
        return Draw(date, *numbers, zusatzzahl)

    def test_write_json_structure(self):
        data = write_and_load_json(fetch_at, [self._draw()])
        self.assertEqual(len(data), 1)
        entry = data[0]
        self.assertEqual(entry["date"], "2025-01-04")
        self.assertEqual(entry["numbers"], [1, 4, 15, 16, 22, 38])
        self.assertEqual(entry["zusatzzahl"], 11)

    def test_write_json_entry_count_matches_draws(self):
        draws = [
            self._draw("2025-01-04"),
            self._draw("2025-01-07", numbers=(2, 5, 10, 20, 30, 40), zusatzzahl=3),
        ]
        data = write_and_load_json(fetch_at, draws)
        self.assertEqual(len(data), 2)

    def test_write_json_merges_with_existing(self):
        """Second call must merge with, not overwrite, the existing JSON."""
        import tempfile, pathlib, json
        draw1 = self._draw("2025-01-04")
        draw2 = self._draw("2025-01-07", numbers=(2, 5, 10, 20, 30, 40), zusatzzahl=3)
        with tempfile.TemporaryDirectory() as tmp:
            json_path = pathlib.Path(tmp) / "results.json"
            original = fetch_at.RESULTS_JSON
            fetch_at.RESULTS_JSON = json_path
            try:
                fetch_at.write_json([draw1])
                fetch_at.write_json([draw2])
                with open(json_path, encoding="utf-8") as f:
                    data = json.load(f)
            finally:
                fetch_at.RESULTS_JSON = original
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["date"], "2025-01-04")
        self.assertEqual(data[1]["date"], "2025-01-07")


if __name__ == "__main__":
    unittest.main()
