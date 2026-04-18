#!/usr/bin/env python3
"""
Update all lottery result files and create a separate git commit per country.

Each country is fetched and committed independently — a failure in one does
not affect the other, and the git history stays cleanly separated by country.

This script is useful for local combined runs or full historical imports.
In CI, each country is handled by its own workflow which calls the individual
fetch scripts directly with the --commit flag.

Usage:
  python update_all.py           # regular update (current + previous year)
  python update_all.py --init    # full historical import for AT, DE, and EU
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import fetch_lotto_at_6aus45 as fetch_at
import fetch_lotto_de_6aus49 as fetch_de
import fetch_euromillions as fetch_eu
from git_utils import git_commit


def update_country(label: str, game: str, csv_file: str, json_file: str, new_draws: list) -> int:
    """Commit new draws for one country. Returns the number of draws committed."""
    if not new_draws:
        print(f"{label}: No new draws.")
        return 0

    dates = ", ".join(d.date for d in new_draws)
    message = f"Add {label} {game} results: {dates}"

    committed = git_commit([csv_file, json_file], message)
    if committed:
        print(f"{label}: Committed {len(new_draws)} new draw(s) — {dates}")
    else:
        print(f"{label}: File unchanged after write — nothing to commit.")

    return len(new_draws)


def main() -> int:
    init = "--init" in sys.argv
    total = 0

    # --- Austria ---
    try:
        at_new = fetch_at.fetch_new_draws(init=init)
        if at_new:
            fetch_at.write_csv(at_new)
            fetch_at.write_json(at_new)
        total += update_country("AT", "Lotto 6 aus 45", str(fetch_at.RESULTS_CSV), str(fetch_at.RESULTS_JSON), at_new)
    except Exception as exc:
        print(f"AT fetch failed: {exc}", file=sys.stderr)

    # --- Germany ---
    try:
        de_new = fetch_de.fetch_new_draws(init=init)
        if de_new:
            fetch_de.write_csv(de_new)
            fetch_de.write_json(de_new)
        total += update_country("DE", "Lotto 6 aus 49", str(fetch_de.RESULTS_CSV), str(fetch_de.RESULTS_JSON), de_new)
    except Exception as exc:
        print(f"DE fetch failed: {exc}", file=sys.stderr)

    # --- EuroMillions ---
    try:
        eu_new = fetch_eu.fetch_new_draws(init=init)
        if eu_new:
            fetch_eu.write_csv(eu_new)
            fetch_eu.write_json(eu_new)
        total += update_country("EU", "EuroMillions", str(fetch_eu.RESULTS_CSV), str(fetch_eu.RESULTS_JSON), eu_new)
    except Exception as exc:
        print(f"EU fetch failed: {exc}", file=sys.stderr)

    if total == 0:
        print("Nothing to commit.")

    return total


if __name__ == "__main__":
    sys.exit(0 if main() >= 0 else 1)
