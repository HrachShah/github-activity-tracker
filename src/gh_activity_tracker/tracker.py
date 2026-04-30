"""Core activity tracking logic."""

from datetime import datetime, timedelta, timezone
from typing import Any

from .github_api import GitHubAPI


class ActivityTracker:
    """Track GitHub repository activity."""

    def __init__(self, token: str | None = None):
        self.api = GitHubAPI(token=token)

    @property
    def rate_limit_remaining(self) -> int | None:
        """Remaining API rate limit requests."""
        return self.api.rate_limit_remaining

    @property
    def rate_limit_reset(self) -> int | None:
        """Timestamp when rate limit resets."""
        return self.api.rate_limit_reset

    def track_repo(self, repo: str, days: int = 30) -> dict[str, Any]:
        """Track activity for a single repository."""
        return self.api.get_activity_summary(repo, days=days)

    def track_multiple(self, repos: list[str], days: int = 30) -> list[dict[str, Any]]:
        """Track activity for multiple repositories."""
        results = []
        for repo in repos:
            try:
                activity = self.track_repo(repo, days=days)
                if activity:
                    results.append(activity)
            except Exception as e:
                print(f"Error tracking {repo}: {e}")
                continue
        return results

    def compare_repos(self, repos: list[str], days: int = 30) -> list[dict[str, Any]]:
        """Compare activity across multiple repositories."""
        return self.track_multiple(repos, days=days)

    def get_trending(self, language: str | None = None, days: int = 7, min_stars: int = 100) -> list[dict[str, Any]]:
        """Get trending repositories within the given number of days.
        
        Args:
            language: Optional language filter (e.g. "python", "rust").
            days: Number of days to look back for newly created repos.
            min_stars: Minimum star count to include in results.
            
        Returns:
            List of trending repository dicts with name, stars, language, etc.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)
        date_str = since.strftime("%Y-%m-%d")
        
        query_parts = [f"created:>{date_str}", f"stars:>={min_stars}"]
        if language:
            query_parts.append(f"language:{language}")
        query = " ".join(query_parts)
        
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 10,
        }
        
        data = self.api.get("/search/repositories", params=params)
        if not isinstance(data, dict):
            return []
        
        items = data.get("items", [])
        return [
            {
                "repo": item.get("full_name", ""),
                "stars": item.get("stargazers_count", 0),
                "forks": item.get("forks_count", 0),
                "open_issues": item.get("open_issues_count", 0),
                "description": item.get("description", ""),
                "language": item.get("language", ""),
                "created_at": item.get("created_at", ""),
                "url": item.get("html_url", ""),
            }
            for item in items
        ]
