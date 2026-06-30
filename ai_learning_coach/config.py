"""Configuration management for AI Learning Coach.

Loads and validates all runtime configuration from environment variables
(via a `.env` file in the project root). Centralizing configuration here
means no other module ever touches `os.environ` directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Resolve project root (one level up from this file: ai_learning_coach/config.py -> root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

# Load .env if present (does not override real environment variables)
load_dotenv(dotenv_path=ENV_PATH, override=False)


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def _require(name: str) -> str:
    """Fetch a required environment variable or raise ConfigError.

    Args:
        name: Environment variable name.

    Returns:
        The variable's string value.

    Raises:
        ConfigError: If the variable is unset or empty.
    """
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(
            f"Missing required environment variable '{name}'. "
            f"Set it in your .env file (see .env.example)."
        )
    return value


def _optional(name: str, default: str) -> str:
    """Fetch an optional environment variable with a default fallback."""
    value = os.environ.get(name, "").strip()
    return value if value else default


@dataclass(frozen=True)
class Settings:
    """Immutable application settings, loaded once at startup.

    Attributes:
        gemini_api_key: API key for Google Gemini.
        gemini_model: Gemini model identifier to use for generation.
        telegram_bot_token: Telegram bot token.
        telegram_chat_id: Target chat/group/channel ID for posting lessons.
        timezone: IANA timezone string used by the scheduler (e.g. "Europe/Rome").
        lesson_time: Daily publish time in 24h "HH:MM" format.
        db_path: Filesystem path to the SQLite database file.
        log_dir: Directory where rotating log files are stored.
        log_level: Logging level name ("INFO" or "DEBUG").
        curriculum_dir: Directory containing curriculum JSON files.
        templates_dir: Directory containing Jinja2 lesson templates.
        gemini_timeout: HTTP timeout (seconds) for Gemini API requests.
        gemini_max_retries: Max retry attempts for Gemini API calls.
        telegram_max_retries: Max retry attempts for Telegram API calls.
        telegram_max_message_length: Telegram hard message-length limit.
    """

    gemini_api_key: str
    gemini_model: str
    telegram_bot_token: str
    telegram_chat_id: str
    timezone: str
    lesson_time: str
    db_path: Path
    log_dir: Path
    log_level: str
    curriculum_dir: Path
    templates_dir: Path
    gemini_timeout: int = 60
    gemini_max_retries: int = 3
    telegram_max_retries: int = 3
    telegram_max_message_length: int = 4096

    @property
    def lesson_hour(self) -> int:
        """Hour component (0-23) parsed from `lesson_time`."""
        return int(self.lesson_time.split(":")[0])

    @property
    def lesson_minute(self) -> int:
        """Minute component (0-59) parsed from `lesson_time`."""
        return int(self.lesson_time.split(":")[1])


def load_settings() -> Settings:
    """Load and validate all application settings from the environment.

    Returns:
        A populated, validated `Settings` instance.

    Raises:
        ConfigError: If required variables are missing or malformed.
    """
    lesson_time = _optional("LESSON_TIME", "08:00")
    if ":" not in lesson_time:
        raise ConfigError("LESSON_TIME must be in HH:MM format, e.g. 08:00")

    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        gemini_api_key=_require("GEMINI_API_KEY"),
        gemini_model=_optional("GEMINI_MODEL", "gemini-2.5-flash"),
        telegram_bot_token=_require("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_require("TELEGRAM_CHAT_ID"),
        timezone=_optional("TIMEZONE", "UTC"),
        lesson_time=lesson_time,
        db_path=Path(_optional("DB_PATH", str(data_dir / "learning_coach.db"))),
        log_dir=Path(_optional("LOG_DIR", str(log_dir))),
        log_level=_optional("LOG_LEVEL", "INFO").upper(),
        curriculum_dir=Path(
            _optional("CURRICULUM_DIR", str(PROJECT_ROOT / "ai_learning_coach" / "curriculum" / "data"))
        ),
        templates_dir=Path(
            _optional("TEMPLATES_DIR", str(PROJECT_ROOT / "ai_learning_coach" / "lesson" / "templates"))
        ),
        gemini_timeout=int(_optional("GEMINI_TIMEOUT", "60")),
        gemini_max_retries=int(_optional("GEMINI_MAX_RETRIES", "3")),
        telegram_max_retries=int(_optional("TELEGRAM_MAX_RETRIES", "3")),
    )
