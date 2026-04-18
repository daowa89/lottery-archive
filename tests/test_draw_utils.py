"""Unit tests for draw_utils.py"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from draw_utils import merge_draws


def _draw(date: str, n1: int = 1):
    d = MagicMock()
    d.date = date
    d.n1 = n1
    return d


class TestMergeDraws(unittest.TestCase):
    def test_new_draws_added_to_empty(self):
        result = merge_draws([_draw("2025-01-04")], [])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].date, "2025-01-04")

    def test_existing_draws_kept_when_no_new(self):
        result = merge_draws([], [_draw("2025-01-01")])
        self.assertEqual(len(result), 1)

    def test_both_empty_returns_empty(self):
        self.assertEqual(merge_draws([], []), [])

    def test_result_sorted_chronologically(self):
        existing = [_draw("2025-01-04")]
        new = [_draw("2025-01-01")]
        result = merge_draws(new, existing)
        self.assertEqual([d.date for d in result], ["2025-01-01", "2025-01-04"])

    def test_new_draw_overwrites_existing_same_date(self):
        old = _draw("2025-01-04", n1=1)
        new = _draw("2025-01-04", n1=99)
        result = merge_draws([new], [old])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].n1, 99)

    def test_existing_draw_kept_when_no_new_for_same_date(self):
        existing = [_draw("2025-01-01"), _draw("2025-01-04")]
        new = [_draw("2025-01-07")]
        result = merge_draws(new, existing)
        self.assertEqual(len(result), 3)

    def test_does_not_modify_input_lists(self):
        existing = [_draw("2025-01-01")]
        new = [_draw("2025-01-04")]
        merge_draws(new, existing)
        self.assertEqual(len(existing), 1)
        self.assertEqual(len(new), 1)


if __name__ == "__main__":
    unittest.main()
