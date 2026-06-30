"""APScheduler integration for AI Learning Coach.

`CoachScheduler` schedules `LearningCoach.run_daily_job` to run once per day
at the configured local time, and blocks the main thread until interrupted.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from ai_learning_coach.coach import LearningCoach
from ai_learning_coach.config import Settings

logger = logging.getLogger(__name__)


class CoachScheduler:
    """Schedules and runs the daily AI Learning Coach job via APScheduler."""

    def __init__(self, coach: LearningCoach, settings: Settings) -> None:
        """Initialize the scheduler.

        Args:
            coach: The `LearningCoach` orchestrator to invoke daily.
            settings: Application settings (timezone, lesson time).
        """
        self.coach = coach
        self.settings = settings
        self.scheduler = BlockingScheduler(timezone=settings.timezone)

    def _job(self) -> None:
        """Wrapper job function registered with APScheduler."""
        logger.info("Scheduled trigger fired — running daily job")
        success = self.coach.run_daily_job()
        if not success:
            logger.error("Scheduled daily job reported failure — see logs above")

    def start(self) -> None:
        """Register the daily cron trigger and start blocking the process."""
        trigger = CronTrigger(
            hour=self.settings.lesson_hour,
            minute=self.settings.lesson_minute,
            timezone=self.settings.timezone,
        )
        self.scheduler.add_job(
            self._job,
            trigger=trigger,
            id="daily_lesson_job",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        logger.info(
            "Scheduler started — daily lesson will publish at %02d:%02d %s",
            self.settings.lesson_hour,
            self.settings.lesson_minute,
            self.settings.timezone,
        )
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped by user/system")
