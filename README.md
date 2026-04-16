# LottoData

[![Unit Tests](https://github.com/daowa89/lottery-archive/actions/workflows/unit_tests.yml/badge.svg)](https://github.com/daowa89/lottery-archive/actions/workflows/unit_tests.yml)
[![Update AT](https://github.com/daowa89/lottery-archive/actions/workflows/update_at.yml/badge.svg)](https://github.com/daowa89/lottery-archive/actions/workflows/update_at.yml)
[![Update DE](https://github.com/daowa89/lottery-archive/actions/workflows/update_de.yml/badge.svg)](https://github.com/daowa89/lottery-archive/actions/workflows/update_de.yml)
[![Update EU](https://github.com/daowa89/lottery-archive/actions/workflows/update_eu.yml/badge.svg)](https://github.com/daowa89/lottery-archive/actions/workflows/update_eu.yml)
[![Deploy Pages](https://github.com/daowa89/lottery-archive/actions/workflows/deploy_pages.yml/badge.svg)](https://github.com/daowa89/lottery-archive/actions/workflows/deploy_pages.yml)

LottoData is an automated archive of lottery draw results. GitHub Actions fetch new results on every draw day and commit them to this repository as plain CSV and JSON files, so the data is always accessible without scraping or signing up for any service.

The latest draw results are published as a **[GitHub Page](https://daowa89.github.io/lottery-archive/)**.

Three lotteries are covered:

- **Austria** — Lotto 6 aus 45 (draws on Wednesday and Sunday, results from 1986)
- **Germany** — Lotto 6 aus 49 (draws on Wednesday and Saturday, results from 1955)
- **Europe** — Euromillionen (draws on Tuesday and Friday, results from 2004)

## Data

Each game is provided as both a CSV and a JSON file:

| Game | CSV | JSON | Source |
|------|-----|------|--------|
| AT Lotto 6 aus 45 | [`at/lotto_6aus45/results.csv`](at/lotto_6aus45/results.csv) | [`at/lotto_6aus45/results.json`](at/lotto_6aus45/results.json) | [win2day.at](https://www.win2day.at/lotterie/lotto/lotto-statistik-zahlen-ergebnisse-download) |
| DE Lotto 6 aus 49 | [`de/lotto_6aus49/results.csv`](de/lotto_6aus49/results.csv) | [`de/lotto_6aus49/results.json`](de/lotto_6aus49/results.json) | [lottozahlenonline.de](https://www.lottozahlenonline.de/statistik/beide-spieltage/lottozahlen-archiv.php) |
| EU EuroMillions | [`eu/euromillions/results.csv`](eu/euromillions/results.csv) | [`eu/euromillions/results.json`](eu/euromillions/results.json) | [win2day.at](https://www.win2day.at/lotterie/euromillionen/euromillionen-statistik-zahlen-ergebnisse-download) |

### AT Lotto 6 aus 45

CSV:
```
date,n1,n2,n3,n4,n5,n6,zusatzzahl
2025-04-09,3,12,18,27,33,41,5
```

JSON:
```json
[
  { "date": "2025-04-09", "numbers": [3, 12, 18, 27, 33, 41], "zusatzzahl": 5 }
]
```

### DE Lotto 6 aus 49

CSV:
```
date,n1,n2,n3,n4,n5,n6,superzahl
2025-04-12,7,14,19,28,35,44,3
```

JSON:
```json
[
  { "date": "2025-04-12", "numbers": [7, 14, 19, 28, 35, 44], "superzahl": 3 }
]
```

The `superzahl` is a digit from 0–9 drawn separately. Draws before 1992-01-01 have an empty `superzahl` field in CSV and `null` in JSON (the Superzahl was not yet in use).

### EU EuroMillions

CSV:
```
date,n1,n2,n3,n4,n5,s1,s2
2025-04-11,7,14,25,38,50,3,9
```

JSON:
```json
[
  { "date": "2025-04-11", "numbers": [7, 14, 25, 38, 50], "stars": [3, 9] }
]
```

`numbers` contains the five main numbers (1–50). `stars` contains the two Lucky Star numbers (1–12).

### Accessing the Data

Fetch the raw files directly from GitHub:

**CSV:**
```
https://raw.githubusercontent.com/daowa89/lottery-archive/main/at/lotto_6aus45/results.csv
https://raw.githubusercontent.com/daowa89/lottery-archive/main/de/lotto_6aus49/results.csv
https://raw.githubusercontent.com/daowa89/lottery-archive/main/eu/euromillions/results.csv
```

**JSON:**
```
https://raw.githubusercontent.com/daowa89/lottery-archive/main/at/lotto_6aus45/results.json
https://raw.githubusercontent.com/daowa89/lottery-archive/main/de/lotto_6aus49/results.json
https://raw.githubusercontent.com/daowa89/lottery-archive/main/eu/euromillions/results.json
```

Load the CSV into a pandas DataFrame:

```python
import pandas as pd

BASE = "https://raw.githubusercontent.com/daowa89/lottery-archive/main"

at = pd.read_csv(f"{BASE}/at/lotto_6aus45/results.csv", parse_dates=["date"])
de = pd.read_csv(f"{BASE}/de/lotto_6aus49/results.csv", parse_dates=["date"])
eu = pd.read_csv(f"{BASE}/eu/euromillions/results.csv", parse_dates=["date"])

# Most recent draw
print(at.iloc[-1])
```

Or fetch the JSON directly:

```python
import urllib.request, json

BASE = "https://raw.githubusercontent.com/daowa89/lottery-archive/main"

with urllib.request.urlopen(f"{BASE}/at/lotto_6aus45/results.json") as r:
    draws = json.load(r)

# Most recent draw
print(draws[-1])
```

## Automation

Three separate [GitHub Actions workflows](.github/workflows/) run automatically on draw days:

| Workflow | Draw days | Time (UTC) | Time (CET / CEST) |
|----------|-----------|------------|-------------------|
| [`update_at.yml`](.github/workflows/update_at.yml) | Wednesday + Sunday | 20:00 | 21:00 / 22:00 |
| [`update_de.yml`](.github/workflows/update_de.yml) | Wednesday + Saturday | 20:00 | 21:00 / 22:00 |
| [`update_eu.yml`](.github/workflows/update_eu.yml) | Tuesday + Friday | 22:00 | 23:00 / 00:00 |

Each workflow fetches new results, creates a dedicated git commit if new data is found, runs an integrity check, and pushes to `main`. All workflows can also be triggered manually from the **Actions** tab.

## Development

### Requirements

Python 3.10 or newer is required (3.12 recommended).

### Local Usage

```bash
python -m venv .venv
source .venv/bin/activate
pip install .

# Fetch current + previous year for all games
python scripts/update_all.py

# Fetch a single game
python scripts/fetch_lotto_at_6aus45.py
python scripts/fetch_lotto_de_6aus49.py
python scripts/fetch_euromillions.py

# Run the data integrity check
python scripts/check_integrity.py
```

All individual fetch scripts accept the following flags:

| Flag | Description |
|------|-------------|
| _(none)_ | Fetch current and previous year only |
| `--init` | Full historical import (AT from 1986, DE from 1955, EU from 2004) |
| `--commit` | Create a git commit if new data was found |
| `--init --commit` | Full historical import and commit the result |

`update_all.py` supports `--init` to run the full import for all three games at once.

`check_integrity.py` accepts the following flags:

| Flag | Description |
|------|-------------|
| _(none)_ | Check all three games |
| `--country at\|de\|eu` | Check a single game only |
| `--skip-stale` | Skip the staleness check (used by CI when no new draw was committed) |

### Initial Historical Import

To populate the CSV files with all available historical data, trigger the respective workflow manually with **init = true**, or run locally:

```bash
# All games at once
python scripts/update_all.py --init

# Individual games
python scripts/fetch_lotto_at_6aus45.py --init
python scripts/fetch_lotto_de_6aus49.py --init
python scripts/fetch_euromillions.py --init
```

This imports AT results from 1986, DE results from 1955, and EU EuroMillions results from 2004.

### Running Tests

```bash
python3 -m unittest discover -s tests -v
```

No additional setup required — the tests use only the Python standard library and the packages listed in `pyproject.toml`.

### Scripts

| Script | Purpose |
|--------|---------|
| [`scripts/fetch_lotto_at_6aus45.py`](scripts/fetch_lotto_at_6aus45.py) | Downloads and parses AT lottery CSVs from win2day.at |
| [`scripts/fetch_lotto_de_6aus49.py`](scripts/fetch_lotto_de_6aus49.py) | Scrapes draw results from lottozahlenonline.de |
| [`scripts/fetch_euromillions.py`](scripts/fetch_euromillions.py) | Downloads and parses EuroMillions CSVs from win2day.at |
| [`scripts/update_all.py`](scripts/update_all.py) | Orchestrates all three fetchers for combined local runs |
| [`scripts/check_integrity.py`](scripts/check_integrity.py) | Validates CSV files for duplicates, number ranges, sort order, and stale data |
| [`scripts/git_utils.py`](scripts/git_utils.py) | Shared git commit helper used by all update scripts |
| [`scripts/generate_page.py`](scripts/generate_page.py) | Generates the static `public/index.html` for GitHub Pages |

## GitHub Pages

The latest draw results are available at **[https://daowa89.github.io/lottery-archive/](https://daowa89.github.io/lottery-archive/)**.

The page is generated automatically by [`scripts/generate_page.py`](scripts/generate_page.py) and deployed via the [`deploy_pages.yml`](.github/workflows/deploy_pages.yml) workflow whenever a results CSV is updated on `main`.

To generate the page locally:

```bash
python scripts/generate_page.py
# Output: public/index.html
```

## License

The **scripts** in this repository are licensed under the [MIT License](LICENSE).

The **data** (CSV files) is sourced from third parties and remains subject to their respective terms of use:

- Austria / EuroMillions: [Österreichische Lotterien GmbH](https://www.win2day.at) via win2day.at
- Germany: [lottozahlenonline.de](https://www.lottozahlenonline.de)

This repository is intended for personal, non-commercial use only. The data is reproduced here solely as an automated mirror for convenience.
