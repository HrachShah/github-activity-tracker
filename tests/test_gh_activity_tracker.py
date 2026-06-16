"""Tests for GitHub Activity Tracker."""

import unittest
import json
import os
import tempfile
from datetime import datetime

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

    def test_api_init_with_token(self):
        """API should use provided token."""
        api = GitHubAPI(token="ghp_test_token")
        self.assertEqual(api.token, "ghp_test_token")


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

    def test_format_csv_quotes_fields_with_commas(self):
        """CSV formatter quotes fields that contain commas (e.g. 'Jupyter Notebook, Python')."""
        import csv as _csv
        import io as _io
        data = [{
            "repo": "a/b",
            "stars": 1,
            "forks": 2,
            "open_issues": 3,
            "commits_30d": 4,
            "language": "Jupyter Notebook, Python",
            "last_updated": "2025-01-01",
        }]
        result = format_csv(data)
        rows = list(_csv.reader(_io.StringIO(result)))
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[1]), 7)
        self.assertEqual(rows[1][5], "Jupyter Notebook, Python")

    def test_format_csv_quotes_repo_names_with_commas(self):
        """CSV formatter quotes repo names that contain commas (typo or org with comma)."""
        import csv as _csv
        import io as _io
        data = [{
            "repo": "has,comma/c",
            "stars": 5,
            "forks": 0,
            "open_issues": 0,
            "commits_30d": 0,
            "language": "C++",
            "last_updated": "2025-01-01",
        }]
        result = format_csv(data)
        rows = list(_csv.reader(_io.StringIO(result)))
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[1]), 7)
        self.assertEqual(rows[1][0], "has,comma/c")
        self.assertEqual(rows[1][5], "C++")

    def test_format_csv_escapes_double_quotes(self):
        """CSV formatter escapes embedded double quotes per RFC 4180 ('a\"b' -> 'a\"\"b')."""
        import csv as _csv
        import io as _io
        data = [{
            "repo": 'has"quote/d',
            "stars": 0,
            "forks": 0,
            "open_issues": 0,
            "commits_30d": 0,
            "language": "Go",
            "last_updated": "2025-01-01",
        }]
        result = format_csv(data)
        rows = list(_csv.reader(_io.StringIO(result)))
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[1]), 7)
        self.assertEqual(rows[1][0], 'has"quote/d')

    def test_format_csv_handles_newlines_in_fields(self):
        """CSV formatter quotes fields containing newlines (e.g. multi-line descriptions)."""
        import csv as _csv
        import io as _io
        data = [{
            "repo": "has\nnewline/e",
            "stars": 0,
            "forks": 0,
            "open_issues": 0,
            "commits_30d": 0,
            "language": "Rust",
            "last_updated": "2025-01-01",
        }]
        result = format_csv(data)
        rows = list(_csv.reader(_io.StringIO(result)))
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[1]), 7)
        self.assertEqual(rows[1][0], "has\nnewline/e")


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
