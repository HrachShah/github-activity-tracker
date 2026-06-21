"""Output formatters for activity data."""

from typing import Any

import csv
import io
import json


def format_text(data: list[dict[str, Any]]) -> str:
    """Format activity data as human-readable text."""
    if not data:
        return "No data available."
    lines = []
    for item in data:
        lines.append(f"Repository: {item.get('repo', 'N/A')}")
        lines.append(f"  Stars:     {item.get('stars', 0)}")
        lines.append(f"  Forks:     {item.get('forks', 0)}")
        lines.append(f"  Issues:    {item.get('open_issues', 0)}")
        lines.append(f"  Commits:   {item.get('commits_30d', 0)}")
        lines.append(f"  Language:  {item.get('language', 'N/A')}")
        lines.append(f"  Updated:   {item.get('last_updated', 'N/A')}")
        lines.append("")
    return "\n".join(lines)


def format_json(data: list[dict[str, Any]]) -> str:
    """Format activity data as JSON."""
    return json.dumps(data, indent=2)


def format_csv(data: list[dict[str, Any]]) -> str:
    """Format activity data as CSV.

    Uses :class:`csv.writer` so values that contain commas, double quotes,
    or newlines (a repo ``description`` from GitHub can legitimately have
    any of these) are RFC 4180 quoted instead of producing a row that
    csv.reader would split into the wrong number of fields. Also includes
    the ``description`` column that :meth:`ActivityTracker.track_repo`
    returns but the previous hand-rolled ``\",\".join(row)`` loop silently
    dropped.
    """
    if not data:
        return ""
    headers = [
        "repo", "stars", "forks", "open_issues",
        "commits_30d", "language", "last_updated", "description",
    ]
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(headers)
    for item in data:
        writer.writerow([
            item.get("repo", ""),
            item.get("stars", 0),
            item.get("forks", 0),
            item.get("open_issues", 0),
            item.get("commits_30d", 0),
            item.get("language", "") or "",
            item.get("last_updated", "") or "",
            item.get("description", "") or "",
        ])
    return buffer.getvalue().rstrip("\n")