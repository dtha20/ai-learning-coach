"""SQLite persistence layer for AI Learning Coach.

This module owns all SQL. It exposes a `Database` class with explicit
methods (no ORM) so behavior is easy to test and reason about.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from ai_learning_coach.database.models import HistoryRecord, LessonRecord, now_iso

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS lessons (
    id              TEXT PRIMARY KEY,
    module          TEXT NOT NULL,
    title           TEXT NOT NULL,
    weekday         TEXT NOT NULL,
    sequence        INTEGER NOT NULL,
    completed       INTEGER NOT NULL DEFAULT 0,
    publish_date    TEXT
);

CREATE TABLE IF NOT EXISTS history (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id               TEXT NOT NULL,
    module                  TEXT NOT NULL,
    title                   TEXT NOT NULL,
    publish_date            TEXT NOT NULL,
    status                  TEXT NOT NULL,
    generation_time_seconds REAL NOT NULL,
    error_message           TEXT,
    FOREIGN KEY (lesson_id) REFERENCES lessons (id)
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class Database:
    """Thin wrapper around a SQLite database file for AI Learning Coach.

    All connections are opened per-operation (SQLite + short-lived
    connections is the simplest safe pattern for a single-process scheduler).
    """

    def __init__(self, db_path: Path) -> None:
        """Initialize the database, creating the file/schema if needed.

        Args:
            db_path: Filesystem path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Open a connection with row-factory and foreign keys enabled."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        """Create tables if they do not already exist."""
        with self._connect() as conn:
            conn.executescript(SCHEMA)
        logger.debug("Database schema ensured at %s", self.db_path)

    # ------------------------------------------------------------------ #
    # Lessons
    # ------------------------------------------------------------------ #

    def upsert_lesson(self, lesson: LessonRecord) -> None:
        """Insert a lesson if it doesn't exist; ignore if it already does.

        This is used to seed the database from the curriculum JSON files
        without overwriting completion state on repeated runs.
        """
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO lessons (id, module, title, weekday, sequence, completed, publish_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (
                    lesson.id,
                    lesson.module,
                    lesson.title,
                    lesson.weekday,
                    lesson.sequence,
                    int(lesson.completed),
                    lesson.publish_date,
                ),
            )

    def get_next_lesson(self, weekday: str) -> Optional[LessonRecord]:
        """Return the next incomplete lesson for the given weekday module.

        Args:
            weekday: Lowercase weekday name, e.g. "monday".

        Returns:
            The lowest-sequence incomplete `LessonRecord` for that weekday,
            or None if every lesson in that module is already completed.
        """
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM lessons
                WHERE weekday = ? AND completed = 0
                ORDER BY sequence ASC
                LIMIT 1
                """,
                (weekday,),
            ).fetchone()
        return self._row_to_lesson(row) if row else None

    def mark_lesson_completed(self, lesson_id: str, publish_date: str) -> None:
        """Mark a lesson as completed with the given publish date."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE lessons SET completed = 1, publish_date = ? WHERE id = ?",
                (publish_date, lesson_id),
            )

    def reset_module(self, weekday: str) -> None:
        """Reset completion status for all lessons in a weekday module.

        Useful once a module's lesson list is exhausted and should restart,
        or for administrative resets.
        """
        with self._connect() as conn:
            conn.execute(
                "UPDATE lessons SET completed = 0, publish_date = NULL WHERE weekday = ?",
                (weekday,),
            )

    @staticmethod
    def _row_to_lesson(row: sqlite3.Row) -> LessonRecord:
        return LessonRecord(
            id=row["id"],
            module=row["module"],
            title=row["title"],
            weekday=row["weekday"],
            sequence=row["sequence"],
            completed=bool(row["completed"]),
            publish_date=row["publish_date"],
        )

    # ------------------------------------------------------------------ #
    # History
    # ------------------------------------------------------------------ #

    def record_history(self, record: HistoryRecord) -> None:
        """Insert a new history row representing a publish attempt."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO history
                    (lesson_id, module, title, publish_date, status, generation_time_seconds, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.lesson_id,
                    record.module,
                    record.title,
                    record.publish_date,
                    record.status,
                    record.generation_time_seconds,
                    record.error_message,
                ),
            )

    def get_recent_history(self, limit: int = 10) -> list[HistoryRecord]:
        """Return the most recent history entries, newest first."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            HistoryRecord(
                id=row["id"],
                lesson_id=row["lesson_id"],
                module=row["module"],
                title=row["title"],
                publish_date=row["publish_date"],
                status=row["status"],
                generation_time_seconds=row["generation_time_seconds"],
                error_message=row["error_message"],
            )
            for row in rows
        ]

    # ------------------------------------------------------------------ #
    # Settings (simple key/value store, e.g. for last-run bookkeeping)
    # ------------------------------------------------------------------ #

    def set_setting(self, key: str, value: str) -> None:
        """Set (or overwrite) a key/value setting."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a setting value by key, or `default` if not present."""
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def mark_last_run(self) -> None:
        """Record the current timestamp as the last successful scheduler run."""
        self.set_setting("last_run_at", now_iso())
