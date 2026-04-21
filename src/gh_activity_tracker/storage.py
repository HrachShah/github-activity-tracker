"""SQLite storage for activity snapshots."""

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any


class ActivityStorage:
    """Persistent storage for activity snapshots using SQLite."""
    
    SCHEMA_VERSION = 1

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or os.path.expanduser("~/.gh-activity-tracker.db")
        self._init_db()

    @property
    def schema_version(self) -> int:
        """Return current schema version for migrations."""
        return self.SCHEMA_VERSION

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo TEXT NOT NULL,
                stars INTEGER,
                forks INTEGER,
                open_issues INTEGER,
                commits INTEGER,
                language TEXT,
                description TEXT,
                snapshot_at TEXT NOT NULL,
                UNIQUE(repo, snapshot_at)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tracked_repos (
                repo TEXT PRIMARY KEY,
                added_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()

    def save_snapshot(self, activity: dict[str, Any]) -> None:
        """Save an activity snapshot to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO snapshots
            (repo, stars, forks, open_issues, commits, language, description, snapshot_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                activity.get("repo"),
                activity.get("stars"),
                activity.get("forks"),
                activity.get("open_issues"),
                activity.get("commits_30d"),
                activity.get("language"),
                activity.get("description"),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def get_snapshots(self, repo: str, limit: int = 30) -> list[dict[str, Any]]:
        """Get historical snapshots for a repository."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM snapshots WHERE repo = ? ORDER BY snapshot_at DESC LIMIT ?",
            (repo, limit),
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def add_tracked_repo(self, repo: str) -> None:
        """Add a repository to the tracking list."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO tracked_repos (repo, added_at) VALUES (?, ?)",
            (repo, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()

    def get_tracked_repos(self) -> list[str]:
        """Get all tracked repositories."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT repo FROM tracked_repos ORDER BY added_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [row["repo"] for row in rows]

    def remove_tracked_repo(self, repo: str) -> None:
        """Remove a repository from tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tracked_repos WHERE repo = ?", (repo,))
        conn.commit()
        conn.close()
