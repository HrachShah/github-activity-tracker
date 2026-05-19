"""Output formatters for activity data."""

from typing import Any

import json
from datetime import datetime


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
    """Format activity data as JSON.
    
    datetime values are serialized as ISO 8601 strings since the raw
    datetime objects are not JSON-serializable.
    """
    def default_serializer(o: Any) -> str:
        if isinstance(o, datetime):
            return o.isoformat()
        raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")
    return json.dumps(data, indent=2, default=default_serializer)


def format_csv(data: list[dict[str, Any]]) -> str:
    """Format activity data as CSV."""
    if not data:
        return ""
    headers = ["repo", "stars", "forks", "open_issues", "commits_30d", "language", "last_updated"]
    lines = [",".join(headers)]
    for item in data:
        row = [
            str(item.get("repo", "")),
            str(item.get("stars", 0)),
            str(item.get("forks", 0)),
            str(item.get("open_issues", 0)),
            str(item.get("commits_30d", 0)),
            str(item.get("language", "")),
            str(item.get("last_updated", "")),
        ]
        lines.append(",".join(row))
    return "\n".join(lines)