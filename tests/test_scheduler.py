"""Unit tests for ai_learning_coach.scheduler.scheduler."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from ai_learning_coach.config import Settings
from ai_learning_coach.scheduler.scheduler import CoachScheduler


def _fake_settings(tmp_path: Path) -> Settings:
    return Settings(
        gemini_api_key="key",
        gemini_model="gemini-2.5-flash",
        telegram_bot_token="token",
        telegram_chat_id="123",
        timezone="UTC",
        lesson_time="09:30",
        db_path=tmp_path / "db.sqlite",
        log_dir=tmp_path / "logs",
        log_level="INFO",
        curriculum_dir=tmp_path / "curriculum",
        templates_dir=tmp_path / "templates",
    )


def test_scheduler_registers_job_with_correct_time(tmp_path: Path) -> None:
    settings = _fake_settings(tmp_path)
    fake_coach = MagicMock()
    scheduler = CoachScheduler(fake_coach, settings)

    with patch.object(scheduler.scheduler, "start") as mock_start:
        scheduler.start()
        mock_start.assert_called_once()

    job = scheduler.scheduler.get_job("daily_lesson_job")
    assert job is not None
    trigger_fields = {f.name: str(f) for f in job.trigger.fields}
    assert trigger_fields["hour"] == "9"
    assert trigger_fields["minute"] == "30"


def test_job_wrapper_calls_run_daily_job(tmp_path: Path) -> None:
    settings = _fake_settings(tmp_path)
    fake_coach = MagicMock()
    fake_coach.run_daily_job.return_value = True
    scheduler = CoachScheduler(fake_coach, settings)

    scheduler._job()

    fake_coach.run_daily_job.assert_called_once()
