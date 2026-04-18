#!/usr/bin/env python3
"""Shared draw utilities used by all lottery fetch scripts."""


def merge_draws(new_draws: list, existing_draws: list) -> list:
    """
    Merge new draws into existing ones, deduplicating by date.

    Both lists must contain objects with a ``date`` attribute (ISO string).
    New draws take precedence over existing ones with the same date.
    Returns a new list sorted chronologically.
    """
    merged = {d.date: d for d in existing_draws}
    for draw in new_draws:
        merged[draw.date] = draw
    return sorted(merged.values(), key=lambda d: d.date)
