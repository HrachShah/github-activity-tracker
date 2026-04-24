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

    def track_repo(self, repo: str, days: int = 30) -> dict[str, Any] | None:
        """Track activity for a single repository.

        Returns None if the repository cannot be found.
        """
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
        """Compare activity across multiple repositories.

        Args:
            repos: List of repository names in 'owner/repo' format.
            days: Number of days of history to track per repo.

        Returns:
            List of activity dicts, excluding any repos that returned no data.
        """
        return self.track_multiple(repos, days=days)

    def get_trending(self, language: str | None = None, days: int = 7, min_stars: int = 100) -> list[dict[str, Any]]:
        """Get trending repositories by star gain over the specified period."""
        query = f"stars:>{min_stars} created:>{days}d"
        if language:
            query += f" language:{language}"
        data = self.api.search_repos(query)
        return data if isinstance(data, list) else []