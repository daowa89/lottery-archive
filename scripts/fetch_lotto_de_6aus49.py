#!/usr/bin/env python3
"""
Fetch German Lotto 6 aus 49 results from lottozahlenonline.de.

Scrapes the combined (both draw days) archive page, one year at a time:
  https://www.lottozahlenonline.de/statistik/beide-spieltage/lottozahlen-archiv.php?j=YYYY

The Superzahl (digit 0–9) was introduced on 1992-01-01. Draws before
that date are stored with an empty superzahl field.

Usage:
  python fetch_lotto_de_6aus49.py            # fetch current + previous year
  python fetch_lotto_de_6aus49.py --init     # full historical import (1955 to present)
  python fetch_lotto_de_6aus49.py --commit   # fetch and git-commit if new data found
"""

import csv
import sys
import time
from bs4 import BeautifulSoup
from datetime import date
from pathlib import Path
from typing import NamedTuple

from git_utils import git_commit
from http_utils import fetch_url

RESULTS_CSV = Path(__file__).parent.parent / "de" / "lotto_6aus49" / "results.csv"
BASE_URL = (
    "https://www.lottozahlenonline.de/statistik/beide-spieltage"
    "/lottozahlen-archiv.php"
)
FIRST_YEAR = 1955   # first German Lotto draw: 1955-10-09

NUMBER_MIN, NUMBER_MAX = 1, 49
SUPERZAHL_MIN, SUPERZAHL_MAX = 0, 9


class Draw(NamedTuple):
    date: str           # ISO format: YYYY-MM-DD
    n1: int
    n2: int
    n3: int
    n4: int
    n5: int
    n6: int
    superzahl: int | None   # None for draws before 1992 (no Superzahl)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_draw(draw: Draw) -> tuple[bool, str]:
    """
    Validate a draw against DE Lotto 6 aus 49 rules.

    Returns (is_valid, error_message). error_message is empty when valid.
    """
    numbers = [draw.n1, draw.n2, draw.n3, draw.n4, draw.n5, draw.n6]

    if len(set(numbers)) != 6:
        return False, f"duplicate numbers: {numbers}"
    if not all(NUMBER_MIN <= n <= NUMBER_MAX for n in numbers):
        out = [n for n in numbers if not NUMBER_MIN <= n <= NUMBER_MAX]
        return False, f"numbers out of range {NUMBER_MIN}-{NUMBER_MAX}: {out}"
    if draw.superzahl is not None and not (SUPERZAHL_MIN <= draw.superzahl <= SUPERZAHL_MAX):
        return False, (
            f"superzahl {draw.superzahl} out of range "
            f"{SUPERZAHL_MIN}-{SUPERZAHL_MAX}"
        )
    return True, ""


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_year_page(html: str) -> list[Draw]:
    """
    Parse one year-page from lottozahlenonline.de.

    Each draw row is a ``div.zahlensuche_rahmen`` containing:
      - ``time.zahlensuche_datum[datetime]``  — ISO date (YYYY-MM-DD)
      - ``div.zahlensuche_zahl`` (×6)         — main numbers 1–49
      - ``div.zahlensuche_zz``                — Superzahl 0–9
    """
    soup = BeautifulSoup(html, "lxml")
    draws: list[Draw] = []

    for row in soup.find_all("div", class_="zahlensuche_rahmen"):
        time_tag = row.find("time", class_="zahlensuche_datum")
        if not time_tag:
            continue
        draw_date = time_tag.get("datetime", "").strip()
        if not draw_date:
            continue

        number_divs = row.find_all("div", class_="zahlensuche_zahl")
        if len(number_divs) != 6:
            print(
                f"  WARNING: Expected 6 numbers, got {len(number_divs)} "
                f"for {draw_date} — skipping.",
                file=sys.stderr,
            )
            continue

        sz_div = row.find("div", class_="zahlensuche_zz")
        sz_text = sz_div.get_text(strip=True) if sz_div else ""

        try:
            numbers = [int(d.get_text(strip=True)) for d in number_divs]
            superzahl: int | None = int(sz_text) if sz_text else None
        except ValueError as e:
            print(
                f"  WARNING: Could not parse numbers for {draw_date}: {e} — skipping.",
                file=sys.stderr,
            )
            continue

        draw = Draw(draw_date, *numbers, superzahl)
        valid, reason = validate_draw(draw)
        if not valid:
            print(
                f"  WARNING: Skipping invalid draw {draw.date}: {reason}",
                file=sys.stderr,
            )
            continue

        draws.append(draw)

    return draws


# ---------------------------------------------------------------------------
# CSV I/O
# ---------------------------------------------------------------------------

def load_existing_dates(csv_path: Path) -> set[str]:
    """Return the set of dates already stored in the results CSV."""
    if not csv_path.exists():
        return set()
    with open(csv_path, newline="", encoding="utf-8") as f:
        return {row["date"] for row in csv.DictReader(f)}


def load_existing_draws(csv_path: Path) -> list[Draw]:
    """Return all draws currently stored in the results CSV."""
    if not csv_path.exists():
        return []
    draws: list[Draw] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                sz_str = row["superzahl"].strip()
                draws.append(Draw(
                    row["date"],
                    int(row["n1"]), int(row["n2"]), int(row["n3"]),
                    int(row["n4"]), int(row["n5"]), int(row["n6"]),
                    int(sz_str) if sz_str else None,
                ))
            except (KeyError, ValueError):
                continue
    return draws


def write_draws(new_draws: list[Draw]) -> None:
    """Merge new draws into results.csv, sort by date, and write the full file."""
    existing = load_existing_draws(RESULTS_CSV)
    merged = {d.date: d for d in existing}
    for draw in new_draws:
        merged[draw.date] = draw

    sorted_draws = sorted(merged.values(), key=lambda d: d.date)
    RESULTS_CSV.parent.mkdir(parents=True, exist_ok=True)

    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "n1", "n2", "n3", "n4", "n5", "n6", "superzahl"])
        for draw in sorted_draws:
            writer.writerow([
                draw.date, draw.n1, draw.n2, draw.n3, draw.n4, draw.n5, draw.n6,
                "" if draw.superzahl is None else draw.superzahl,
            ])


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def fetch_year(year: int, existing_dates: set[str]) -> list[Draw]:
    """Fetch all draws for one calendar year and return those not yet stored."""
    url = f"{BASE_URL}?j={year}"
    html = fetch_url(url)
    all_draws = parse_year_page(html)
    return [d for d in all_draws if d.date not in existing_dates]


def fetch_new_draws(init: bool = False) -> list[Draw]:
    """
    Download draw data and return only draws not yet in results.csv.

    init=True  — full import from FIRST_YEAR to present
    init=False — current and previous year only (catches year-boundary draws)
    """
    existing_dates = load_existing_dates(RESULTS_CSV)
    today = date.today()

    years = range(FIRST_YEAR, today.year + 1) if init else [today.year - 1, today.year]

    all_new: list[Draw] = []
    for year in years:
        print(f"  Fetching year {year}...")
        new = fetch_year(year, existing_dates)
        all_new.extend(new)
        existing_dates.update(d.date for d in new)
        if init:
            time.sleep(0.5)     # polite delay during bulk import

    return sorted(all_new, key=lambda d: d.date)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    args = sys.argv[1:]
    commit = "--commit" in args
    init = "--init" in args

    print("Fetching DE Lotto 6 aus 49...")

    try:
        new_draws = fetch_new_draws(init=init)
    except Exception as exc:
        print(f"  Fetch failed: {exc}", file=sys.stderr)
        return -1

    if new_draws:
        print(f"  {len(new_draws)} new draw(s) found:")
        for draw in new_draws:
            print(f"    {draw.date}: {draw.n1},{draw.n2},{draw.n3},"
                  f"{draw.n4},{draw.n5},{draw.n6} SZ:{draw.superzahl}")
        write_draws(new_draws)

        if commit:
            dates = ", ".join(d.date for d in new_draws)
            message = f"Add DE Lotto 6 aus 49 results: {dates}"
            if git_commit(str(RESULTS_CSV), message):
                print(f"  Committed: {message}")
    else:
        print("  No new draws found.")

    return len(new_draws)


if __name__ == "__main__":
    sys.exit(0 if main() >= 0 else 1)
