"""Logging configuration for AI Learning Coach.

Provides a single `setup_logging` entry point that configures a rotating
file handler plus a console handler. All other modules simply call
`logging.getLogger(__name__)`.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_dir: Path, level: str = "INFO", filename: str = "ai_learning_coach.log") -> None:
    """Configure root logging with rotating file + console handlers.

    Args:
        log_dir: Directory in which to store log files (created if missing).
        level: Logging level name, e.g. "INFO" or "DEBUG".
        filename: Log file name within `log_dir`.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / filename

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers if setup_logging is called more than once.
    root_logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    file_handler = RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(numeric_level)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(numeric_level)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Quiet down noisy third-party loggers unless DEBUG is explicitly requested.
    if numeric_level > logging.DEBUG:
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("apscheduler").setLevel(logging.WARNING)
