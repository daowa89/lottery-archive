"""Generate a static index.html showing the latest lottery draw results."""

import csv
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

LOTTERIES = [
    {
        "id": "at",
        "name": "Lotto 6 aus 45",
        "flag": "🇦🇹",
        "csv": REPO_ROOT / "at" / "lotto_6aus45" / "results.csv",
        "numbers": ["n1", "n2", "n3", "n4", "n5", "n6"],
        "bonus": [("Zusatzzahl", "zusatzzahl")],
        "bonus_style": "bonus-red",
    },
    {
        "id": "de",
        "name": "Lotto 6 aus 49",
        "flag": "🇩🇪",
        "csv": REPO_ROOT / "de" / "lotto_6aus49" / "results.csv",
        "numbers": ["n1", "n2", "n3", "n4", "n5", "n6"],
        "bonus": [("Superzahl", "superzahl")],
        "bonus_style": "bonus-red",
    },
    {
        "id": "eu",
        "name": "Euromillionen",
        "flag": "🇪🇺",
        "csv": REPO_ROOT / "eu" / "euromillions" / "results.csv",
        "numbers": ["n1", "n2", "n3", "n4", "n5"],
        "bonus": [("Lucky Star", "s1"), ("Lucky Star", "s2")],
        "bonus_style": "bonus-eu",
    },
]


def read_last_row(csv_path: Path) -> dict:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        last = None
        for row in reader:
            last = row
    return last


def format_date(iso_date: str) -> str:
    d = datetime.strptime(iso_date, "%Y-%m-%d").date()
    return d.strftime("%d.%m.%Y")


def render_lottery_card(lottery: dict, row: dict) -> str:
    main_balls = "".join(
        f'<span class="ball main">{row[col]}</span>'
        for col in lottery["numbers"]
    )

    bonus_balls = ""
    for label, col in lottery["bonus"]:
        val = row.get(col, "").strip()
        if val:
            bonus_balls += (
                f'<span class="ball {lottery["bonus_style"]}" title="{label}">{val}</span>'
            )

    draw_date = format_date(row["date"])

    return f"""
    <article class="card" id="{lottery['id']}">
      <header>
        <span class="flag">{lottery['flag']}</span>
        <h2>{lottery['name']}</h2>
      </header>
      <p class="draw-date">Ziehung vom {draw_date}</p>
      <div class="balls">
        {main_balls}
        {"<span class='separator'>+</span>" + bonus_balls if bonus_balls else ""}
      </div>
    </article>"""


def generate_html(cards: list[str], generated_at: str) -> str:
    cards_html = "\n".join(cards)
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Lottery Archive – Letzte Ziehungen</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: system-ui, -apple-system, sans-serif;
      background: #0f172a;
      color: #e2e8f0;
      min-height: 100vh;
      padding: 2rem 1rem;
    }}

    header.page-header {{
      text-align: center;
      margin-bottom: 2.5rem;
    }}

    header.page-header h1 {{
      font-size: 2rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: #f8fafc;
    }}

    header.page-header p {{
      margin-top: 0.5rem;
      color: #94a3b8;
      font-size: 0.9rem;
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 1.5rem;
      max-width: 1100px;
      margin: 0 auto;
    }}

    .card {{
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 1rem;
      padding: 1.5rem;
    }}

    .card header {{
      display: flex;
      align-items: center;
      gap: 0.6rem;
      margin-bottom: 0.75rem;
    }}

    .flag {{ font-size: 1.6rem; line-height: 1; }}

    .card h2 {{
      font-size: 1.1rem;
      font-weight: 600;
      color: #f1f5f9;
    }}

    .draw-date {{
      font-size: 0.82rem;
      color: #64748b;
      margin-bottom: 1.1rem;
    }}

    .balls {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 0.5rem;
    }}

    .ball {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 2.6rem;
      height: 2.6rem;
      border-radius: 50%;
      font-size: 0.95rem;
      font-weight: 700;
    }}

    .ball.main {{
      background: #2563eb;
      color: #fff;
    }}

    .ball.bonus-red {{
      background: #dc2626;
      color: #fff;
    }}

    .ball.bonus-eu {{
      background: #f59e0b;
      color: #1e293b;
    }}

    .separator {{
      color: #475569;
      font-weight: 700;
      font-size: 1.2rem;
    }}

    footer {{
      text-align: center;
      margin-top: 3rem;
      color: #475569;
      font-size: 0.8rem;
    }}

    footer a {{
      color: #60a5fa;
      text-decoration: none;
    }}
  </style>
</head>
<body>
  <header class="page-header">
    <h1>Lottery Archive</h1>
    <p>Letzte offizielle Ziehungsergebnisse</p>
  </header>

  <main class="grid">
    {cards_html}
  </main>

  <footer>
    <p>Aktualisiert: {generated_at} &nbsp;·&nbsp;
       <a href="https://github.com/daowa89/lottery-archive" target="_blank" rel="noopener">GitHub</a>
    </p>
  </footer>
</body>
</html>
"""


def main():
    cards = []
    for lottery in LOTTERIES:
        row = read_last_row(lottery["csv"])
        if row is None:
            print(f"WARNING: No data found in {lottery['csv']}")
            continue
        cards.append(render_lottery_card(lottery, row))

    generated_at = datetime.now(UTC).strftime("%d.%m.%Y %H:%M UTC")
    html = generate_html(cards, generated_at)

    out_dir = REPO_ROOT / "public"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    print(f"Generated: {out_dir / 'index.html'}")


if __name__ == "__main__":
    main()
