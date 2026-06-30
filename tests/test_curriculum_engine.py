"""Unit tests for ai_learning_coach.curriculum.engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_learning_coach.curriculum.engine import CurriculumEngine, CurriculumError
from ai_learning_coach.database.db import Database


def test_loads_all_weekdays(curriculum_dir: Path, tmp_db: Database) -> None:
    engine = CurriculumEngine(curriculum_dir, tmp_db)
    topic = engine.get_topic_for_weekday("monday")
    assert topic.weekday == "monday"
    assert topic.lesson_type == "lesson"
    assert topic.title == "Monday Lesson One"


def test_lesson_type_detected_for_saturday_and_sunday(curriculum_dir: Path, tmp_db: Database) -> None:
    engine = CurriculumEngine(curriculum_dir, tmp_db)
    saturday_topic = engine.get_topic_for_weekday("saturday")
    sunday_topic = engine.get_topic_for_weekday("sunday")
    assert saturday_topic.lesson_type == "mini_project"
    assert sunday_topic.lesson_type == "quiz"


def test_next_lesson_advances_after_marking_published(curriculum_dir: Path, tmp_db: Database) -> None:
    engine = CurriculumEngine(curriculum_dir, tmp_db)
    first = engine.get_topic_for_weekday("monday")
    engine.mark_published(first.lesson_id, "2026-06-22")

    second = engine.get_topic_for_weekday("monday")
    assert second.lesson_id != first.lesson_id
    assert second.title == "Monday Lesson Two"


def test_module_cycles_after_exhaustion(curriculum_dir: Path, tmp_db: Database) -> None:
    engine = CurriculumEngine(curriculum_dir, tmp_db)
    first = engine.get_topic_for_weekday("monday")
    engine.mark_published(first.lesson_id, "2026-06-22")
    second = engine.get_topic_for_weekday("monday")
    engine.mark_published(second.lesson_id, "2026-06-23")

    # Both lessons now complete -> should wrap around to lesson one again.
    third = engine.get_topic_for_weekday("monday")
    assert third.lesson_id == first.lesson_id


def test_unknown_weekday_raises(curriculum_dir: Path, tmp_db: Database) -> None:
    engine = CurriculumEngine(curriculum_dir, tmp_db)
    with pytest.raises(CurriculumError):
        engine.get_topic_for_weekday("funday")


def test_missing_curriculum_file_raises(tmp_path: Path, tmp_db: Database) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    with pytest.raises(CurriculumError):
        CurriculumEngine(empty_dir, tmp_db)
