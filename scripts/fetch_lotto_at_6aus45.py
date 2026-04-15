#!/usr/bin/env python3
"""
Fetch Austrian Lotto 6 aus 45 results from win2day.at.

Sources:
  - Historical 1986-2010: statics.win2day.at/media-nopagespeed/lotto-ergebnisse-1986-2010.csv
  - Historical 2010-2017: statics.win2day.at/media-nopagespeed/lotto-ziehungen-2010-2017.csv
  - Yearly 2018+:         statics.win2day.at/media/NN_W2D_STAT_Lotto_{YEAR}.csv

Usage:
  python fetch_lotto_at_6aus45.py                    # fetch recent draws
  python fetch_lotto_at_6aus45.py --init             # fetch full history (1986 to present)
  python fetch_lotto_at_6aus45.py --commit           # fetch and git-commit if new data found
  python fetch_lotto_at_6aus45.py --init --commit    # full history + commit
"""

import csv
import re
import sys
import time
import requests
from datetime import date, datetime
from io import StringIO
from pathlib import Path
from typing import NamedTuple

from git_utils import git_commit

RESULTS_CSV = Path(__file__).parent.parent / "at" / "lotto_6aus45" / "results.csv"
YEARLY_BASE_URL = "https://statics.win2day.at/media/NN_W2D_STAT_Lotto_{year}.csv"
HISTORICAL_URLS = [
    "https://statics.win2day.at/media-nopagespeed/lotto-ergebnisse-1986-2010.csv",
    "https://statics.win2day.at/media-nopagespeed/lotto-ziehungen-2010-2017.csv",
]
YEARLY_START = 2018

WEEKDAYS = {"Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"}
YEAR_HEADER_RE = re.compile(r"^(\d{4})\s+Lotto", re.IGNORECASE)

# Valid number ranges for AT Lotto 6 aus 45
NUMBER_MIN, NUMBER_MAX = 1, 45
ZUSATZZAHL_MIN, ZUSATZZAHL_MAX = 1, 45


class Draw(NamedTuple):
    date: str       # ISO format: YYYY-MM-DD
    n1: int
    n2: int
    n3: int
    n4: int
    n5: int
    n6: int
    zusatzzahl: int


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_draw(draw: Draw) -> tuple[bool, str]:
    """
    Validate a draw against AT Lotto 6 aus 45 rules.

    Returns (is_valid, error_message). error_message is empty when valid.
    """
    numbers = [draw.n1, draw.n2, draw.n3, draw.n4, draw.n5, draw.n6]

    if len(set(numbers)) != 6:
        return False, f"duplicate numbers: {numbers}"
    if not all(NUMBER_MIN <= n <= NUMBER_MAX for n in numbers):
        out = [n for n in numbers if not NUMBER_MIN <= n <= NUMBER_MAX]
        return False, f"numbers out of range {NUMBER_MIN}-{NUMBER_MAX}: {out}"
    if not (ZUSATZZAHL_MIN <= draw.zusatzzahl <= ZUSATZZAHL_MAX):
        return False, (
            f"zusatzzahl {draw.zusatzzahl} out of range "
            f"{ZUSATZZAHL_MIN}-{ZUSATZZAHL_MAX}"
        )
    return True, ""


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

def fetch_url(url: str, retries: int = 3, backoff: float = 2.0) -> str:
    """
    Download a URL and return the text content.
    Retries up to `retries` times with exponential backoff on transient errors.
    """
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "windows-1252"
            return resp.text
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < retries:
                wait = backoff ** attempt
                print(f"  Attempt {attempt} failed ({exc}). Retrying in {wait:.0f}s...")
                time.sleep(wait)
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_date_str(date_str: str, year: int) -> date | None:
    """Parse a 'DD.M.' or 'DD.MM.' date string using the given year."""
    cleaned = date_str.strip().rstrip(".")
    parts = cleaned.split(".")
    if len(parts) < 2:
        return None
    try:
        return date(year, int(parts[1]), int(parts[0]))
    except ValueError:
        return None


def parse_yearly_file(content: str, year: int) -> list[Draw]:
    """
    Parse the modern yearly CSV format used from 2018 onwards.

    Format (semicolon-separated):
        Datum;Reihenfolge;Zahl1;Zahl2;Zahl3;Zahl4;Zahl5;Zahl6;ZZ;Zusatzzahl;...
        04.01.;aufsteigend;1;4;15;16;22;38;ZZ;11;...
        04.01.;;;;;;;;;;...   <- second row per draw (prize tiers, skipped)

    Only rows with Reihenfolge == 'aufsteigend' contain draw numbers.
    """
    draws: list[Draw] = []
    reader = csv.reader(StringIO(content), delimiter=";")
    header_found = False

    for row in reader:
        if not row or not row[0].strip():
            continue
        if not header_found:
            if row[0].strip() == "Datum":
                header_found = True
            continue
        if len(row) < 10 or row[1].strip() != "aufsteigend":
            continue

        draw_date = parse_date_str(row[0], year)
        if draw_date is None:
            continue

        try:
            numbers = [int(row[i]) for i in range(2, 8)]
            zusatzzahl = int(row[9])
        except (ValueError, IndexError):
            continue

        draw = Draw(draw_date.isoformat(), *numbers, zusatzzahl)
        valid, reason = validate_draw(draw)
        if not valid:
            print(f"  WARNING: Skipping invalid draw {draw.date}: {reason}",
                  file=sys.stderr)
            continue

        draws.append(draw)

    return draws


def parse_historical_file(content: str) -> list[Draw]:
    """
    Parse the multi-year historical CSV format (1986-2010, 2010-2017).

    Year header lines like '2010 Lotto - Beträge in EUR' mark year boundaries.

    Two column layouts are used:
      Format A (2010-2017): Weekday; Date; "aufsteigend"; N1-N6; "Zz"; Zusatzzahl; ...
      Format B (1986-2010): Weekday.; Date; N1-N6; "Zz:"; Zusatzzahl; ...
    """
    draws: list[Draw] = []
    current_year: int | None = None
    reader = csv.reader(StringIO(content), delimiter=";")

    for row in reader:
        if not row:
            continue
        first = row[0].strip()

        match = YEAR_HEADER_RE.match(first)
        if match:
            current_year = int(match.group(1))
            continue
        if current_year is None:
            continue

        # Normalise weekday: both "So" (2010-2017) and "So." (1986-2010) are valid
        weekday = first.rstrip(".")
        if weekday not in WEEKDAYS:
            continue

        order = row[2].strip() if len(row) > 2 else ""

        if order == "aufsteigend" and len(row) >= 11:
            # Format A (2010-2017)
            draw_date = parse_date_str(row[1], current_year)
            try:
                numbers = [int(row[i]) for i in range(3, 9)]
                zusatzzahl = int(row[10])
            except (ValueError, IndexError):
                continue
        elif len(row) >= 10:
            # Format B (1986-2010): N1-N6 start at column 2, Zusatzzahl at column 9
            draw_date = parse_date_str(row[1], current_year)
            try:
                numbers = [int(row[i]) for i in range(2, 8)]
                zusatzzahl = int(row[9])
            except (ValueError, IndexError):
                continue
        else:
            continue

        if draw_date is None:
            continue

        draw = Draw(draw_date.isoformat(), *numbers, zusatzzahl)
        valid, reason = validate_draw(draw)
        if not valid:
            print(f"  WARNING: Skipping invalid draw {draw.date}: {reason}",
                  file=sys.stderr)
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
                draws.append(Draw(
                    row["date"],
                    int(row["n1"]), int(row["n2"]), int(row["n3"]),
                    int(row["n4"]), int(row["n5"]), int(row["n6"]),
                    int(row["zusatzzahl"]),
                ))
            except (KeyError, ValueError):
                continue
    return draws


def fetch_new_draws(init: bool = False) -> list[Draw]:
    """
    Fetch draws from win2day.at and return only those not yet in results.csv.

    Args:
        init: If True, download full history from 1986. Otherwise only fetch
              the current and previous year (sufficient for regular updates).
    """
    current_year = datetime.today().year
    existing_dates = load_existing_dates(RESULTS_CSV)
    all_draws: list[Draw] = []

    if init:
        for url in HISTORICAL_URLS:
            print(f"  Fetching historical file: {url}")
            try:
                content = fetch_url(url)
                all_draws.extend(parse_historical_file(content))
            except requests.RequestException as e:
                print(f"  WARNING: Could not fetch {url}: {e}", file=sys.stderr)
        years = range(YEARLY_START, current_year + 1)
    else:
        years = [current_year - 1, current_year]

    for year in years:
        url = YEARLY_BASE_URL.format(year=year)
        print(f"  Fetching yearly file: {url}")
        try:
            content = fetch_url(url)
            all_draws.extend(parse_yearly_file(content, year))
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                print(f"  Skipping {year}: file not yet available.")
            else:
                print(f"  WARNING: HTTP error for {year}: {e}", file=sys.stderr)
        except requests.RequestException as e:
            print(f"  WARNING: Could not fetch {year}: {e}", file=sys.stderr)

    seen: set[str] = set()
    new_draws: list[Draw] = []
    for draw in sorted(all_draws, key=lambda d: d.date):
        if draw.date in seen or draw.date in existing_dates:
            continue
        seen.add(draw.date)
        new_draws.append(draw)

    return new_draws


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
        writer.writerow(["date", "n1", "n2", "n3", "n4", "n5", "n6", "zusatzzahl"])
        for draw in sorted_draws:
            writer.writerow(draw)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    init = "--init" in sys.argv
    commit = "--commit" in sys.argv
    mode = "full history" if init else "recent update"
    print(f"Fetching AT Lotto 6 aus 45 ({mode})...")

    new_draws = fetch_new_draws(init=init)

    if new_draws:
        print(f"  {len(new_draws)} new draw(s) found:")
        for draw in new_draws:
            print(f"    {draw.date}: {draw.n1},{draw.n2},{draw.n3},"
                  f"{draw.n4},{draw.n5},{draw.n6} ZZ:{draw.zusatzzahl}")
        write_draws(new_draws)

        if commit:
            dates = ", ".join(d.date for d in new_draws)
            message = f"Add AT Lotto 6 aus 45 results: {dates}"
            if git_commit(str(RESULTS_CSV), message):
                print(f"  Committed: {message}")
    else:
        print("  No new draws found.")

    return len(new_draws)


if __name__ == "__main__":
    try:
        sys.exit(0 if main() >= 0 else 1)
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        sys.exit(1)
