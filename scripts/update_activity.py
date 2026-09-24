"""Build profile activity SVGs from GitHub's contribution calendar."""

from collections import defaultdict
from datetime import date
from html import escape
import json
import os
from pathlib import Path
import re
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
    return {"total": calendar["totalContributions"], "monthly": dict(monthly), "days": days}


def svg_open(width, height, title, description):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">'
        f'<title>{escape(title)}</title><desc>{escape(description)}</desc>'
        f'<rect width="{width}" height="{height}" rx="14" fill="#ffffff" stroke="#d0d7de"/>'
    )


def render_heatmap(calendar):
    summary = summarize_calendar(calendar)
    weeks = calendar["weeks"]
    width = max(830, 86 + len(weeks) * 13)
    height = 196
    last = summary["days"][-1]["date"] if summary["days"] else ""
    parts = [svg_open(width, height, "GitHub contribution calendar",
                      f'{summary["total"]} contributions through {last}. Each square is one day.')]
    parts.append('<text x="24" y="31" font-family="Arial,sans-serif" font-size="17" font-weight="700" fill="#24292f">GitHub activity</text>')
    parts.append(f'<text x="24" y="51" font-family="Arial,sans-serif" font-size="12" fill="#57606a">{summary["total"]} contributions in the last year · through {escape(last)}</text>')
    for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        parts.append(f'<text x="24" y="{90 + row * 13}" font-family="Arial,sans-serif" font-size="10" fill="#57606a">{label}</text>')
    seen_months = set()
    for wi, week in enumerate(weeks):
        x = 64 + wi * 13
        for day in week["contributionDays"]:
            day_date = date.fromisoformat(day["date"])
            month = day_date.strftime("%Y-%m")
            if month not in seen_months:
                seen_months.add(month)
                parts.append(f'<text x="{x}" y="69" font-family="Arial,sans-serif" font-size="10" fill="#57606a">{escape(day_date.strftime("%b"))}</text>')
            row = (day_date.weekday() + 1) % 7
            y = 91 + row * 13
            color = day.get("color", "#ebedf0")
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
                color = "#ebedf0"
            parts.append(f'<rect x="{x}" y="{y}" width="10" height="10" rx="2" fill="{color}"><title>{day["date"]}: {day["contributionCount"]} contributions</title></rect>')
    parts.append('</svg>')
    return "".join(parts)


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
    width, height = 830, 256
    parts = [svg_open(width, height, "Monthly GitHub contributions",
                      f'{displayed_total} contributions across the 12 displayed months.')]
    parts.append('<text x="24" y="31" font-family="Arial,sans-serif" font-size="17" font-weight="700" fill="#24292f">Contributions by month</text>')
    parts.append('<text x="24" y="51" font-family="Arial,sans-serif" font-size="12" fill="#57606a">GitHub contribution calendar · last 12 months</text>')
    parts.append('<line x1="49" y1="208" x2="809" y2="208" stroke="#d0d7de"/>')
    for i, (key, count) in enumerate(months):
        x = 58 + i * 62
        bar_height = round(128 * count / maximum)
        y = 208 - bar_height
        parts.append(f'<rect x="{x}" y="{y}" width="33" height="{bar_height}" rx="3" fill="#2da44e"/>')
        if count:
            parts.append(f'<text x="{x + 16}" y="{max(75, y - 5)}" text-anchor="middle" font-family="Arial,sans-serif" font-size="11" fill="#24292f">{count}</text>')
        year, month = map(int, key.split("-"))
        label = date(year, month, 1).strftime("%b")
        parts.append(f'<text x="{x + 16}" y="226" text-anchor="middle" font-family="Arial,sans-serif" font-size="11" fill="#57606a">{label}</text>')
        if month == 1:
            parts.append(f'<text x="{x + 16}" y="242" text-anchor="middle" font-family="Arial,sans-serif" font-size="10" fill="#57606a">{year}</text>')
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
