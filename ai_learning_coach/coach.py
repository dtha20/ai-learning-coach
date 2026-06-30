"""Top-level orchestrator for AI Learning Coach.

`LearningCoach` wires together configuration, database, curriculum engine,
Gemini client, lesson engine, and Telegram client, exposing a single
`run_daily_job()` method that the scheduler (or CLI) calls once per day.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime

from ai_learning_coach.config import Settings
from ai_learning_coach.curriculum.engine import CurriculumEngine
from ai_learning_coach.database.db import Database
from ai_learning_coach.database.models import HistoryRecord, now_iso, today_iso
from ai_learning_coach.gemini.client import GeminiClient
from ai_learning_coach.lesson.engine import LessonEngine
from ai_learning_coach.telegram.client import TelegramClient
from ai_learning_coach.utils.helpers import current_weekday_name

logger = logging.getLogger(__name__)


class LearningCoach:
    """Wires together all components and runs the daily lesson job."""

    def __init__(self, settings: Settings) -> None:
        """Initialize all sub-components from validated settings.

        Args:
            settings: Loaded application settings.
        """
        self.settings = settings
        self.database = Database(settings.db_path)
        self.curriculum = CurriculumEngine(settings.curriculum_dir, self.database)
        self.gemini = GeminiClient(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            timeout=settings.gemini_timeout,
            max_retries=settings.gemini_max_retries,
        )
        self.lesson_engine = LessonEngine(self.gemini, settings.templates_dir)
        self.telegram = TelegramClient(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            max_retries=settings.telegram_max_retries,
            max_message_length=settings.telegram_max_message_length,
        )

    def run_daily_job(self, weekday: str | None = None) -> bool:
        """Run the full pipeline once: select topic, generate, publish, record.

        Args:
            weekday: Optional override weekday (mainly for CLI testing).
                Defaults to today's actual weekday.

        Returns:
            True if the lesson was generated and published successfully,
            False otherwise (the failure is logged and recorded in history).
        """
        target_weekday = (weekday or current_weekday_name()).lower()
        logger.info("Starting daily job for weekday=%s", target_weekday)
        start = time.perf_counter()

        try:
            topic = self.curriculum.get_topic_for_weekday(target_weekday)
            logger.info("Selected topic: [%s] %s", topic.lesson_id, topic.title)

            generated = self.lesson_engine.generate(topic)
            logger.info("Content generated for '%s'", generated.title)

            self.telegram.send_markdown(generated.markdown)
            logger.info("Lesson published to Telegram successfully")

            self.curriculum.mark_published(topic.lesson_id, today_iso())
            elapsed = time.perf_counter() - start

            self.database.record_history(
                HistoryRecord(
                    lesson_id=topic.lesson_id,
                    module=topic.module,
                    title=topic.title,
                    publish_date=now_iso(),
                    status="success",
                    generation_time_seconds=round(elapsed, 2),
                )
            )
            self.database.mark_last_run()
            logger.info("Daily job completed successfully in %.2fs", elapsed)
            return True

        except Exception as exc:  # noqa: BLE001 - top-level job boundary
            elapsed = time.perf_counter() - start
            logger.exception("Daily job failed: %s", exc)
            self.database.record_history(
                HistoryRecord(
                    lesson_id="unknown",
                    module=target_weekday,
                    title="N/A",
                    publish_date=now_iso(),
                    status="failure",
                    generation_time_seconds=round(elapsed, 2),
                    error_message=str(exc),
                )
            )
            return False
