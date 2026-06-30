"""Data models for AI Learning Coach's SQLite-backed persistence layer.

These are simple, framework-free dataclasses representing rows. The actual
SQL lives in `database.db`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class LessonRecord:
    """Represents a single curriculum lesson and its completion state.

    Attributes:
        id: Primary key (curriculum-defined lesson id, e.g. "mon-01").
        module: Curriculum module/day name (e.g. "prompt_engineering").
        title: Human-readable lesson title.
        weekday: Weekday this lesson belongs to ("monday".."sunday").
        sequence: Ordering index within the module.
        completed: Whether this lesson has already been published.
        publish_date: ISO date string of when it was published, if any.
    """

    id: str
    module: str
    title: str
    weekday: str
    sequence: int
    completed: bool = False
    publish_date: Optional[str] = None


@dataclass
class HistoryRecord:
    """Represents one publishing attempt (success or failure) for audit/history.

    Attributes:
        id: Auto-increment primary key (None until inserted).
        lesson_id: Foreign key referencing `lessons.id`.
        module: Module/day name, duplicated for easy querying.
        title: Lesson title, duplicated for easy querying.
        publish_date: ISO datetime string of the publish attempt.
        status: "success" or "failure".
        generation_time_seconds: Wall-clock time spent generating the lesson.
        error_message: Error details if status == "failure".
    """

    lesson_id: str
    module: str
    title: str
    publish_date: str
    status: str
    generation_time_seconds: float
    error_message: Optional[str] = None
    id: Optional[int] = None


def now_iso() -> str:
    """Return the current UTC timestamp as an ISO 8601 string."""
    return datetime.utcnow().isoformat(timespec="seconds")


def today_iso() -> str:
    """Return today's date (UTC) as an ISO 8601 date string."""
    return date.today().isoformat()
