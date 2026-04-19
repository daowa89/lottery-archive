"""Generate a static index.html showing all lottery draw results sorted newest first."""

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


def read_all_rows(csv_path: Path) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return sorted(rows, key=lambda r: r["date"], reverse=True)


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


def render_lottery_section(lottery: dict, rows: list[dict]) -> str:
    if not rows:
        return ""

    num_th = "".join(f"<th>N{i + 1}</th>" for i in range(len(lottery["numbers"])))
    bonus_th = "".join(f"<th>{label}</th>" for label, _ in lottery["bonus"])

    tbody_rows = []
    for row in rows:
        tds = f'<td class="td-date">{format_date(row["date"])}</td>'
        tds += "".join(
            f'<td><span class="ball main">{row[col]}</span></td>'
            for col in lottery["numbers"]
        )
        for label, col in lottery["bonus"]:
            val = row.get(col, "").strip()
            if val:
                tds += f'<td><span class="ball {lottery["bonus_style"]}" title="{label}">{val}</span></td>'
            else:
                tds += "<td>–</td>"
        tbody_rows.append(f"<tr>{tds}</tr>")

    tbody_html = "\n".join(tbody_rows)

    return f"""
    <section class="lottery-section" id="{lottery['id']}">
      <h2 class="lottery-title">
        <span class="flag">{lottery['flag']}</span>
        {lottery['name']}
      </h2>
      <div class="table-wrapper">
        <table class="draws-table">
          <thead><tr><th>Datum</th>{num_th}{bonus_th}</tr></thead>
          <tbody>
            {tbody_html}
          </tbody>
        </table>
      </div>
    </section>"""


def generate_html(sections: list[str], generated_at: str) -> str:
    sections_html = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Lottery Archive – Ziehungsergebnisse</title>
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

    .sections {{
      display: flex;
      flex-direction: column;
      gap: 3rem;
      max-width: 1100px;
      margin: 0 auto;
    }}

    .lottery-section {{
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 1rem;
      padding: 1.5rem;
    }}

    .lottery-title {{
      display: flex;
      align-items: center;
      gap: 0.6rem;
      font-size: 1.2rem;
      font-weight: 600;
      color: #f1f5f9;
      margin-bottom: 1.25rem;
    }}

    .flag {{ font-size: 1.6rem; line-height: 1; }}

    .table-wrapper {{
      max-height: 400px;
      overflow-y: auto;
      border-radius: 0.5rem;
    }}

    .draws-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }}

    .draws-table thead th {{
      position: sticky;
      top: 0;
      background: #0f172a;
      color: #94a3b8;
      font-weight: 600;
      text-align: left;
      padding: 0.5rem 0.75rem;
      border-bottom: 1px solid #334155;
      white-space: nowrap;
    }}

    .draws-table tbody tr {{
      border-bottom: 1px solid #263348;
    }}

    .draws-table tbody tr:hover {{
      background: #263348;
    }}

    .draws-table td {{
      padding: 0.4rem 0.75rem;
      vertical-align: middle;
      white-space: nowrap;
    }}

    .td-date {{
      color: #94a3b8;
      font-size: 0.82rem;
      min-width: 6rem;
    }}

    .ball {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 2.2rem;
      height: 2.2rem;
      border-radius: 50%;
      font-size: 0.85rem;
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
    <p>Offizielle Ziehungsergebnisse – neueste zuerst</p>
  </header>

  <main class="sections">
    {sections_html}
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
    sections = []
    for lottery in LOTTERIES:
        rows = read_all_rows(lottery["csv"])
        if not rows:
            print(f"WARNING: No data found in {lottery['csv']}")
            continue
        sections.append(render_lottery_section(lottery, rows))

    generated_at = datetime.now(UTC).strftime("%d.%m.%Y %H:%M UTC")
    html = generate_html(sections, generated_at)

    out_dir = REPO_ROOT / "public"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    print(f"Generated: {out_dir / 'index.html'}")


if __name__ == "__main__":
    main()
