"""Curriculum engine for AI Learning Coach.

This module is the single source of truth for *what* topics exist. Gemini
is never allowed to invent lesson topics — it only ever generates the
*content* for a topic that this engine has already chosen from the JSON
curriculum files.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ai_learning_coach.database.db import Database
from ai_learning_coach.database.models import LessonRecord

logger = logging.getLogger(__name__)

VALID_WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


class CurriculumError(RuntimeError):
    """Raised when curriculum data is missing, malformed, or exhausted."""


@dataclass(frozen=True)
class CurriculumTopic:
    """A single topic selected from the curriculum for content generation.

    Attributes:
        lesson_id: Stable curriculum identifier (e.g. "mon-03").
        module: Module name (e.g. "prompt_engineering").
        title: Human-facing lesson title (chosen by curriculum, not by Gemini).
        weekday: Weekday this topic belongs to.
        lesson_type: One of "lesson", "mini_project", "quiz".
    """

    lesson_id: str
    module: str
    title: str
    weekday: str
    lesson_type: str


class CurriculumEngine:
    """Loads curriculum JSON files and selects the next lesson to publish.

    The engine seeds the database from JSON on every load (idempotent —
    existing rows are left untouched) and then asks the database for the
    next *incomplete* lesson belonging to today's weekday module. If a
    weekday's module is fully exhausted, it automatically wraps around by
    resetting that module's completion state, so the curriculum repeats
    indefinitely rather than ever running dry.
    """

    def __init__(self, curriculum_dir: Path, database: Database) -> None:
        """Initialize the engine and seed the database from JSON files.

        Args:
            curriculum_dir: Directory containing one JSON file per weekday.
            database: Database instance used for tracking completion.

        Raises:
            CurriculumError: If curriculum files are missing or malformed.
        """
        self.curriculum_dir = Path(curriculum_dir)
        self.database = database
        self._modules: dict[str, dict] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Load and validate every weekday's curriculum JSON file."""
        for weekday in VALID_WEEKDAYS:
            file_path = self.curriculum_dir / f"{weekday}.json"
            if not file_path.exists():
                raise CurriculumError(f"Missing curriculum file: {file_path}")
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise CurriculumError(f"Invalid JSON in {file_path}: {exc}") from exc

            self._validate_module(data, weekday)
            self._modules[weekday] = data
            self._seed_database(data, weekday)

        logger.info("Curriculum loaded for all %d weekdays", len(self._modules))

    @staticmethod
    def _validate_module(data: dict, weekday: str) -> None:
        """Validate a parsed curriculum module's structure."""
        required_keys = {"weekday", "module", "lessons"}
        missing = required_keys - data.keys()
        if missing:
            raise CurriculumError(f"Curriculum file for {weekday} missing keys: {missing}")
        if data["weekday"] != weekday:
            raise CurriculumError(
                f"Curriculum file weekday mismatch: file={weekday}, content={data['weekday']}"
            )
        if not isinstance(data["lessons"], list) or not data["lessons"]:
            raise CurriculumError(f"Curriculum file for {weekday} has no lessons")
        for lesson in data["lessons"]:
            for key in ("id", "title", "sequence"):
                if key not in lesson:
                    raise CurriculumError(
                        f"Lesson entry in {weekday}.json missing required key '{key}': {lesson}"
                    )

    def _seed_database(self, data: dict, weekday: str) -> None:
        """Insert any not-yet-known lessons into the database (idempotent)."""
        module_name = data["module"]
        for lesson in data["lessons"]:
            record = LessonRecord(
                id=lesson["id"],
                module=module_name,
                title=lesson["title"],
                weekday=weekday,
                sequence=lesson["sequence"],
            )
            self.database.upsert_lesson(record)

    def get_topic_for_weekday(self, weekday: str) -> CurriculumTopic:
        """Select the next topic to publish for the given weekday.

        If every lesson in the weekday's module has already been completed,
        the module is automatically reset so the curriculum cycles rather
        than raising an error — this keeps the daily job running forever.

        Args:
            weekday: Lowercase weekday name, e.g. "monday".

        Returns:
            The chosen `CurriculumTopic`.

        Raises:
            CurriculumError: If `weekday` is not a recognized weekday.
        """
        weekday = weekday.lower()
        if weekday not in self._modules:
            raise CurriculumError(f"Unknown weekday: {weekday}")

        module_data = self._modules[weekday]
        lesson_type = module_data.get("lesson_type", "lesson")

        next_lesson = self.database.get_next_lesson(weekday)
        if next_lesson is None:
            logger.info("Module '%s' exhausted — resetting for a new cycle", weekday)
            self.database.reset_module(weekday)
            next_lesson = self.database.get_next_lesson(weekday)
            if next_lesson is None:
                raise CurriculumError(f"Curriculum module '{weekday}' has no lessons defined")

        return CurriculumTopic(
            lesson_id=next_lesson.id,
            module=next_lesson.module,
            title=next_lesson.title,
            weekday=weekday,
            lesson_type=lesson_type,
        )

    def mark_published(self, lesson_id: str, publish_date: str) -> None:
        """Mark the given lesson as completed/published.

        Args:
            lesson_id: Curriculum lesson id to mark complete.
            publish_date: ISO date string of publication.
        """
        self.database.mark_lesson_completed(lesson_id, publish_date)
