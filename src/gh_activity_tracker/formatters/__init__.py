"""Output formatters for activity data."""

import csv
import io
import json
from typing import Any


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
        commit_key = next((key for key in item if key.startswith("commits_")), "commits_30d")
        lines.append(f"  Commits:   {item.get(commit_key, 0)} ({commit_key.removeprefix('commits_')})")
        lines.append(f"  Language:  {item.get('language', 'N/A')}")
        lines.append(f"  Updated:   {item.get('last_updated', 'N/A')}")
        lines.append("")
    return "\n".join(lines)


def format_json(data: list[dict[str, Any]]) -> str:
    """Format activity data as JSON."""
    return json.dumps(data, indent=2)


def format_csv(data: list[dict[str, Any]]) -> str:
    """Format activity data as CSV."""
    if not data:
        return ""
    commit_key = next((key for key in data[0] if key.startswith("commits_")), "commits_30d")
    headers = ["repo", "stars", "forks", "open_issues", commit_key, "language", "last_updated"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    for item in data:
        writer.writerow(item)
    return output.getvalue()