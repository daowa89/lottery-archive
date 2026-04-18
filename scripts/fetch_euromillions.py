#!/usr/bin/env python3
"""
Fetch EuroMillions results from win2day.at.

Two data sources:
  - Yearly CSVs (2017–present):
    https://statics.win2day.at/media/NN_W2D_STAT_EUML_{YEAR}.csv
  - Historical CSV (2004–2016):
    https://statics.win2day.at/media-nopagespeed/euromillionen-ergebnisse-2004-2017.csv

EuroMillions rules:
  - 5 main numbers drawn from 1–50
  - 2 star numbers drawn from 1–12
  - Draws on Tuesday and Friday

Usage:
  python fetch_euromillions.py            # fetch current + previous year
  python fetch_euromillions.py --init     # full historical import (2004 to present)
  python fetch_euromillions.py --commit   # fetch and git-commit if new data found
"""

import csv
import io
import json
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import NamedTuple

from draw_utils import merge_draws
from git_utils import git_commit
from http_utils import fetch_url, BROWSER_HEADERS

RESULTS_CSV = Path(__file__).parent.parent / "eu" / "euromillions" / "results.csv"
RESULTS_JSON = Path(__file__).parent.parent / "eu" / "euromillions" / "results.json"

YEARLY_URL = "https://statics.win2day.at/media/NN_W2D_STAT_EUML_{year}.csv"
HISTORICAL_URL = (
    "https://statics.win2day.at/media-nopagespeed"
    "/euromillionen-ergebnisse-2004-2017.csv"
)

FIRST_YEARLY_YEAR = 2017
FIRST_YEAR = 2004

NUMBER_MIN, NUMBER_MAX = 1, 50
STAR_MIN, STAR_MAX = 1, 12


class Draw(NamedTuple):
    date: str   # ISO format: YYYY-MM-DD
    n1: int
    n2: int
    n3: int
    n4: int
    n5: int
    s1: int
    s2: int


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_draw(draw: Draw) -> tuple[bool, str]:
    """
    Validate a draw against EuroMillions rules.

    Returns (is_valid, error_message). error_message is empty when valid.
    """
    numbers = [draw.n1, draw.n2, draw.n3, draw.n4, draw.n5]
    stars = [draw.s1, draw.s2]

    if len(set(numbers)) != 5:
        return False, f"duplicate main numbers: {numbers}"
    if not all(NUMBER_MIN <= n <= NUMBER_MAX for n in numbers):
        out = [n for n in numbers if not NUMBER_MIN <= n <= NUMBER_MAX]
        return False, f"main numbers out of range {NUMBER_MIN}-{NUMBER_MAX}: {out}"
    if len(set(stars)) != 2:
        return False, f"duplicate star numbers: {stars}"
    if not all(STAR_MIN <= s <= STAR_MAX for s in stars):
        out = [s for s in stars if not STAR_MIN <= s <= STAR_MAX]
        return False, f"star numbers out of range {STAR_MIN}-{STAR_MAX}: {out}"
    return True, ""


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_DATE_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")


def _parse_date(raw: str) -> str | None:
    """Parse a date string like 'Fr. 03.01.2025' or '13.02.2004' into 'YYYY-MM-DD'."""
    m = _DATE_RE.search(raw)
    if not m:
        return None
    day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_yearly_file(content: str) -> list[Draw]:
    """
    Parse a yearly CSV from win2day.at (2017–present).

    Format (semicolon-delimited):
      Ziehungstag;Zahl1;Zahl2;Zahl3;Zahl4;Zahl5;Stern1;Stern2;...
      Fr. 03.01.2025;3;19;29;35;37;1;9;...

    Rows with an empty first column are prize detail rows and are skipped.
    """
    draws: list[Draw] = []
    reader = csv.reader(io.StringIO(content), delimiter=";")
    header_skipped = False

    for row in reader:
        if not row:
            continue
        if not header_skipped:
            header_skipped = True
            continue  # skip header row

        date_raw = row[0].strip()
        if not date_raw:
            continue  # prize detail row

        draw_date = _parse_date(date_raw)
        if not draw_date:
            continue

        try:
            numbers = [int(row[i]) for i in range(1, 6)]
            stars = [int(row[i]) for i in range(6, 8)]
        except (IndexError, ValueError) as e:
            print(
                f"  WARNING: Could not parse numbers for {date_raw}: {e} — skipping.",
                file=sys.stderr,
            )
            continue

        draw = Draw(draw_date, *numbers, *stars)
        valid, reason = validate_draw(draw)
        if not valid:
            print(
                f"  WARNING: Skipping invalid draw {draw.date}: {reason}",
                file=sys.stderr,
            )
            continue

        draws.append(draw)

    return draws


def parse_historical_file(content: str) -> list[Draw]:
    """
    Parse the historical CSV (2004–2017) from win2day.at.

    The file uses a sideways layout with two draws per block.
    Each block starts with a header row identifiable by col[1] == "Ergebnisse:".
    The format changed slightly between the 2004–2010 and 2011–2017 sections, but
    in both cases the dates can be found by scanning all cells for DD.MM.YYYY patterns.

    The ascending-order numbers follow immediately after the first label row:
      Draw 1: main numbers at columns [1:6], stars at columns [6:8]
      Draw 2: main numbers at columns [13:18], stars at columns [18:20]
    """
    draws: list[Draw] = []
    reader = csv.reader(io.StringIO(content), delimiter=";")
    rows = list(reader)

    today_year = date.today().year

    i = 0
    while i < len(rows):
        row = rows[i]

        # Detect block header: col[1] == "Ergebnisse:"
        if len(row) < 2 or row[1].strip() != "Ergebnisse:":
            i += 1
            continue

        # Collect the first two dates found in the header row in appearance
        # order.  The position (first vs. second) determines the slot — slot 0
        # holds the left draw (columns 1–5/6–7) and slot 1 the right draw
        # (columns 13–17/18–19).  Corrupted years are set to None so the slot
        # index is preserved even when one date is invalid.
        raw_dates: list[str] = []
        for cell in row:
            d = _parse_date(cell.strip())
            if d:
                raw_dates.append(d)
                if len(raw_dates) == 2:
                    break
        while len(raw_dates) < 2:
            raw_dates.append("")

        dates: list[str | None] = []
        for d in raw_dates:
            try:
                yr = int(d[:4]) if d else 0
                dates.append(d if 2004 <= yr <= today_year + 1 else None)
            except ValueError:
                dates.append(None)

        # Skip label rows (e.g. "aufsteigende Reihenfolge:") until we reach
        # the ascending-order numbers row (first row where col[1] is an integer).
        i += 1
        while i < len(rows):
            try:
                int(rows[i][1].strip())
                break
            except (ValueError, IndexError):
                i += 1
        if i >= len(rows):
            break
        num_row = rows[i]

        # Fixed column offsets for draw 1 and draw 2
        slot_offsets = [
            (1, 6, dates[0]),
            (13, 18, dates[1]),
        ]

        for main_start, star_start, draw_date in slot_offsets:
            if not draw_date:
                continue
            try:
                numbers = [int(num_row[j]) for j in range(main_start, main_start + 5)]
                stars = [int(num_row[j]) for j in range(star_start, star_start + 2)]
            except (IndexError, ValueError) as e:
                print(
                    f"  WARNING: Could not parse numbers for {draw_date}: {e} — skipping.",
                    file=sys.stderr,
                )
                continue

            draw = Draw(draw_date, *numbers, *stars)
            valid, reason = validate_draw(draw)
            if not valid:
                print(
                    f"  WARNING: Skipping invalid draw {draw.date}: {reason}",
                    file=sys.stderr,
                )
                continue

            draws.append(draw)

        i += 1

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
                draws.append(Draw(
                    row["date"],
                    int(row["n1"]), int(row["n2"]), int(row["n3"]),
                    int(row["n4"]), int(row["n5"]),
                    int(row["s1"]), int(row["s2"]),
                ))
            except (KeyError, ValueError):
                continue
    return draws


def write_csv(new_draws: list[Draw]) -> None:
    """Merge new draws into results.csv, sort by date, and write the full file."""
    sorted_draws = merge_draws(new_draws, load_existing_draws(RESULTS_CSV))
    RESULTS_CSV.parent.mkdir(parents=True, exist_ok=True)

    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "n1", "n2", "n3", "n4", "n5", "s1", "s2"])
        for draw in sorted_draws:
            writer.writerow([
                draw.date,
                draw.n1, draw.n2, draw.n3, draw.n4, draw.n5,
                draw.s1, draw.s2,
            ])


def load_existing_draws_json(json_path: Path) -> list[Draw]:
    """Return all draws currently stored in the results JSON."""
    if not json_path.exists():
        return []
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    draws: list[Draw] = []
    for entry in data:
        try:
            draws.append(Draw(
                entry["date"],
                *entry["numbers"],
                *entry["stars"],
            ))
        except (KeyError, TypeError, ValueError):
            continue
    return draws


def write_json(new_draws: list[Draw]) -> None:
    """Merge new draws and write results.json. Independent of results.csv."""
    sorted_draws = merge_draws(new_draws, load_existing_draws_json(RESULTS_JSON))
    data = [
        {
            "date": d.date,
            "numbers": [d.n1, d.n2, d.n3, d.n4, d.n5],
            "stars": [d.s1, d.s2],
        }
        for d in sorted_draws
    ]
    RESULTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def fetch_new_draws(init: bool = False) -> list[Draw]:
    """
    Download draw data and return only draws not yet in results.csv.

    init=True  — full import from 2004 to present
    init=False — current and previous year only
    """
    existing_dates = load_existing_dates(RESULTS_CSV)
    today = date.today()
    all_new: list[Draw] = []

    if init:
        print("  Fetching historical data (2004–2016)...")
        content = fetch_url(HISTORICAL_URL, headers=BROWSER_HEADERS)
        hist_draws = parse_historical_file(content)
        new = [d for d in hist_draws if d.date not in existing_dates]
        all_new.extend(new)
        existing_dates.update(d.date for d in new)
        time.sleep(0.5)

    years = (
        range(FIRST_YEARLY_YEAR, today.year + 1)
        if init
        else [today.year - 1, today.year]
    )

    for year in years:
        print(f"  Fetching year {year}...")
        url = YEARLY_URL.format(year=year)
        content = fetch_url(url, headers=BROWSER_HEADERS)
        year_draws = parse_yearly_file(content)
        new = [d for d in year_draws if d.date not in existing_dates]
        all_new.extend(new)
        existing_dates.update(d.date for d in new)
        if init:
            time.sleep(0.5)

    return sorted(all_new, key=lambda d: d.date)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    args = sys.argv[1:]
    commit = "--commit" in args
    init = "--init" in args

    print("Fetching EuroMillions...")

    try:
        new_draws = fetch_new_draws(init=init)
    except Exception as exc:
        print(f"  Fetch failed: {exc}", file=sys.stderr)
        return -1

    if new_draws:
        print(f"  {len(new_draws)} new draw(s) found:")
        for draw in new_draws:
            print(
                f"    {draw.date}: {draw.n1},{draw.n2},{draw.n3},"
                f"{draw.n4},{draw.n5} S:{draw.s1},{draw.s2}"
            )
        write_csv(new_draws)
        write_json(new_draws)

        if commit:
            dates = ", ".join(d.date for d in new_draws)
            message = f"Add EU EuroMillions results: {dates}"
            if git_commit([str(RESULTS_CSV), str(RESULTS_JSON)], message):
                print(f"  Committed: {message}")
    else:
        print("  No new draws found.")

    return len(new_draws)


if __name__ == "__main__":
    sys.exit(0 if main() >= 0 else 1)
