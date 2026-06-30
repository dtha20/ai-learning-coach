"""Command-line entrypoint for AI Learning Coach.

Usage:
    python -m ai_learning_coach.main run [--weekday monday]   # run once, immediately
    python -m ai_learning_coach.main schedule                  # start the daemon scheduler
    python -m ai_learning_coach.main history [--limit 10]      # show recent publish history
"""

from __future__ import annotations

import argparse
import logging
import sys

from ai_learning_coach.coach import LearningCoach
from ai_learning_coach.config import ConfigError, load_settings
from ai_learning_coach.logger import setup_logging
from ai_learning_coach.scheduler.scheduler import CoachScheduler

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        Configured `argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        prog="ai-learning-coach",
        description="Generate and publish daily AI/IT lessons to Telegram.",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Force DEBUG logging regardless of LOG_LEVEL."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the daily job immediately (for testing/cron).")
    run_parser.add_argument(
        "--weekday",
        choices=[
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ],
        default=None,
        help="Override the weekday module to run (defaults to today).",
    )

    subparsers.add_parser("schedule", help="Start the long-running daily scheduler.")

    history_parser = subparsers.add_parser("history", help="Show recent publish history.")
    history_parser.add_argument("--limit", type=int, default=10, help="Number of records to show.")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint.

    Args:
        argv: Optional argument list (defaults to `sys.argv[1:]`).

    Returns:
        Process exit code (0 = success, 1 = failure).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    log_level = "DEBUG" if args.debug else settings.log_level
    setup_logging(settings.log_dir, level=log_level)

    coach = LearningCoach(settings)

    if args.command == "run":
        success = coach.run_daily_job(weekday=args.weekday)
        return 0 if success else 1

    if args.command == "schedule":
        scheduler = CoachScheduler(coach, settings)
        scheduler.start()
        return 0

    if args.command == "history":
        records = coach.database.get_recent_history(limit=args.limit)
        if not records:
            print("No history yet.")
            return 0
        for record in records:
            status_icon = "✅" if record.status == "success" else "❌"
            print(
                f"{status_icon} {record.publish_date} | {record.module} | "
                f"{record.title} | {record.generation_time_seconds}s"
                + (f" | error: {record.error_message}" if record.error_message else "")
            )
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
