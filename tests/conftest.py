"""Shared pytest fixtures for AI Learning Coach tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_learning_coach.database.db import Database

SAMPLE_CURRICULUM = {
    "weekday": "monday",
    "module": "prompt_engineering",
    "lessons": [
        {"id": "mon-01", "title": "Lesson One", "sequence": 1},
        {"id": "mon-02", "title": "Lesson Two", "sequence": 2},
    ],
}

ALL_WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Database:
    """Provide a fresh temporary SQLite database."""
    return Database(tmp_path / "test.db")


@pytest.fixture()
def curriculum_dir(tmp_path: Path) -> Path:
    """Create a full set of minimal valid curriculum JSON files for all weekdays."""
    directory = tmp_path / "curriculum"
    directory.mkdir()
    for weekday in ALL_WEEKDAYS:
        data = {
            "weekday": weekday,
            "module": f"{weekday}_module",
            "lessons": [
                {"id": f"{weekday}-01", "title": f"{weekday.title()} Lesson One", "sequence": 1},
                {"id": f"{weekday}-02", "title": f"{weekday.title()} Lesson Two", "sequence": 2},
            ],
        }
        if weekday == "saturday":
            data["lesson_type"] = "mini_project"
        if weekday == "sunday":
            data["lesson_type"] = "quiz"
        (directory / f"{weekday}.json").write_text(json.dumps(data), encoding="utf-8")
    return directory
