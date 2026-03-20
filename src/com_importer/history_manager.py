"""
History manager for tracking created dangers.

Persists danger creation history to SQLite database for review, export, and re-editing.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


class HistoryEntry:
    """Represents a single history entry."""

    def __init__(
        self,
        actor_id: str,
        danger_name: str,
        danger_rating: str | None = None,
        actor_json: dict[str, Any] | None = None,
        foundry_url: str | None = None,
        created_at: datetime | None = None,
        source: str = "text",  # "text", "image", "pdf", "batch"
        status: str = "success",  # "success", "failed"
        error_message: str | None = None,
    ) -> None:
        """Initialize a history entry."""
        self.actor_id = actor_id
        self.danger_name = danger_name
        self.danger_rating = danger_rating
        self.actor_json = actor_json or {}
        self.foundry_url = foundry_url
        self.created_at = created_at or datetime.now()
        self.source = source
        self.status = status
        self.error_message = error_message

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "actor_id": self.actor_id,
            "danger_name": self.danger_name,
            "danger_rating": self.danger_rating,
            "actor_json": self.actor_json,
            "foundry_url": self.foundry_url,
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "status": self.status,
            "error_message": self.error_message,
        }


class HistoryManager:
    """Manages danger creation history with SQLite persistence."""

    DB_SCHEMA_VERSION = 1

    def __init__(self, db_path: str | Path = None) -> None:
        """
        Initialize the history manager.

        Args:
            db_path: Path to SQLite database file. Uses ~/.com-importer/history.db if not provided.
        """
        if db_path is None:
            db_dir = Path.home() / ".com-importer"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = db_dir / "history.db"
        else:
            db_path = Path(db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor_id TEXT UNIQUE NOT NULL,
                    danger_name TEXT NOT NULL,
                    danger_rating TEXT,
                    actor_json TEXT,
                    foundry_url TEXT,
                    created_at TIMESTAMP NOT NULL,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT
                )
                """
            )

            # Create indices for common queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON history(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON history(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON history(source)")
            conn.commit()

    def add_entry(self, entry: HistoryEntry) -> int:
        """
        Add an entry to history.

        Args:
            entry: HistoryEntry to add

        Returns:
            Row ID of the added entry
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO history
                (actor_id, danger_name, danger_rating, actor_json, foundry_url,
                 created_at, source, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.actor_id,
                    entry.danger_name,
                    entry.danger_rating,
                    json.dumps(entry.actor_json),
                    entry.foundry_url,
                    entry.created_at.isoformat(),
                    entry.source,
                    entry.status,
                    entry.error_message,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_entry(self, actor_id: str) -> HistoryEntry | None:
        """Get a single history entry by actor ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM history WHERE actor_id = ?", (actor_id,))
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_entry(row)

    def get_recent(self, limit: int = 50) -> list[HistoryEntry]:
        """Get recent history entries."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT * FROM history
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()

        return [self._row_to_entry(row) for row in rows]

    def get_by_status(self, status: str, limit: int = 50) -> list[HistoryEntry]:
        """Get entries filtered by status (success, failed)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT * FROM history
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (status, limit),
            )
            rows = cursor.fetchall()

        return [self._row_to_entry(row) for row in rows]

    def get_by_source(self, source: str, limit: int = 50) -> list[HistoryEntry]:
        """Get entries filtered by source (text, image, pdf, batch)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT * FROM history
                WHERE source = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (source, limit),
            )
            rows = cursor.fetchall()

        return [self._row_to_entry(row) for row in rows]

    def get_all(self) -> list[HistoryEntry]:
        """Get all history entries."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM history ORDER BY created_at DESC")
            rows = cursor.fetchall()

        return [self._row_to_entry(row) for row in rows]

    def delete_entry(self, actor_id: str) -> bool:
        """Delete a history entry."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM history WHERE actor_id = ?", (actor_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_all(self) -> int:
        """Clear all history entries."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM history")
            conn.commit()
            return cursor.rowcount

    def export_csv(self, output_path: str | Path) -> None:
        """Export history to CSV file."""
        import csv

        output_path = Path(output_path)
        entries = self.get_all()

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Actor ID",
                    "Danger Name",
                    "Rating",
                    "Created At",
                    "Source",
                    "Status",
                ]
            )

            for entry in entries:
                writer.writerow(
                    [
                        entry.actor_id,
                        entry.danger_name,
                        entry.danger_rating or "",
                        entry.created_at.isoformat(),
                        entry.source,
                        entry.status,
                    ]
                )

    def export_json(self, output_path: str | Path) -> None:
        """Export history to JSON file."""
        output_path = Path(output_path)
        entries = self.get_all()

        data = {
            "exported_at": datetime.now().isoformat(),
            "entry_count": len(entries),
            "entries": [entry.to_dict() for entry in entries],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about the history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count,
                    MAX(created_at) as last_created
                FROM history
                """
            )
            row = cursor.fetchone()

        return {
            "total": row[0] or 0,
            "success": row[1] or 0,
            "failed": row[2] or 0,
            "last_created": row[3],
            "by_source": self._get_source_counts(),
        }

    def _get_source_counts(self) -> dict[str, int]:
        """Get counts by source type."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT source, COUNT(*) as count
                FROM history
                GROUP BY source
                """
            )
            rows = cursor.fetchall()

        return {row[0]: row[1] for row in rows}

    @staticmethod
    def _row_to_entry(row: tuple) -> HistoryEntry:
        """Convert a database row to a HistoryEntry."""
        _, actor_id, name, rating, actor_json_str, url, created_at, source, status, error = row

        actor_json = json.loads(actor_json_str) if actor_json_str else {}

        return HistoryEntry(
            actor_id=actor_id,
            danger_name=name,
            danger_rating=rating,
            actor_json=actor_json,
            foundry_url=url,
            created_at=datetime.fromisoformat(created_at),
            source=source,
            status=status,
            error_message=error,
        )
