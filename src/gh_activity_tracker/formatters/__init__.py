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
    commit_keys = {
        key
        for item in data
        for key in item
        if key.startswith("commits_")
    }
    if len(commit_keys) > 1:
        raise ValueError("CSV data must use one commit history window")
    commit_key = next(iter(commit_keys), "commits_30d")
    headers = ["repo", "stars", "forks", "open_issues", commit_key, "language", "last_updated"]
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(headers)
    for item in data:
        writer.writerow([
            item.get("repo", ""),
            item.get("stars", 0),
            item.get("forks", 0),
            item.get("open_issues", 0),
            item.get(commit_key, 0),
            item.get("language", ""),
            item.get("last_updated", ""),
        ])
    return output.getvalue().rstrip("\n")