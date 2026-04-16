"""
Unit tests for git_utils.py

Uses unittest.mock — no actual git commands are executed.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from git_utils import git_commit


class TestGitCommit(unittest.TestCase):
    def test_returns_false_when_nothing_staged(self):
        """git diff --cached --quiet exits 0 (no changes) → False returned."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            self.assertFalse(git_commit(["/some/file.csv"], "msg"))

    def test_returns_true_when_changes_staged(self):
        """git diff --cached --quiet exits 1 (changes present) → commit created → True."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git add
                MagicMock(returncode=1),  # git diff --cached --quiet (1 = changes)
                MagicMock(returncode=0),  # git commit
            ]
            self.assertTrue(git_commit(["/some/file.csv"], "msg"))

    def test_git_add_called_with_correct_file(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            git_commit(["/data/results.csv"], "msg")
            mock_run.assert_any_call(
                ["git", "add", "/data/results.csv"], check=True
            )

    def test_commit_not_called_when_nothing_staged(self):
        """When diff reports no changes, git commit must never be invoked."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            git_commit(["/some/file.csv"], "msg")
            for c in mock_run.call_args_list:
                self.assertNotIn("commit", c.args[0])

    def test_commit_called_with_correct_message(self):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # git add
                MagicMock(returncode=1),  # git diff
                MagicMock(returncode=0),  # git commit
            ]
            git_commit(["/some/file.csv"], "Add DE results: 2025-01-04")
            mock_run.assert_called_with(
                ["git", "commit", "-m", "Add DE results: 2025-01-04"],
                check=True,
            )

    def test_git_add_always_called_first(self):
        """git add must be the very first subprocess call."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            git_commit(["/some/file.csv"], "msg")
            first_call = mock_run.call_args_list[0]
            self.assertEqual(first_call, call(["git", "add", "/some/file.csv"], check=True))

    def test_all_files_are_staged(self):
        """Every file in the list must be staged before the diff check."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            git_commit(["/a.csv", "/a.json"], "msg")
            mock_run.assert_any_call(["git", "add", "/a.csv"], check=True)
            mock_run.assert_any_call(["git", "add", "/a.json"], check=True)


if __name__ == "__main__":
    unittest.main()
