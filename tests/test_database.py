"""Unit tests for ai_learning_coach.database.db."""

from __future__ import annotations

from ai_learning_coach.database.db import Database
from ai_learning_coach.database.models import HistoryRecord, LessonRecord


def test_upsert_and_get_next_lesson(tmp_db: Database) -> None:
    tmp_db.upsert_lesson(LessonRecord(id="a-1", module="m", title="T1", weekday="monday", sequence=1))
    tmp_db.upsert_lesson(LessonRecord(id="a-2", module="m", title="T2", weekday="monday", sequence=2))

    next_lesson = tmp_db.get_next_lesson("monday")
    assert next_lesson is not None
    assert next_lesson.id == "a-1"


def test_mark_lesson_completed_advances_next(tmp_db: Database) -> None:
    tmp_db.upsert_lesson(LessonRecord(id="a-1", module="m", title="T1", weekday="monday", sequence=1))
    tmp_db.upsert_lesson(LessonRecord(id="a-2", module="m", title="T2", weekday="monday", sequence=2))

    tmp_db.mark_lesson_completed("a-1", "2026-06-22")
    next_lesson = tmp_db.get_next_lesson("monday")
    assert next_lesson.id == "a-2"


def test_reset_module_restores_all_lessons(tmp_db: Database) -> None:
    tmp_db.upsert_lesson(LessonRecord(id="a-1", module="m", title="T1", weekday="monday", sequence=1))
    tmp_db.mark_lesson_completed("a-1", "2026-06-22")
    assert tmp_db.get_next_lesson("monday") is None

    tmp_db.reset_module("monday")
    assert tmp_db.get_next_lesson("monday").id == "a-1"


def test_record_and_get_history(tmp_db: Database) -> None:
    tmp_db.record_history(
        HistoryRecord(
            lesson_id="a-1",
            module="m",
            title="T1",
            publish_date="2026-06-22T08:00:00",
            status="success",
            generation_time_seconds=1.23,
        )
    )
    history = tmp_db.get_recent_history(limit=5)
    assert len(history) == 1
    assert history[0].status == "success"


def test_settings_roundtrip(tmp_db: Database) -> None:
    tmp_db.set_setting("foo", "bar")
    assert tmp_db.get_setting("foo") == "bar"
    assert tmp_db.get_setting("missing", "default") == "default"
