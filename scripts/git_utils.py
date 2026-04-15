#!/usr/bin/env python3
"""Shared git utilities used by all lottery update scripts."""

import subprocess


def git_commit(file: str, message: str) -> bool:
    """
    Stage a single file and create a commit if there are staged changes.

    Returns True if a commit was created, False if nothing changed.
    """
    subprocess.run(["git", "add", file], check=True)
    result = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if result.returncode == 0:
        return False
    subprocess.run(["git", "commit", "-m", message], check=True)
    return True
