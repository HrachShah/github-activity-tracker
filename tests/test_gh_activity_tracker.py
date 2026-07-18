"""Tests for GitHub Activity Tracker."""

import unittest
import json
import csv
import io
import os
import tempfile
from datetime import datetime
from pathlib import Path

from gh_activity_tracker.tracker import ActivityTracker
from gh_activity_tracker.github_api import GitHubAPI
from gh_activity_tracker.formatters import format_text, format_json, format_csv
from gh_activity_tracker.storage import ActivityStorage
from unittest.mock import patch


class TestGitHubAPI(unittest.TestCase):
    """Tests for GitHub API client."""

    def test_api_init_without_token(self):
        """API should initialize without a token."""
        api = GitHubAPI()
        self.assertIsNone(api.token)

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

    def test_activity_summary_rejects_non_positive_history_window(self):
        """A non-positive window must not query commits from the future."""
        api = GitHubAPI()
        with self.assertRaisesRegex(ValueError, "days must be at least 1"):
            api.get_activity_summary("owner/repo", days=0)

    def test_activity_summary_ignores_non_object_repository_payloads(self):
        """A scalar or list repository response should behave like a missing repo."""
        api = GitHubAPI()
        with patch.object(api, "get_repo", return_value=[]), \
             patch.object(api, "get_commits") as get_commits:
            self.assertIsNone(api.get_activity_summary("owner/repo"))
        get_commits.assert_not_called()

    def test_malformed_rate_limit_headers_do_not_abort_response_handling(self):
        """Non-numeric proxy headers should leave rate-limit values unknown."""
        from unittest.mock import Mock

        api = GitHubAPI()
        response = Mock()
        response.headers = {
            "X-RateLimit-Remaining": "unknown",
            "X-RateLimit-Reset": None,
        }
        api._update_rate_limit(response)
        self.assertIsNone(api.rate_limit_remaining)
        self.assertIsNone(api.rate_limit_reset)

    def test_negative_rate_limit_headers_are_not_treated_as_exhausted(self):
        """Negative headers should not trigger an unnecessary rate-limit wait."""
        from unittest.mock import Mock

        api = GitHubAPI()
        response = Mock()
        response.headers = {
            "X-RateLimit-Remaining": "-1",
            "X-RateLimit-Reset": "-1",
        }
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
        import csv
        import io

        data = [{"repo": "test/repo", "stars": 100, "forks": 0, "open_issues": 0, "commits_30d": 0, "language": "", "last_updated": ""}]
        result = format_csv(data)
        rows = list(csv.reader(io.StringIO(result)))
        self.assertEqual(len(rows), 2, f"expected header + 1 data row, got {len(rows)} rows: {result!r}")
        self.assertEqual(rows[0][0], "repo")
        self.assertEqual(rows[1][0], "test/repo")
        self.assertEqual(rows[1][1], "100")

    def test_format_csv_uses_commit_window_from_later_row(self):
        """CSV output keeps the commit column when the first row lacks it."""
        data = [
            {"repo": "first/repo", "stars": 1},
            {"repo": "second/repo", "commits_7d": 3},
        ]
        rows = list(csv.reader(io.StringIO(format_csv(data))))
        self.assertIn("commits_7d", rows[0])
        self.assertEqual(rows[2][4], "3")

    def test_format_csv_fills_missing_fields_with_empty_values(self):
        """Rows without optional metrics should still have all CSV columns."""
        data = [{"repo": "owner/repo"}]
        rows = list(csv.reader(io.StringIO(format_csv(data))))
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[0]), len(rows[1]))
        self.assertEqual(rows[1], ["owner/repo", "", "", "", "", "", ""])

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

    def test_format_csv_quotes_field_containing_comma(self):
        """A repo name with a comma must be quoted so it does not split into extra cells."""
        import csv
        import io

        data = [{"repo": "owner/repo,with,commas", "stars": 100, "forks": 0, "open_issues": 0, "commits_30d": 0, "language": "Python", "last_updated": "2026-04-20"}]
        result = format_csv(data)
        rows = list(csv.reader(io.StringIO(result)))
        self.assertEqual(len(rows), 2, f"expected header + 1 data row, got: {result!r}")
        self.assertEqual(rows[1][0], "owner/repo,with,commas")
        self.assertEqual(rows[1][5], "Python")

    def test_format_csv_doubles_internal_quotes(self):
        """A field containing a quote must double the quote so csv.reader restores it."""
        import csv
        import io

        data = [{"repo": "owner/repo", "stars": 100, "forks": 0, "open_issues": 0, "commits_30d": 0, "language": 'Python "snake"', "last_updated": "2026-04-20"}]
        result = format_csv(data)
        rows = list(csv.reader(io.StringIO(result)))
        self.assertEqual(rows[1][5], 'Python "snake"')

    def test_format_csv_quotes_field_containing_newline(self):
        """A field containing a newline must stay on one logical row, not split rows."""
        import csv
        import io

        data = [{"repo": "owner/repo", "stars": 100, "forks": 0, "open_issues": 0, "commits_30d": 0, "language": "Python\nis\ngreat", "last_updated": "2026-04-20"}]
        result = format_csv(data)
        rows = list(csv.reader(io.StringIO(result)))
        self.assertEqual(len(rows), 2, f"expected header + 1 data row, got {len(rows)} rows: {result!r}")
        self.assertEqual(rows[1][5], "Python\nis\ngreat")


class TestCLIFileEncoding(unittest.TestCase):
    def test_input_file_is_read_as_utf8(self):
        from gh_activity_tracker import cli
        import argparse

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "repos.txt"
            path.write_text("owner/répo\n", encoding="utf-8")
            args = argparse.Namespace(
                token=None, save=False, input=str(path), repos=[], days=1,
                format="json", output=None,
            )
            with patch.object(cli.ActivityTracker, "track_multiple", return_value=[]) as track:
                cli.cmd_track(args)
            track.assert_called_once_with(["owner/répo"], days=1)


class TestActivityTracker(unittest.TestCase):
    """Tests for activity tracker."""

    def test_tracker_init(self):
        """Tracker initializes with API client."""
        tracker = ActivityTracker()
        self.assertIsNotNone(tracker.api)

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


if __name__ == "__main__":
    unittest.main()
