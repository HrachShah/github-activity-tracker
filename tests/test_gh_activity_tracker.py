"""Tests for GitHub Activity Tracker."""

import unittest
import json
import os
import tempfile
from datetime import datetime
from unittest.mock import Mock

from gh_activity_tracker.tracker import ActivityTracker
from gh_activity_tracker.github_api import GitHubAPI
from gh_activity_tracker.formatters import format_text, format_json, format_csv
from gh_activity_tracker.storage import ActivityStorage


class TestGitHubAPI(unittest.TestCase):
    """Tests for GitHub API client."""

    def test_api_init_without_token(self):
        """API should initialize without a token."""
        api = GitHubAPI()
        self.assertIsNone(api.token)

    def test_api_rejects_non_positive_retry_counts(self):
        for max_retries, error in ((0, ValueError), (True, TypeError), (1.5, TypeError)):
            with self.subTest(max_retries=max_retries):
                with self.assertRaises(error):
                    GitHubAPI(max_retries=max_retries)

    def test_api_init_with_token(self):
        """API should use provided token."""
        api = GitHubAPI(token="ghp_test_token")
        self.assertEqual(api.token, "ghp_test_token")

    def test_activity_summary_names_commit_window_after_requested_days(self):
        """The summary key must describe the requested history window."""
        from unittest.mock import patch

        api = GitHubAPI()
        with patch.object(api, "get_repo", return_value={"stargazers_count": 1, "forks_count": 2, "open_issues_count": 3}), \
             patch.object(api, "get_commits", return_value=[{}, {}]):
            summary = api.get_activity_summary("owner/repo", days=7)

        self.assertEqual(summary["commits_7d"], 2)
        self.assertNotIn("commits_30d", summary)

    def test_get_commits_follows_github_pagination(self):
        """Commit summaries must include commits beyond the first API page."""
        api = GitHubAPI()
        first_page = [{"sha": str(index)} for index in range(100)]
        second_page = [{"sha": "100"}]
        api.get = Mock(side_effect=[first_page, second_page])

        commits = api.get_commits("owner/repo")

        self.assertEqual(len(commits), 101)
        self.assertEqual(api.get.call_args_list[0].kwargs["params"]["page"], 1)
        self.assertEqual(api.get.call_args_list[1].kwargs["params"]["page"], 2)

    def test_repository_helpers_ignore_non_object_payloads(self):
        """Malformed successful payloads should not crash repository helpers."""
        api = GitHubAPI()
        api.get = Mock(return_value=[{"stargazers_count": 4}])

        self.assertIsNone(api.get_repo("owner/repo"))
        self.assertEqual(api.get_stargazers("owner/repo"), 0)

    def test_malformed_rate_limit_headers_do_not_break_requests(self):
        """Unexpected rate-limit headers should not abort an otherwise valid response."""
        api = GitHubAPI()
        response = Mock()
        response.headers = {"X-RateLimit-Remaining": "unknown", "X-RateLimit-Reset": "later"}
        api._update_rate_limit(response)
        self.assertIsNone(api.rate_limit_remaining)
        self.assertIsNone(api.rate_limit_reset)

    def test_negative_rate_limit_headers_are_clamped(self):
        """Malformed negative counters must not trigger a rate-limit wait."""
        api = GitHubAPI()
        response = Mock()
        response.headers = {"X-RateLimit-Remaining": "-1", "X-RateLimit-Reset": "-2"}

        api._update_rate_limit(response)

        self.assertEqual(api.rate_limit_remaining, 0)
        self.assertEqual(api.rate_limit_reset, 0)


class TestFormatters(unittest.TestCase):
    """Tests for output formatters."""

    def test_format_text_empty(self):
        """Text formatter handles empty data."""
        result = format_text([])
        self.assertEqual(result, "No data available.")

    def test_format_text_single_repo(self):
        """Text formatter formats single repo correctly."""
        data = [{
            "repo": "test/repo",
            "stars": 100,
            "forks": 20,
            "open_issues": 5,
            "commits_30d": 42,
            "language": "Python",
            "last_updated": "2026-04-20T12:00:00Z",
        }]
        result = format_text(data)
        self.assertIn("test/repo", result)
        self.assertIn("100", result)
        self.assertIn("Python", result)

    def test_format_json_empty(self):
        """JSON formatter handles empty data."""
        result = format_json([])
        self.assertEqual(result, "[]")

    def test_format_json_single_repo(self):
        """JSON formatter outputs valid JSON."""
        data = [{"repo": "test/repo", "stars": 100}]
        result = format_json(data)
        parsed = json.loads(result)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["repo"], "test/repo")

    def test_format_csv_empty(self):
        """CSV formatter handles empty data."""
        result = format_csv([])
        self.assertEqual(result, "")

    def test_format_csv_single_repo(self):
        """CSV formatter outputs valid CSV with headers."""
        data = [{"repo": "test/repo", "stars": 100, "forks": 0, "open_issues": 0, "commits_30d": 0, "language": "", "last_updated": ""}]
        result = format_csv(data)
        lines = result.split("\n")
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("repo"))
        self.assertTrue(lines[1].startswith("test/repo"))
    def test_format_csv_quotes_values_containing_commas(self):
        """CSV formatter preserves commas inside text fields."""
        data = [{"repo": "test/repo", "stars": 100, "forks": 0, "open_issues": 0, "commits_30d": 0, "language": "C, C++", "last_updated": ""}]

        result = format_csv(data)

        self.assertIn('"C, C++"', result)

    def test_format_csv_header(self):
        """CSV formatter includes correct headers."""
        data = [{
            "repo": "test/repo",
            "stars": 100,
            "forks": 20,
            "open_issues": 5,
            "commits_30d": 42,
            "language": "Python",
            "last_updated": "2026-04-20T12:00:00Z",
        }]
        result = format_csv(data)
        lines = result.strip().split("\n")
        self.assertIn("repo", lines[0].lower())
        self.assertIn("stars", lines[0].lower())


class TestActivityTracker(unittest.TestCase):
    """Tests for activity tracker."""

    def test_tracker_init(self):
        """Tracker initializes with API client."""
        tracker = ActivityTracker()
        self.assertIsNotNone(tracker.api)

    def test_activity_summary_rejects_negative_history_window(self):
        """A negative history window must not query a future date range."""
        api = GitHubAPI()
        with self.assertRaisesRegex(ValueError, "days must be non-negative"):
            api.get_activity_summary("owner/repo", days=-1)

    def test_activity_summary_rejects_non_integer_history_window(self):
        """A fractional or boolean history window must not reach timedelta."""
        api = GitHubAPI()
        for days in (1.5, True):
            with self.subTest(days=days):
                with self.assertRaisesRegex(TypeError, "days must be an integer"):
                    api.get_activity_summary("owner/repo", days=days)

    def test_tracker_has_rate_limit_props(self):
        """Tracker exposes rate limit properties for monitoring."""
        tracker = ActivityTracker()
        self.assertTrue(hasattr(tracker, "rate_limit_remaining"))
        self.assertTrue(hasattr(tracker, "rate_limit_reset"))


class TestActivityStorage(unittest.TestCase):
    """Tests for SQLite storage."""

    def test_storage_init(self):
        """Storage initializes and creates tables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            storage = ActivityStorage(db_path=db_path)
            self.assertTrue(os.path.exists(db_path))

    def test_storage_schema_version(self):
        """Storage tracks schema version for migrations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "schema_test.db")
            storage = ActivityStorage(db_path=db_path)
            self.assertTrue(hasattr(storage, "schema_version"))
            self.assertEqual(storage.schema_version, 1)

    def test_get_snapshots_rejects_invalid_limits(self):
        """Snapshot queries must not accept negative or boolean limits."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ActivityStorage(db_path=os.path.join(tmpdir, "limits.db"))
            for limit, error in ((-1, ValueError), (True, TypeError), (1.5, TypeError)):
                with self.subTest(limit=limit):
                    with self.assertRaises(error):
                        storage.get_snapshots("owner/repo", limit=limit)


if __name__ == "__main__":
    unittest.main()
