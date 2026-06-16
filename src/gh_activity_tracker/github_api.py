"""GitHub API interactions with rate-limit handling."""

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

DEFAULT_API_URL = "https://api.github.com"


class GitHubAPI:
    """GitHub API client with rate-limit awareness."""

    def __init__(self, token: str | None = None, max_retries: int = 3):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.max_retries = max_retries
        self.session = requests.Session()
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"
        self.session.headers["Accept"] = "application/vnd.github+json"
        self.rate_limit_remaining = None
        self.rate_limit_reset = None

    def _handle_rate_limit(self) -> None:
        """Wait if rate limited."""
        if self.rate_limit_remaining == 0:
            reset_time = self.rate_limit_reset or time.time() + 60
            wait = max(1, reset_time - time.time())
            print(f"Rate limited. Waiting {wait:.0f}s...")
            time.sleep(wait)

    def _update_rate_limit(self, response: requests.Response) -> None:
        """Extract rate limit info from response headers."""
        self.rate_limit_remaining = int(response.headers.get("X-RateLimit-Remaining", "5000"))
        self.rate_limit_reset = int(response.headers.get("X-RateLimit-Reset", "0"))

    def get(self, endpoint: str, params: dict | None = None) -> dict[str, Any] | None:
        """Make a GET request with retry and rate-limit handling."""
        url = f"{DEFAULT_API_URL}{endpoint}"
        for attempt in range(self.max_retries):
            self._handle_rate_limit()
            try:
                response = self.session.get(url, params=params, timeout=30)
                self._update_rate_limit(response)
                if response.status_code == 200:
                    return response.json()
                if response.status_code == 404:
                    return None
                if response.status_code == 403 and self.rate_limit_remaining == 0:
                    continue
                response.raise_for_status()
            except requests.RequestException:
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None
        return None

    def get_repo(self, repo: str) -> dict[str, Any] | None:
        """Fetch repository metadata."""
        return self.get(f"/repos/{repo}")

    def get_commits(
        self, repo: str, since: datetime | None = None, until: datetime | None = None
    ) -> list[dict[str, Any]]:
        """Fetch commits within a date range, following Link-header pagination.

        GitHub's /repos/{repo}/commits endpoint returns at most 100 commits
        per page. The previous implementation only requested the first page,
        so any repo with more than 100 commits in the window had its
        `commits_30d` count silently truncated. We now follow the `rel="next"`
        Link header up to a generous page cap (1000 pages × 100 = 100k
        commits) to make the count accurate for any realistically active repo
        while still bounding work on misbehaving responses.
        """
        params: dict[str, Any] = {"per_page": 100}
        if since:
            params["since"] = since.isoformat()
        if until:
            params["until"] = until.isoformat()

        commits: list[dict[str, Any]] = []
        endpoint = f"/repos/{repo}/commits"
        # Cap to avoid runaway loops on a malformed or self-referential
        # Link header.
        max_pages = 1000
        for _ in range(max_pages):
            response = self.session.get(
                f"{DEFAULT_API_URL}{endpoint}", params=params, timeout=30
            )
            self._update_rate_limit(response)
            if response.status_code == 404:
                return commits
            if response.status_code != 200:
                # Mirror the existing get() retry policy: surface non-200 as
                # 'no more data' so the caller gets whatever we collected
                # on prior pages rather than losing the whole window.
                return commits
            page = response.json()
            if not isinstance(page, list) or not page:
                return commits
            commits.extend(page)
            link_header = response.headers.get("Link", "")
            next_url = self._next_link_url(link_header)
            if not next_url:
                return commits
            # Extract the query string from the next URL and use it as the
            # params for the following request so the since/until window
            # stays in effect.
            from urllib.parse import urlparse, parse_qs

            parsed = urlparse(next_url)
            next_params = parse_qs(parsed.query)
            # Normalize list-valued params from parse_qs back to scalars
            # for keys the existing call shape uses.
            params = {k: v[0] if len(v) == 1 else v for k, v in next_params.items()}
            endpoint = parsed.path
        return commits

    @staticmethod
    def _next_link_url(link_header: str) -> str | None:
        """Parse a GitHub Link header and return the `rel="next"` URL, if any.

        GitHub's pagination Link header looks like:
          <https://api.github.com/.../commits?page=2>; rel="next",
          <https://api.github.com/.../commits?page=831>; rel="last"
        A page with no further results has no Link header, or a Link
        header that lacks rel="next".
        """
        if not link_header:
            return None
        for part in link_header.split(","):
            section = part.strip()
            if 'rel="next"' not in section:
                continue
            # URL is the leading <...> token before the first semicolon.
            url_end = section.find(">")
            url_start = section.find("<")
            if url_start == -1 or url_end == -1 or url_end <= url_start:
                continue
            return section[url_start + 1 : url_end]
        return None

    def get_stargazers(self, repo: str) -> int:
        """Get star count for a repository."""
        data = self.get(f"/repos/{repo}")
        return data.get("stargazers_count", 0) if data else 0

    def get_activity_summary(self, repo: str, days: int = 30) -> dict[str, Any] | None:
        """Get activity summary for a repository over N days.
        
        Returns None if the repository cannot be found, to distinguish
        from a valid zero-activity response.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)
        repo_data = self.get_repo(repo)
        if not repo_data:
            return None
        commits = self.get_commits(repo, since=since)
        return {
            "repo": repo,
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "open_issues": repo_data.get("open_issues_count", 0),
            "commits_30d": len(commits),
            "last_updated": repo_data.get("pushed_at"),
            "description": repo_data.get("description", ""),
            "language": repo_data.get("language", ""),
        }


if __name__ == "__main__":
    api = GitHubAPI()
    result = api.get_activity_summary("HrachShah/FreeRelay")
    print(result)