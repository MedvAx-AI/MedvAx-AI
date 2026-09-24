"""Build profile activity SVGs from GitHub's contribution calendar."""

from collections import defaultdict
from datetime import date
from html import escape
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


LOGIN = "MedvAx-AI"
QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount color } }
      }
    }
  }
}
"""


def summarize_calendar(calendar):
    days = sorted(
        (day for week in calendar["weeks"] for day in week["contributionDays"]),
        key=lambda day: day["date"],
    )
    monthly = defaultdict(int)
    for day in days:
        monthly[day["date"][:7]] += day["contributionCount"]
    return {
        "total": calendar["totalContributions"],
        "active_days": sum(day["contributionCount"] > 0 for day in days),
        "monthly": dict(monthly),
        "days": days,
    }


def svg_open(width, height, title, description):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">'
        f'<title>{escape(title)}</title><desc>{escape(description)}</desc>'
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="16" fill="#0d1117" stroke="#30363d"/>'
        f'<rect x="26" y="83" width="{width - 52}" height="1" fill="#30363d"/>'
    )


def render_heatmap(calendar):
    summary = summarize_calendar(calendar)
    weeks = calendar["weeks"]
    width = max(830, 120 + len(weeks) * 13)
    height = 248
    last = summary["days"][-1]["date"] if summary["days"] else ""
    first = summary["days"][0]["date"] if summary["days"] else ""
    parts = [svg_open(width, height, "GitHub contribution calendar",
                      f'{summary["total"]} contributions on {summary["active_days"]} active days from {first} through {last}. Each square is one day.')]
    parts.append('<circle cx="33" cy="33" r="5" fill="#3fb950"/>')
    parts.append('<text x="48" y="39" font-family="Arial,sans-serif" font-size="20" font-weight="700" fill="#f0f6fc">A year on GitHub</text>')
    parts.append(f'<text x="27" y="63" font-family="Arial,sans-serif" font-size="12" fill="#8b949e">Daily contribution activity · through {escape(last)}</text>')
    parts.append(f'<text x="{width - 222}" y="37" font-family="Arial,sans-serif" font-size="21" font-weight="700" fill="#f0f6fc">{summary["total"]}</text>')
    parts.append(f'<text x="{width - 222}" y="57" font-family="Arial,sans-serif" font-size="10" fill="#8b949e">CONTRIBUTIONS</text>')
    parts.append(f'<text x="{width - 86}" y="37" font-family="Arial,sans-serif" font-size="21" font-weight="700" fill="#f0f6fc">{summary["active_days"]}</text>')
    parts.append(f'<text x="{width - 86}" y="57" font-family="Arial,sans-serif" font-size="10" fill="#8b949e">ACTIVE DAYS</text>')
    for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        parts.append(f'<text x="27" y="{129 + row * 13}" font-family="Arial,sans-serif" font-size="10" fill="#8b949e">{label}</text>')
    seen_months = set()
    for wi, week in enumerate(weeks):
        x = 81 + wi * 13
        for day in week["contributionDays"]:
            day_date = date.fromisoformat(day["date"])
            month = day_date.strftime("%Y-%m")
            if month not in seen_months:
                seen_months.add(month)
                if month != first[:7] or day_date.day <= 15:
                    parts.append(f'<text x="{x}" y="108" font-family="Arial,sans-serif" font-size="10" fill="#8b949e">{escape(day_date.strftime("%b"))}</text>')
            row = (day_date.weekday() + 1) % 7
            y = 121 + row * 13
            count = day["contributionCount"]
            color = contribution_color(count)
            parts.append(f'<rect x="{x}" y="{y}" width="10" height="10" rx="2" fill="{color}"><title>{day["date"]}: {count} contributions</title></rect>')
    parts.append('<text x="27" y="230" font-family="Arial,sans-serif" font-size="10" fill="#8b949e">Each square is one day</text>')
    parts.append(f'<text x="{width - 165}" y="230" font-family="Arial,sans-serif" font-size="10" fill="#8b949e">Less</text>')
    for level, count in enumerate((0, 1, 2, 4, 8)):
        parts.append(f'<rect x="{width - 137 + level * 14}" y="220" width="10" height="10" rx="2" fill="{contribution_color(count)}"/>')
    parts.append(f'<text x="{width - 58}" y="230" font-family="Arial,sans-serif" font-size="10" fill="#8b949e">More</text>')
    parts.append('</svg>')
    return "".join(parts)


def contribution_color(count):
    if count == 0:
        return "#161b22"
    if count == 1:
        return "#0e4429"
    if count <= 3:
        return "#006d32"
    if count <= 7:
        return "#26a641"
    return "#39d353"


def render_monthly(calendar):
    summary = summarize_calendar(calendar)
    last_date = date.fromisoformat(summary["days"][-1]["date"])
    last_month = last_date.year * 12 + last_date.month - 1
    months = []
    for offset in range(11, -1, -1):
        index = last_month - offset
        year, zero_month = divmod(index, 12)
        month = zero_month + 1
        key = f"{year:04d}-{month:02d}"
        months.append((key, summary["monthly"].get(key, 0)))
    maximum = max((count for _, count in months), default=0) or 1
    displayed_total = sum(count for _, count in months)
    width, height = 830, 274
    parts = [svg_open(width, height, "Monthly GitHub contributions",
                      f'{displayed_total} contributions across the 12 displayed months.')]
    parts.append('<circle cx="33" cy="33" r="5" fill="#3fb950"/>')
    parts.append('<text x="48" y="39" font-family="Arial,sans-serif" font-size="20" font-weight="700" fill="#f0f6fc">The monthly view</text>')
    parts.append('<text x="27" y="63" font-family="Arial,sans-serif" font-size="12" fill="#8b949e">Contributions across the last 12 months</text>')
    parts.append(f'<text x="704" y="37" font-family="Arial,sans-serif" font-size="21" font-weight="700" fill="#f0f6fc">{maximum}</text>')
    parts.append('<text x="704" y="57" font-family="Arial,sans-serif" font-size="10" fill="#8b949e">PEAK MONTH</text>')
    for y in (116, 171, 226):
        parts.append(f'<line x1="48" y1="{y}" x2="808" y2="{y}" stroke="#21262d"/>')
    for i, (key, count) in enumerate(months):
        x = 61 + i * 62
        bar_height = round(103 * count / maximum)
        y = 226 - bar_height
        parts.append(f'<rect x="{x}" y="{y}" width="36" height="{bar_height}" rx="4" fill="#3fb950"/>')
        if count:
            parts.append(f'<text x="{x + 18}" y="{max(113, y - 7)}" text-anchor="middle" font-family="Arial,sans-serif" font-size="11" font-weight="700" fill="#c9d1d9">{count}</text>')
        year, month = map(int, key.split("-"))
        label = date(year, month, 1).strftime("%b")
        parts.append(f'<text x="{x + 18}" y="250" text-anchor="middle" font-family="Arial,sans-serif" font-size="11" fill="#8b949e">{label}</text>')
        if month == 1:
            parts.append(f'<text x="{x + 18}" y="265" text-anchor="middle" font-family="Arial,sans-serif" font-size="10" fill="#8b949e">{year}</text>')
    parts.append('</svg>')
    return "".join(parts)


def fetch_calendar():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required to query GitHub GraphQL")
    payload = json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode("utf-8")
    request = Request(
        "https://api.github.com/graphql", data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": "profile-activity-graphs"},
    )
    with urlopen(request, timeout=30) as response:
        data = json.load(response)
    if data.get("errors"):
        raise RuntimeError(f"GitHub GraphQL returned errors: {data['errors']}")
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def main():
    calendar = fetch_calendar()
    assets = Path(__file__).resolve().parents[1] / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "github-contributions.svg").write_text(render_heatmap(calendar), encoding="utf-8")
    (assets / "github-monthly.svg").write_text(render_monthly(calendar), encoding="utf-8")
    print(f'Updated GitHub activity charts: {calendar["totalContributions"]} contributions')


if __name__ == "__main__":
    main()
