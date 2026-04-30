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

    def get_trending(self, language: str | None = None, days: int = 7, min_stars: int = 100) -> list[dict[str, Any]]:
        """Get trending repositories based on star activity within the given window.
        
        Uses the GitHub Search API to find repositories that gained stars
        during the specified period. Only repositories with at least `min_stars`
        total stars are included.
        
        Args:
            language: Optional programming language to filter by.
            days: Number of days to look back for star activity (default: 7).
            min_stars: Minimum total star count (default: 100).
            
        Returns:
            List of repository data dicts with stars, forks, and activity metrics.
        """
        params: dict[str, Any] = {
            "q": f"created:>{days}d",
            "sort": "stars",
            "order": "desc",
            "per_page": 30,
        }
        if language:
            params["q"] += f" language:{language}"
        
        search_results = self.api.get("/search/repositories", params=params)
        if not isinstance(search_results, dict) or "items" not in search_results:
            return []
        
        results = []
        for repo in search_results["items"][:10]:
            if repo.get("stargazers_count", 0) < min_stars:
                continue
            results.append({
                "repo": repo.get("full_name", ""),
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "open_issues": repo.get("open_issues_count", 0),
                "commits_30d": 0,
                "last_updated": repo.get("pushed_at"),
                "description": repo.get("description", ""),
                "language": repo.get("language", ""),
            })
        return results