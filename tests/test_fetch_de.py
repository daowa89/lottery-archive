"""
Unit tests for fetch_lotto_de_6aus49.py

All tests are offline — no network requests are made.
"""

import contextlib
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import fetch_lotto_de_6aus49 as fetch_de
from fetch_lotto_de_6aus49 import Draw


# ---------------------------------------------------------------------------
# HTML fixtures (mimics lottozahlenonline.de structure)
# ---------------------------------------------------------------------------

def _make_row(draw_date: str, numbers: list[int], superzahl: str = "5") -> str:
    """Build one zahlensuche_rahmen div with the given data."""
    zahl_divs = "".join(
        f'<div class="zahlensuche_zahl">{n}</div>' for n in numbers
    )
    return (
        f'<div class="zahlensuche_rahmen">'
        f'<div class="zahlensuche_nr">1</div>'
        f'<time class="zahlensuche_datum" datetime="{draw_date}">'
        f'{draw_date}</time>'
        f'<div class="zahlensuche_tag">Sa</div>'
        f'{zahl_divs}'
        f'<div class="zahlensuche_zz">{superzahl}</div>'
        f'</div>'
    )


VALID_ROW_1 = _make_row("2025-01-04", [2, 6, 24, 30, 36, 45], "2")
VALID_ROW_2 = _make_row("2025-01-08", [9, 27, 28, 30, 45, 49], "6")
VALID_ROW_3 = _make_row("2025-01-11", [10, 22, 26, 27, 30, 33], "8")

PAGE_THREE_DRAWS = f"<html><body>{VALID_ROW_1}{VALID_ROW_2}{VALID_ROW_3}</body></html>"
PAGE_ONE_DRAW   = f"<html><body>{VALID_ROW_1}</body></html>"
PAGE_EMPTY      = "<html><body></body></html>"

ROW_MISSING_SZ = (
    '<div class="zahlensuche_rahmen">'
    '<time class="zahlensuche_datum" datetime="2025-02-01">2025-02-01</time>'
    '<div class="zahlensuche_zahl">1</div>'
    '<div class="zahlensuche_zahl">2</div>'
    '<div class="zahlensuche_zahl">3</div>'
    '<div class="zahlensuche_zahl">4</div>'
    '<div class="zahlensuche_zahl">5</div>'
    '<div class="zahlensuche_zahl">6</div>'
    '<div class="zahlensuche_zz"></div>'    # empty — pre-Superzahl era
    '</div>'
)

ROW_INVALID_RANGE = _make_row("2025-03-01", [0, 2, 3, 4, 5, 6], "5")   # n1=0
ROW_INVALID_SZ    = _make_row("2025-03-02", [1, 2, 3, 4, 5, 6], "10")  # sz=10
ROW_DUPLICATE_NR  = _make_row("2025-03-03", [1, 1, 3, 4, 5, 6], "5")   # dup

ROW_FIVE_NUMBERS = (
    '<div class="zahlensuche_rahmen">'
    '<time class="zahlensuche_datum" datetime="2025-04-01">2025-04-01</time>'
    '<div class="zahlensuche_zahl">1</div>'
    '<div class="zahlensuche_zahl">2</div>'
    '<div class="zahlensuche_zahl">3</div>'
    '<div class="zahlensuche_zahl">4</div>'
    '<div class="zahlensuche_zahl">5</div>'
    '<div class="zahlensuche_zz">3</div>'
    '</div>'
)


# ---------------------------------------------------------------------------
# parse_year_page
# ---------------------------------------------------------------------------

class TestParseYearPage(unittest.TestCase):
    def test_returns_three_draws(self):
        draws = fetch_de.parse_year_page(PAGE_THREE_DRAWS)
        self.assertEqual(len(draws), 3)

    def test_first_draw_date(self):
        draws = fetch_de.parse_year_page(PAGE_THREE_DRAWS)
        self.assertEqual(draws[0].date, "2025-01-04")

    def test_first_draw_numbers(self):
        draws = fetch_de.parse_year_page(PAGE_THREE_DRAWS)
        d = draws[0]
        self.assertEqual((d.n1, d.n2, d.n3, d.n4, d.n5, d.n6), (2, 6, 24, 30, 36, 45))

    def test_first_draw_superzahl(self):
        draws = fetch_de.parse_year_page(PAGE_THREE_DRAWS)
        self.assertEqual(draws[0].superzahl, 2)

    def test_empty_page_returns_empty_list(self):
        self.assertEqual(fetch_de.parse_year_page(PAGE_EMPTY), [])

    def test_single_draw_page(self):
        draws = fetch_de.parse_year_page(PAGE_ONE_DRAW)
        self.assertEqual(len(draws), 1)

    def test_empty_superzahl_stored_as_none(self):
        """Rows with no Superzahl value (pre-1992 era) are stored with superzahl=None."""
        html = f"<html><body>{ROW_MISSING_SZ}</body></html>"
        draws = fetch_de.parse_year_page(html)
        self.assertEqual(len(draws), 1)
        self.assertIsNone(draws[0].superzahl)

    def test_invalid_number_range_skipped(self):
        html = f"<html><body>{ROW_INVALID_RANGE}</body></html>"
        with contextlib.redirect_stderr(io.StringIO()):
            draws = fetch_de.parse_year_page(html)
        self.assertEqual(draws, [])

    def test_invalid_superzahl_skipped(self):
        html = f"<html><body>{ROW_INVALID_SZ}</body></html>"
        with contextlib.redirect_stderr(io.StringIO()):
            draws = fetch_de.parse_year_page(html)
        self.assertEqual(draws, [])

    def test_duplicate_numbers_skipped(self):
        html = f"<html><body>{ROW_DUPLICATE_NR}</body></html>"
        with contextlib.redirect_stderr(io.StringIO()):
            draws = fetch_de.parse_year_page(html)
        self.assertEqual(draws, [])

    def test_row_with_five_numbers_skipped(self):
        html = f"<html><body>{ROW_FIVE_NUMBERS}</body></html>"
        with contextlib.redirect_stderr(io.StringIO()):
            draws = fetch_de.parse_year_page(html)
        self.assertEqual(draws, [])

    def test_valid_rows_mixed_with_invalid_parsed_correctly(self):
        html = (
            f"<html><body>"
            f"{VALID_ROW_1}{ROW_INVALID_RANGE}{VALID_ROW_2}"
            f"</body></html>"
        )
        with contextlib.redirect_stderr(io.StringIO()):
            draws = fetch_de.parse_year_page(html)
        self.assertEqual(len(draws), 2)
        self.assertEqual(draws[0].date, "2025-01-04")
        self.assertEqual(draws[1].date, "2025-01-08")


# ---------------------------------------------------------------------------
# validate_draw
# ---------------------------------------------------------------------------

class TestValidateDraw(unittest.TestCase):
    def _make(self, numbers=(1, 2, 3, 4, 5, 6), superzahl: int | None = 5):
        return Draw("2025-01-01", *numbers, superzahl)

    def test_valid_draw_passes(self):
        valid, reason = fetch_de.validate_draw(self._make())
        self.assertTrue(valid)
        self.assertEqual(reason, "")

    def test_none_superzahl_passes(self):
        valid, _ = fetch_de.validate_draw(self._make(superzahl=None))
        self.assertTrue(valid)

    def test_boundary_numbers_pass(self):
        valid, _ = fetch_de.validate_draw(self._make(numbers=(1, 2, 3, 4, 5, 49)))
        self.assertTrue(valid)

    def test_superzahl_zero_passes(self):
        valid, _ = fetch_de.validate_draw(self._make(superzahl=0))
        self.assertTrue(valid)

    def test_superzahl_nine_passes(self):
        valid, _ = fetch_de.validate_draw(self._make(superzahl=9))
        self.assertTrue(valid)

    def test_duplicate_numbers_fail(self):
        valid, reason = fetch_de.validate_draw(self._make(numbers=(1, 1, 3, 4, 5, 6)))
        self.assertFalse(valid)
        self.assertIn("duplicate", reason)

    def test_number_zero_fails(self):
        valid, reason = fetch_de.validate_draw(self._make(numbers=(0, 2, 3, 4, 5, 6)))
        self.assertFalse(valid)
        self.assertIn("out of range", reason)

    def test_number_50_fails(self):
        valid, reason = fetch_de.validate_draw(self._make(numbers=(1, 2, 3, 4, 5, 50)))
        self.assertFalse(valid)
        self.assertIn("out of range", reason)

    def test_superzahl_minus1_fails(self):
        valid, reason = fetch_de.validate_draw(self._make(superzahl=-1))
        self.assertFalse(valid)
        self.assertIn("superzahl", reason)

    def test_superzahl_10_fails(self):
        valid, reason = fetch_de.validate_draw(self._make(superzahl=10))
        self.assertFalse(valid)
        self.assertIn("superzahl", reason)


# ---------------------------------------------------------------------------
# CSV I/O: load_existing_draws / write_draws
# ---------------------------------------------------------------------------

class TestCsvIO(unittest.TestCase):
    def _draw(self, date="2025-01-04", numbers=(2, 6, 24, 30, 36, 45), superzahl=2):
        return Draw(date, *numbers, superzahl)

    def test_load_existing_draws_missing_file_returns_empty(self):
        from pathlib import Path
        result = fetch_de.load_existing_draws(Path("/nonexistent/path.csv"))
        self.assertEqual(result, [])

    def test_load_existing_dates_missing_file_returns_empty(self):
        from pathlib import Path
        result = fetch_de.load_existing_dates(Path("/nonexistent/path.csv"))
        self.assertEqual(result, set())

    def test_write_and_reload_roundtrip(self):
        import tempfile
        draw = self._draw()
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = io.StringIO()  # use a temp file via monkeypatching RESULTS_CSV
            import pathlib
            real_path = pathlib.Path(tmp) / "results.csv"
            original = fetch_de.RESULTS_CSV
            fetch_de.RESULTS_CSV = real_path
            try:
                fetch_de.write_draws([draw])
                loaded = fetch_de.load_existing_draws(real_path)
            finally:
                fetch_de.RESULTS_CSV = original

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].date, "2025-01-04")
        self.assertEqual(loaded[0].n1, 2)
        self.assertEqual(loaded[0].superzahl, 2)

    def test_write_draws_none_superzahl_roundtrip(self):
        """Pre-1992 draws with superzahl=None survive a write/read cycle."""
        import tempfile, pathlib
        draw = self._draw(date="1970-10-10", superzahl=None)
        with tempfile.TemporaryDirectory() as tmp:
            real_path = pathlib.Path(tmp) / "results.csv"
            original = fetch_de.RESULTS_CSV
            fetch_de.RESULTS_CSV = real_path
            try:
                fetch_de.write_draws([draw])
                loaded = fetch_de.load_existing_draws(real_path)
            finally:
                fetch_de.RESULTS_CSV = original

        self.assertEqual(len(loaded), 1)
        self.assertIsNone(loaded[0].superzahl)

    def test_write_draws_merges_with_existing(self):
        """Writing new draws must not overwrite draws already in the file."""
        import tempfile, pathlib
        draw1 = self._draw(date="2025-01-04")
        draw2 = self._draw(date="2025-01-08", numbers=(9, 27, 28, 30, 45, 49), superzahl=6)
        with tempfile.TemporaryDirectory() as tmp:
            real_path = pathlib.Path(tmp) / "results.csv"
            original = fetch_de.RESULTS_CSV
            fetch_de.RESULTS_CSV = real_path
            try:
                fetch_de.write_draws([draw1])
                fetch_de.write_draws([draw2])
                loaded = fetch_de.load_existing_draws(real_path)
            finally:
                fetch_de.RESULTS_CSV = original

        self.assertEqual(len(loaded), 2)

    def test_write_draws_sorted_by_date(self):
        """Draws must be written in chronological order regardless of input order."""
        import tempfile, pathlib
        draw_late = self._draw(date="2025-01-08")
        draw_early = self._draw(date="2025-01-04", numbers=(1, 2, 3, 4, 5, 6))
        with tempfile.TemporaryDirectory() as tmp:
            real_path = pathlib.Path(tmp) / "results.csv"
            original = fetch_de.RESULTS_CSV
            fetch_de.RESULTS_CSV = real_path
            try:
                fetch_de.write_draws([draw_late, draw_early])
                loaded = fetch_de.load_existing_draws(real_path)
            finally:
                fetch_de.RESULTS_CSV = original

        self.assertEqual(loaded[0].date, "2025-01-04")
        self.assertEqual(loaded[1].date, "2025-01-08")


if __name__ == "__main__":
    unittest.main()
