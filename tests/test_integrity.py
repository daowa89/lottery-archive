"""
Unit tests for check_integrity.py

All tests work with temporary CSV files — no network requests are made.
"""

import csv
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import json

from check_integrity import check_csv, check_json, GameRules


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_rules(path: Path, country: str, json_path: Path = None) -> GameRules:
    if json_path is None:
        json_path = path.with_suffix(".json")
    if country == "at":
        return GameRules(
            label="AT Lotto 6 aus 45", csv_path=path, json_path=json_path,
            number_min=1, number_max=45,
            num_count=6,
            extra_fields=["zusatzzahl"], extra_min=1, extra_max=45,
            json_extra_key="zusatzzahl",
        )
    if country == "de":
        return GameRules(
            label="DE Lotto 6 aus 49", csv_path=path, json_path=json_path,
            number_min=1, number_max=49,
            num_count=6,
            extra_fields=["superzahl"], extra_min=0, extra_max=9,
            json_extra_key="superzahl",
        )
    # eu
    return GameRules(
        label="EU EuroMillions", csv_path=path, json_path=json_path,
        number_min=1, number_max=50,
        num_count=5,
        extra_fields=["s1", "s2"], extra_min=1, extra_max=12,
        json_extra_key="stars",
    )


def write_csv(path: Path, fieldnames: list, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


AT_FIELDS = ["date", "n1", "n2", "n3", "n4", "n5", "n6", "zusatzzahl"]
DE_FIELDS = ["date", "n1", "n2", "n3", "n4", "n5", "n6", "superzahl"]
EU_FIELDS = ["date", "n1", "n2", "n3", "n4", "n5", "s1", "s2"]

VALID_AT_ROW = {"date": "2025-01-04", "n1": 1, "n2": 4, "n3": 15,
                "n4": 16, "n5": 22, "n6": 38, "zusatzzahl": 11}
VALID_AT_ROW2 = {"date": "2025-01-08", "n1": 3, "n2": 9, "n3": 18,
                 "n4": 27, "n5": 33, "n6": 41, "zusatzzahl": 5}
VALID_DE_ROW = {"date": "2021-01-02", "n1": 5, "n2": 11, "n3": 13,
                "n4": 20, "n5": 38, "n6": 40, "superzahl": 8}
VALID_EU_ROW = {"date": "2025-01-03", "n1": 3, "n2": 19, "n3": 29,
                "n4": 35, "n5": 37, "s1": 1, "s2": 9}
VALID_EU_ROW2 = {"date": "2025-01-07", "n1": 12, "n2": 17, "n3": 27,
                 "n4": 44, "n5": 50, "s1": 4, "s2": 11}


# ---------------------------------------------------------------------------
# Valid data
# ---------------------------------------------------------------------------

class TestValidData(unittest.TestCase):
    def test_clean_at_csv_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "at.csv"
            write_csv(p, AT_FIELDS, [VALID_AT_ROW, VALID_AT_ROW2])
            # Use the last draw date as reference so stale check does not fire
            self.assertEqual(check_csv(make_rules(p, "at"),
                                       reference_date=date(2025, 1, 8)), [])

    def test_clean_de_csv_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "de.csv"
            write_csv(p, DE_FIELDS, [VALID_DE_ROW])
            self.assertEqual(check_csv(make_rules(p, "de"),
                                       reference_date=date(2021, 1, 2)), [])

    def test_clean_eu_csv_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "eu.csv"
            write_csv(p, EU_FIELDS, [VALID_EU_ROW, VALID_EU_ROW2])
            self.assertEqual(check_csv(make_rules(p, "eu"),
                                       reference_date=date(2025, 1, 7)), [])


# ---------------------------------------------------------------------------
# Duplicate dates
# ---------------------------------------------------------------------------

class TestDuplicateDates(unittest.TestCase):
    def test_duplicate_date_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "at.csv"
            row2 = {**VALID_AT_ROW, "n1": 2}  # same date, different numbers
            write_csv(p, AT_FIELDS, [VALID_AT_ROW, row2])
            errors = check_csv(make_rules(p, "at"))
            self.assertTrue(any("duplicate" in e for e in errors))


# ---------------------------------------------------------------------------
# Number ranges
# ---------------------------------------------------------------------------

class TestNumberRanges(unittest.TestCase):
    def test_at_number_46_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "at.csv"
            write_csv(p, AT_FIELDS, [{**VALID_AT_ROW, "n6": 46}])
            errors = check_csv(make_rules(p, "at"))
            self.assertTrue(any("out of range" in e for e in errors))

    def test_de_number_50_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "de.csv"
            write_csv(p, DE_FIELDS, [{**VALID_DE_ROW, "n6": 50}])
            errors = check_csv(make_rules(p, "de"))
            self.assertTrue(any("out of range" in e for e in errors))

    def test_de_superzahl_10_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "de.csv"
            write_csv(p, DE_FIELDS, [{**VALID_DE_ROW, "superzahl": 10}])
            errors = check_csv(make_rules(p, "de"))
            self.assertTrue(any("superzahl" in e for e in errors))

    def test_de_empty_superzahl_passes(self):
        """Pre-1992 DE draws have an empty superzahl field — must not be an error."""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "de.csv"
            write_csv(p, DE_FIELDS, [{**VALID_DE_ROW, "superzahl": ""}])
            errors = check_csv(make_rules(p, "de"),
                               reference_date=date(2021, 1, 2))
            self.assertEqual(errors, [])

    def test_at_zusatzzahl_0_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "at.csv"
            write_csv(p, AT_FIELDS, [{**VALID_AT_ROW, "zusatzzahl": 0}])
            errors = check_csv(make_rules(p, "at"))
            self.assertTrue(any("zusatzzahl" in e for e in errors))

    def test_eu_main_number_51_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "eu.csv"
            write_csv(p, EU_FIELDS, [{**VALID_EU_ROW, "n5": 51}])
            errors = check_csv(make_rules(p, "eu"))
            self.assertTrue(any("out of range" in e for e in errors))

    def test_eu_star_13_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "eu.csv"
            write_csv(p, EU_FIELDS, [{**VALID_EU_ROW, "s2": 13}])
            errors = check_csv(make_rules(p, "eu"))
            self.assertTrue(any("s2" in e for e in errors))

    def test_eu_duplicate_stars_reported(self):
        """Two identical star numbers in one row must be flagged."""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "eu.csv"
            write_csv(p, EU_FIELDS, [{**VALID_EU_ROW, "s1": 9, "s2": 9}])
            errors = check_csv(make_rules(p, "eu"))
            self.assertTrue(any("duplicate" in e for e in errors))


# ---------------------------------------------------------------------------
# Sort order
# ---------------------------------------------------------------------------

class TestSortOrder(unittest.TestCase):
    def test_unsorted_dates_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "at.csv"
            # Write in reverse order (newer date first)
            write_csv(p, AT_FIELDS, [VALID_AT_ROW2, VALID_AT_ROW])
            errors = check_csv(make_rules(p, "at"))
            self.assertTrue(any("sorted" in e for e in errors))


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases(unittest.TestCase):
    def test_missing_file_reported(self):
        errors = check_csv(make_rules(Path("/nonexistent/path.csv"), "at"))
        self.assertTrue(any("not found" in e for e in errors))

    def test_empty_file_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "at.csv"
            write_csv(p, AT_FIELDS, [])
            errors = check_csv(make_rules(p, "at"))
            self.assertTrue(any("empty" in e for e in errors))


# ---------------------------------------------------------------------------
# Stale data detection
# ---------------------------------------------------------------------------

class TestStaleData(unittest.TestCase):
    def test_fresh_data_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "at.csv"
            today = date.today()
            row = {**VALID_AT_ROW, "date": today.isoformat()}
            write_csv(p, AT_FIELDS, [row])
            rules = make_rules(p, "at")
            # reference_date = today, last draw = today → 0 days → OK
            errors = check_csv(rules, reference_date=today)
            self.assertFalse(any("stale" in e for e in errors))

    def test_data_within_threshold_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "at.csv"
            last_draw = date(2025, 1, 1)
            row = {**VALID_AT_ROW, "date": last_draw.isoformat()}
            write_csv(p, AT_FIELDS, [row])
            rules = make_rules(p, "at")
            # 6 days since last draw, threshold is 7 → OK
            reference = last_draw + timedelta(days=6)
            errors = check_csv(rules, reference_date=reference)
            self.assertFalse(any("stale" in e for e in errors))

    def test_stale_data_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "at.csv"
            last_draw = date(2025, 1, 1)
            row = {**VALID_AT_ROW, "date": last_draw.isoformat()}
            write_csv(p, AT_FIELDS, [row])
            rules = make_rules(p, "at")
            # 10 days since last draw, threshold is 7 → stale
            reference = last_draw + timedelta(days=10)
            errors = check_csv(rules, reference_date=reference)
            self.assertTrue(any("stale" in e for e in errors))

    def test_stale_error_mentions_last_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "at.csv"
            last_draw = date(2025, 3, 15)
            row = {**VALID_AT_ROW, "date": last_draw.isoformat()}
            write_csv(p, AT_FIELDS, [row])
            rules = make_rules(p, "at")
            reference = last_draw + timedelta(days=14)
            errors = check_csv(rules, reference_date=reference)
            self.assertTrue(any("2025-03-15" in e for e in errors))

    def test_skip_stale_suppresses_stale_error(self):
        """With skip_stale=True, stale data must not be reported."""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "at.csv"
            last_draw = date(2025, 1, 1)
            row = {**VALID_AT_ROW, "date": last_draw.isoformat()}
            write_csv(p, AT_FIELDS, [row])
            rules = make_rules(p, "at")
            reference = last_draw + timedelta(days=30)
            errors = check_csv(rules, reference_date=reference, skip_stale=True)
            self.assertFalse(any("stale" in e for e in errors))

    def test_skip_stale_still_catches_other_errors(self):
        """skip_stale=True must not suppress unrelated errors like duplicates."""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "at.csv"
            row2 = {**VALID_AT_ROW, "n1": 2}
            write_csv(p, AT_FIELDS, [VALID_AT_ROW, row2])  # duplicate date
            rules = make_rules(p, "at")
            errors = check_csv(rules, skip_stale=True)
            self.assertTrue(any("duplicate" in e for e in errors))


# ---------------------------------------------------------------------------
# JSON integrity: check_json
# ---------------------------------------------------------------------------

AT_JSON_ENTRY  = {"date": "2025-01-04", "numbers": [1, 4, 15, 16, 22, 38], "zusatzzahl": 11}
AT_JSON_ENTRY2 = {"date": "2025-01-08", "numbers": [3, 9, 18, 27, 33, 41], "zusatzzahl": 5}


class TestJsonIntegrity(unittest.TestCase):
    def _rules(self, csv_path: Path, json_path: Path) -> GameRules:
        return make_rules(csv_path, "at", json_path=json_path)

    def test_missing_json_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_p = Path(tmp) / "at.csv"
            json_p = Path(tmp) / "at.json"   # not created
            write_csv(csv_p, AT_FIELDS, [VALID_AT_ROW])
            errors = check_json(self._rules(csv_p, json_p), csv_rows=[VALID_AT_ROW])
            self.assertTrue(any("not found" in e for e in errors))

    def test_invalid_json_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_p = Path(tmp) / "at.csv"
            json_p = Path(tmp) / "at.json"
            write_csv(csv_p, AT_FIELDS, [VALID_AT_ROW])
            json_p.write_text("not valid json", encoding="utf-8")
            errors = check_json(self._rules(csv_p, json_p), csv_rows=[VALID_AT_ROW])
            self.assertTrue(any("valid JSON" in e for e in errors))

    def test_count_mismatch_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_p = Path(tmp) / "at.csv"
            json_p = Path(tmp) / "at.json"
            write_csv(csv_p, AT_FIELDS, [VALID_AT_ROW])
            json_p.write_text(json.dumps([]), encoding="utf-8")  # 0 entries vs 1
            errors = check_json(self._rules(csv_p, json_p), csv_rows=[VALID_AT_ROW])
            self.assertTrue(any("count" in e for e in errors))

    def test_valid_json_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_p = Path(tmp) / "at.csv"
            json_p = Path(tmp) / "at.json"
            write_csv(csv_p, AT_FIELDS, [VALID_AT_ROW])
            json_p.write_text(json.dumps([AT_JSON_ENTRY]), encoding="utf-8")
            errors = check_json(self._rules(csv_p, json_p), csv_rows=[VALID_AT_ROW])
            self.assertEqual(errors, [])

    def test_number_mismatch_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_p = Path(tmp) / "at.csv"
            json_p = Path(tmp) / "at.json"
            write_csv(csv_p, AT_FIELDS, [VALID_AT_ROW])
            wrong = {**AT_JSON_ENTRY, "numbers": [1, 2, 3, 4, 5, 6]}
            json_p.write_text(json.dumps([wrong]), encoding="utf-8")
            errors = check_json(self._rules(csv_p, json_p), csv_rows=[VALID_AT_ROW])
            self.assertTrue(any("numbers differ" in e for e in errors))

    def test_bonus_mismatch_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_p = Path(tmp) / "at.csv"
            json_p = Path(tmp) / "at.json"
            write_csv(csv_p, AT_FIELDS, [VALID_AT_ROW])
            wrong = {**AT_JSON_ENTRY, "zusatzzahl": 99}
            json_p.write_text(json.dumps([wrong]), encoding="utf-8")
            errors = check_json(self._rules(csv_p, json_p), csv_rows=[VALID_AT_ROW])
            self.assertTrue(any("zusatzzahl" in e for e in errors))

    def test_date_missing_in_json_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_p = Path(tmp) / "at.csv"
            json_p = Path(tmp) / "at.json"
            write_csv(csv_p, AT_FIELDS, [VALID_AT_ROW, VALID_AT_ROW2])
            json_p.write_text(json.dumps([AT_JSON_ENTRY]), encoding="utf-8")
            errors = check_json(self._rules(csv_p, json_p), csv_rows=[VALID_AT_ROW, VALID_AT_ROW2])
            self.assertTrue(any("missing in JSON" in e for e in errors))

    def test_date_extra_in_json_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_p = Path(tmp) / "at.csv"
            json_p = Path(tmp) / "at.json"
            write_csv(csv_p, AT_FIELDS, [VALID_AT_ROW])
            json_p.write_text(json.dumps([AT_JSON_ENTRY, AT_JSON_ENTRY2]), encoding="utf-8")
            errors = check_json(self._rules(csv_p, json_p), csv_rows=[VALID_AT_ROW])
            self.assertTrue(any("not in CSV" in e for e in errors))

    def test_eu_stars_compared_correctly(self):
        """EuroMillions stars are stored as a JSON array — comparison must handle this."""
        with tempfile.TemporaryDirectory() as tmp:
            csv_p = Path(tmp) / "eu.csv"
            json_p = Path(tmp) / "eu.json"
            write_csv(csv_p, EU_FIELDS, [VALID_EU_ROW])
            entry = {"date": "2025-01-03", "numbers": [3, 19, 29, 35, 37], "stars": [1, 9]}
            json_p.write_text(json.dumps([entry]), encoding="utf-8")
            errors = check_json(make_rules(csv_p, "eu", json_path=json_p), csv_rows=[VALID_EU_ROW])
            self.assertEqual(errors, [])

    def test_eu_stars_mismatch_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_p = Path(tmp) / "eu.csv"
            json_p = Path(tmp) / "eu.json"
            write_csv(csv_p, EU_FIELDS, [VALID_EU_ROW])
            entry = {"date": "2025-01-03", "numbers": [3, 19, 29, 35, 37], "stars": [2, 9]}
            json_p.write_text(json.dumps([entry]), encoding="utf-8")
            errors = check_json(make_rules(csv_p, "eu", json_path=json_p), csv_rows=[VALID_EU_ROW])
            self.assertTrue(any("stars" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
