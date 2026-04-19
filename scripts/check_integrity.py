#!/usr/bin/env python3
"""
Check data integrity of all lottery result CSV files.

Verifies for each CSV:
  - No duplicate dates
  - All numbers within the valid range for the game
  - Rows sorted chronologically
  - Data is not stale (last draw is not older than max_stale_days)

Usage:
  python check_integrity.py              # check all countries
  python check_integrity.py --country at # check Austria only
  python check_integrity.py --country de # check Germany only
  python check_integrity.py --country eu # check EuroMillions only

Exit code 0: all checks passed
Exit code 1: one or more checks failed
"""

import csv
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

AT_CSV = Path(__file__).parent.parent / "at" / "lotto_6aus45" / "results.csv"
DE_CSV = Path(__file__).parent.parent / "de" / "lotto_6aus49" / "results.csv"
EU_CSV = Path(__file__).parent.parent / "eu" / "euromillions" / "results.csv"


@dataclass
class GameRules:
    label: str
    csv_path: Path
    number_min: int
    number_max: int
    num_count: int              # count of main numbers (6 for Lotto, 5 for EuroMillions)
    extra_fields: list[str]     # column names for bonus numbers
    extra_min: int
    extra_max: int
    max_stale_days: int = 7     # alert if last draw is older than this many days


GAMES = [
    GameRules(
        label="AT Lotto 6 aus 45",
        csv_path=AT_CSV,
        number_min=1, number_max=45,
        num_count=6,
        extra_fields=["zusatzzahl"], extra_min=1, extra_max=45,
        max_stale_days=7,   # draws Wed + Sun, max gap 4 days
    ),
    GameRules(
        label="DE Lotto 6 aus 49",
        csv_path=DE_CSV,
        number_min=1, number_max=49,
        num_count=6,
        extra_fields=["superzahl"], extra_min=0, extra_max=9,
        max_stale_days=7,   # draws Wed + Sat, max gap 4 days
    ),
    GameRules(
        label="EU EuroMillions",
        csv_path=EU_CSV,
        number_min=1, number_max=50,
        num_count=5,
        extra_fields=["s1", "s2"], extra_min=1, extra_max=12,
        max_stale_days=7,   # draws Tue + Fri, max gap 4 days
    ),
]


def check_csv(rules: GameRules,
              reference_date: date | None = None,
              skip_stale: bool = False) -> tuple[list[str], int]:
    """
    Run all integrity checks on a single CSV file.

    Args:
        rules:          Game-specific validation rules.
        reference_date: Date to use for the stale check. Defaults to today.
                        Inject a fixed date in tests to get deterministic results.
        skip_stale:     When True, skip the stale-data check. Used by workflows
                        when no new data was committed (avoids false positives
                        between two draw days).

    Returns (errors, row_count). errors is empty when all checks passed.
    row_count is 0 when the file is missing or empty.
    """
    errors: list[str] = []
    today = reference_date or date.today()

    if not rules.csv_path.exists():
        return [f"File not found: {rules.csv_path}"], 0

    with open(rules.csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        errors.append("File is empty (header only).")
        return errors, 0

    dates: list[date] = []
    seen_dates: dict[str, int] = {}

    for i, row in enumerate(rows, start=2):  # row 1 is header
        raw_date = row.get("date", "").strip()

        # --- Date parse ---
        try:
            d = date.fromisoformat(raw_date)
            dates.append(d)
        except ValueError:
            errors.append(f"Row {i}: invalid date '{raw_date}'")
            continue

        # --- Duplicate date ---
        if raw_date in seen_dates:
            errors.append(
                f"Row {i}: duplicate date {raw_date} "
                f"(first seen in row {seen_dates[raw_date]})"
            )
        else:
            seen_dates[raw_date] = i

        # --- Parse main numbers ---
        try:
            numbers = [int(row[f"n{j}"]) for j in range(1, rules.num_count + 1)]
        except (KeyError, ValueError) as e:
            errors.append(f"Row {i} ({raw_date}): could not parse numbers — {e}")
            continue

        # --- Parse extra fields (bonus numbers) ---
        extras: list[tuple[str, int | None]] = []
        parse_failed = False
        for field_name in rules.extra_fields:
            extra_str = row.get(field_name, "").strip()
            try:
                extra: int | None = int(extra_str) if extra_str else None
            except ValueError as e:
                errors.append(
                    f"Row {i} ({raw_date}): could not parse {field_name} — {e}"
                )
                parse_failed = True
                break
            extras.append((field_name, extra))

        if parse_failed:
            continue

        # --- Duplicate numbers within draw ---
        if len(set(numbers)) != rules.num_count:
            errors.append(f"Row {i} ({raw_date}): duplicate numbers {numbers}")

        # --- Number range ---
        out_of_range = [n for n in numbers
                        if not (rules.number_min <= n <= rules.number_max)]
        if out_of_range:
            errors.append(
                f"Row {i} ({raw_date}): numbers out of range "
                f"{rules.number_min}-{rules.number_max}: {out_of_range}"
            )

        # --- Extra field ranges (skipped when field is empty) ---
        for field_name, extra in extras:
            if extra is not None and not (rules.extra_min <= extra <= rules.extra_max):
                errors.append(
                    f"Row {i} ({raw_date}): {field_name} {extra} "
                    f"out of range {rules.extra_min}-{rules.extra_max}"
                )

        # --- Duplicate extra numbers (e.g. two star numbers must differ) ---
        if len(rules.extra_fields) > 1:
            valid_extras = [v for _, v in extras if v is not None]
            if len(valid_extras) > 1 and len(set(valid_extras)) != len(valid_extras):
                errors.append(
                    f"Row {i} ({raw_date}): duplicate extra numbers {valid_extras}"
                )

    # --- Chronological order ---
    for i in range(1, len(dates)):
        if dates[i] < dates[i - 1]:
            errors.append(
                f"Row {i + 2}: date {dates[i]} is before previous {dates[i - 1]} "
                "(file is not sorted chronologically)"
            )

    # --- Stale data check ---
    if not skip_stale and dates:
        last_date = max(dates)
        days_since = (today - last_date).days
        if days_since > rules.max_stale_days:
            errors.append(
                f"Data is stale: last draw was {last_date} "
                f"({days_since} day(s) ago, threshold is {rules.max_stale_days} days). "
                "A draw may have been missed."
            )

    return errors, len(rows)


def main() -> int:
    args = sys.argv[1:]
    country_filter: str | None = None
    skip_stale = "--skip-stale" in args

    if "--country" in args:
        idx = args.index("--country")
        if idx + 1 < len(args):
            country_filter = args[idx + 1].lower()

    games = GAMES
    if country_filter:
        games = [g for g in GAMES if country_filter in g.label.lower()]
        if not games:
            print(
                f"Unknown country filter '{country_filter}'. Use 'at', 'de', or 'eu'.",
                file=sys.stderr,
            )
            return 1

    if skip_stale:
        print("Note: stale-data check skipped (no new draws committed).")

    all_passed = True

    for rules in games:
        print(f"Checking {rules.label} ({rules.csv_path.name})...")
        errors, count = check_csv(rules, skip_stale=skip_stale)

        if errors:
            all_passed = False
            print(f"  FAILED — {len(errors)} issue(s):")
            for err in errors:
                print(f"    - {err}")
        else:
            print(f"  OK — {count} draw(s), all checks passed.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
