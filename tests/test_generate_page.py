"""
Unit tests for generate_page.py

All tests are offline — no network requests, no filesystem side-effects
except where a temporary directory is explicitly used.
"""

import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import generate_page as gp


# ---------------------------------------------------------------------------
# read_last_row
# ---------------------------------------------------------------------------

class TestReadLastRow(unittest.TestCase):

    def _csv(self, rows):
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        )
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(tmp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        tmp.flush()
        return Path(tmp.name)

    def test_returns_last_row(self):
        path = self._csv([
            {"date": "2024-01-01", "n1": "1"},
            {"date": "2024-06-15", "n1": "7"},
            {"date": "2025-03-22", "n1": "42"},
        ])
        row = gp.read_last_row(path)
        self.assertEqual(row["date"], "2025-03-22")
        self.assertEqual(row["n1"], "42")

    def test_single_data_row(self):
        path = self._csv([{"date": "2020-05-10", "n1": "3"}])
        row = gp.read_last_row(path)
        self.assertEqual(row["date"], "2020-05-10")

    def test_returns_none_for_empty_csv(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write("date,n1\n")  # header only
        self.assertIsNone(gp.read_last_row(Path(f.name)))


# ---------------------------------------------------------------------------
# read_all_rows
# ---------------------------------------------------------------------------

class TestReadAllRows(unittest.TestCase):

    def _csv(self, rows):
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        )
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(tmp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        tmp.flush()
        return Path(tmp.name)

    def test_returns_all_rows_sorted_newest_first(self):
        path = self._csv([
            {"date": "2024-01-01", "n1": "1"},
            {"date": "2024-06-15", "n1": "7"},
            {"date": "2025-03-22", "n1": "42"},
        ])
        rows = gp.read_all_rows(path)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["date"], "2025-03-22")
        self.assertEqual(rows[1]["date"], "2024-06-15")
        self.assertEqual(rows[2]["date"], "2024-01-01")

    def test_single_row(self):
        path = self._csv([{"date": "2020-05-10", "n1": "3"}])
        rows = gp.read_all_rows(path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["date"], "2020-05-10")

    def test_empty_csv_returns_empty_list(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write("date,n1\n")
        rows = gp.read_all_rows(Path(f.name))
        self.assertEqual(rows, [])

    def test_already_sorted_input_still_correct(self):
        path = self._csv([
            {"date": "2025-12-31", "n1": "10"},
            {"date": "2025-01-01", "n1": "20"},
        ])
        rows = gp.read_all_rows(path)
        self.assertEqual(rows[0]["date"], "2025-12-31")
        self.assertEqual(rows[1]["date"], "2025-01-01")


# ---------------------------------------------------------------------------
# format_date
# ---------------------------------------------------------------------------

class TestFormatDate(unittest.TestCase):

    def test_standard_date(self):
        self.assertEqual(gp.format_date("2025-04-12"), "12.04.2025")

    def test_single_digit_day_and_month(self):
        self.assertEqual(gp.format_date("2004-02-05"), "05.02.2004")

    def test_year_boundary(self):
        self.assertEqual(gp.format_date("2000-01-01"), "01.01.2000")


# ---------------------------------------------------------------------------
# render_lottery_card
# ---------------------------------------------------------------------------

class TestRenderLotteryCard(unittest.TestCase):

    AT = {
        "id": "at",
        "name": "Lotto 6 aus 45",
        "flag": "🇦🇹",
        "numbers": ["n1", "n2", "n3", "n4", "n5", "n6"],
        "bonus": [("Zusatzzahl", "zusatzzahl")],
        "bonus_style": "bonus-red",
    }

    EU = {
        "id": "eu",
        "name": "Euromillionen",
        "flag": "🇪🇺",
        "numbers": ["n1", "n2", "n3", "n4", "n5"],
        "bonus": [("Lucky Star", "s1"), ("Lucky Star", "s2")],
        "bonus_style": "bonus-eu",
    }

    def test_contains_draw_date(self):
        row = {"date": "2025-03-15", "n1": "5", "n2": "10", "n3": "15",
               "n4": "20", "n5": "25", "n6": "30", "zusatzzahl": "7"}
        html = gp.render_lottery_card(self.AT, row)
        self.assertIn("15.03.2025", html)

    def test_contains_all_main_numbers(self):
        row = {"date": "2025-01-01", "n1": "3", "n2": "17", "n3": "22",
               "n4": "31", "n5": "40", "n6": "45", "zusatzzahl": "12"}
        html = gp.render_lottery_card(self.AT, row)
        for num in ["3", "17", "22", "31", "40", "45"]:
            self.assertIn(num, html)

    def test_contains_bonus_number(self):
        row = {"date": "2025-01-01", "n1": "1", "n2": "2", "n3": "3",
               "n4": "4", "n5": "5", "n6": "6", "zusatzzahl": "9"}
        html = gp.render_lottery_card(self.AT, row)
        self.assertIn("bonus-red", html)
        self.assertIn(">9<", html)

    def test_empty_bonus_omitted(self):
        row = {"date": "2025-01-01", "n1": "1", "n2": "2", "n3": "3",
               "n4": "4", "n5": "5", "n6": "6", "zusatzzahl": ""}
        html = gp.render_lottery_card(self.AT, row)
        self.assertNotIn("bonus-red", html)
        self.assertNotIn("separator", html)

    def test_two_lucky_stars_rendered(self):
        row = {"date": "2025-02-01", "n1": "10", "n2": "20", "n3": "30",
               "n4": "40", "n5": "50", "s1": "3", "s2": "11"}
        html = gp.render_lottery_card(self.EU, row)
        self.assertEqual(html.count("bonus-eu"), 2)

    def test_lottery_name_in_card(self):
        row = {"date": "2025-01-01", "n1": "1", "n2": "2", "n3": "3",
               "n4": "4", "n5": "5", "n6": "6", "zusatzzahl": "7"}
        html = gp.render_lottery_card(self.AT, row)
        self.assertIn("Lotto 6 aus 45", html)

    def test_card_id_attribute(self):
        row = {"date": "2025-01-01", "n1": "1", "n2": "2", "n3": "3",
               "n4": "4", "n5": "5", "n6": "6", "zusatzzahl": "7"}
        html = gp.render_lottery_card(self.AT, row)
        self.assertIn('id="at"', html)


# ---------------------------------------------------------------------------
# render_lottery_section
# ---------------------------------------------------------------------------

class TestRenderLotterySection(unittest.TestCase):

    AT = {
        "id": "at",
        "name": "Lotto 6 aus 45",
        "flag": "🇦🇹",
        "numbers": ["n1", "n2", "n3", "n4", "n5", "n6"],
        "bonus": [("Zusatzzahl", "zusatzzahl")],
        "bonus_style": "bonus-red",
    }

    EU = {
        "id": "eu",
        "name": "Euromillionen",
        "flag": "🇪🇺",
        "numbers": ["n1", "n2", "n3", "n4", "n5"],
        "bonus": [("Lucky Star", "s1"), ("Lucky Star", "s2")],
        "bonus_style": "bonus-eu",
    }

    def _rows_at(self):
        return [
            {"date": "2025-03-22", "n1": "1", "n2": "2", "n3": "3",
             "n4": "4", "n5": "5", "n6": "6", "zusatzzahl": "7"},
            {"date": "2025-03-15", "n1": "8", "n2": "9", "n3": "10",
             "n4": "11", "n5": "12", "n6": "13", "zusatzzahl": "2"},
        ]

    def test_returns_empty_for_no_rows(self):
        html = gp.render_lottery_section(self.AT, [])
        self.assertEqual(html, "")

    def test_contains_lottery_name(self):
        html = gp.render_lottery_section(self.AT, self._rows_at())
        self.assertIn("Lotto 6 aus 45", html)

    def test_contains_section_id(self):
        html = gp.render_lottery_section(self.AT, self._rows_at())
        self.assertIn('id="at"', html)

    def test_contains_draws_table(self):
        html = gp.render_lottery_section(self.AT, self._rows_at())
        self.assertIn("draws-table", html)

    def test_rows_appear_in_order_newest_first(self):
        html = gp.render_lottery_section(self.AT, self._rows_at())
        pos_newer = html.find("22.03.2025")
        pos_older = html.find("15.03.2025")
        self.assertLess(pos_newer, pos_older)

    def test_all_main_numbers_rendered(self):
        html = gp.render_lottery_section(self.AT, self._rows_at()[:1])
        for num in ["1", "2", "3", "4", "5", "6"]:
            self.assertIn(f">{num}<", html)

    def test_bonus_number_rendered(self):
        html = gp.render_lottery_section(self.AT, self._rows_at()[:1])
        self.assertIn("bonus-red", html)

    def test_two_lucky_stars_per_row(self):
        rows = [{"date": "2025-01-01", "n1": "1", "n2": "2", "n3": "3",
                 "n4": "4", "n5": "5", "s1": "3", "s2": "11"}]
        html = gp.render_lottery_section(self.EU, rows)
        self.assertEqual(html.count("bonus-eu"), 2)

    def test_empty_bonus_shows_dash(self):
        rows = [{"date": "2025-01-01", "n1": "1", "n2": "2", "n3": "3",
                 "n4": "4", "n5": "5", "n6": "6", "zusatzzahl": ""}]
        html = gp.render_lottery_section(self.AT, rows)
        self.assertNotIn("bonus-red", html)
        self.assertIn("–", html)

    def test_table_header_has_datum_column(self):
        html = gp.render_lottery_section(self.AT, self._rows_at())
        self.assertIn("<th>Datum</th>", html)


# ---------------------------------------------------------------------------
# generate_html
# ---------------------------------------------------------------------------

class TestGenerateHtml(unittest.TestCase):

    def test_contains_page_title(self):
        html = gp.generate_html([], "01.01.2025 12:00 UTC")
        self.assertIn("Lottery Archive", html)

    def test_contains_generated_timestamp(self):
        html = gp.generate_html([], "15.04.2026 08:30 UTC")
        self.assertIn("15.04.2026 08:30 UTC", html)

    def test_cards_included(self):
        html = gp.generate_html(["<article>Card A</article>", "<article>Card B</article>"], "x")
        self.assertIn("Card A", html)
        self.assertIn("Card B", html)

    def test_valid_html_structure(self):
        html = gp.generate_html([], "x")
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("<html", html)
        self.assertIn("</html>", html)
        self.assertIn("<body>", html)
        self.assertIn("</body>", html)


# ---------------------------------------------------------------------------
# main (integration)
# ---------------------------------------------------------------------------

class TestMain(unittest.TestCase):
    """Runs main() against the real CSV files and checks the output file."""

    def test_generates_index_html(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_root = gp.REPO_ROOT
            try:
                gp.REPO_ROOT = Path(original_root)

                captured = {}

                def patched_main():
                    sections = []
                    for lottery in gp.LOTTERIES:
                        rows = gp.read_all_rows(lottery["csv"])
                        if not rows:
                            continue
                        sections.append(gp.render_lottery_section(lottery, rows))
                    from datetime import UTC, datetime
                    ts = datetime.now(UTC).strftime("%d.%m.%Y %H:%M UTC")
                    html = gp.generate_html(sections, ts)
                    out = Path(tmpdir) / "index.html"
                    out.write_text(html, encoding="utf-8")
                    captured["html"] = html

                patched_main()
                html = captured["html"]

                self.assertIn("Lotto 6 aus 45", html)
                self.assertIn("Lotto 6 aus 49", html)
                self.assertIn("Euromillionen", html)
                self.assertIn('class="ball main"', html)
            finally:
                gp.REPO_ROOT = original_root


if __name__ == "__main__":
    unittest.main()
