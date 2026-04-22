"""Output formatters for activity data."""

from typing import Any

import json


def format_text(data: list[dict[str, Any]]) -> str:
    """Format activity data as human-readable text."""
    if not data:
        return "No data available."
    lines = []
    for item in data:
        lines.append(f"Repository: {item.get('repo', 'N/A')}")
        stars = item.get('stars', item.get('stargazers_count', 0))
        lines.append(f"  Stars:     {stars}")
        forks = item.get('forks', item.get('forks_count', 0))
        lines.append(f"  Forks:     {forks}")
        lines.append(f"  Issues:    {item.get('open_issues', 0)}")
        lines.append(f"  Commits:   {item.get('commits_30d', 0)}")
        lines.append(f"  Language:  {item.get('language', 'N/A')}")
        if item.get('description'):
            lines.append(f"  Description: {item.get('description', '')[:80]}")
        if item.get('url'):
            lines.append(f"  URL:        {item.get('url')}")
        updated = item.get('last_updated') or item.get('created_at', 'N/A')
        lines.append(f"  Updated:   {updated}")
        lines.append("")
    return "\n".join(lines)


def format_json(data: list[dict[str, Any]]) -> str:
    """Format activity data as JSON."""
    return json.dumps(data, indent=2)


def format_csv(data: list[dict[str, Any]]) -> str:
    """Format activity data as CSV."""
    if not data:
        return ""
    headers = ["repo", "stars", "forks", "open_issues", "commits_30d", "language", "last_updated"]
    lines = [",".join(headers)]
    for item in data:
        row = [
            str(item.get("repo", "")),
            str(item.get("stars", item.get("stargazers_count", 0))),
            str(item.get("forks", item.get("forks_count", 0))),
            str(item.get("open_issues", "")),
            str(item.get("commits_30d", "")),
            str(item.get("language", "")),
            str(item.get("last_updated", item.get("created_at", ""))),
        ]
        lines.append(",".join(row))
    return "\n".join(lines)