"""Telegram Bot API client for AI Learning Coach.

Handles sending Markdown-formatted lesson messages to a Telegram group/chat,
including automatic message splitting (Telegram's 4096-char limit), rate
limit (429) handling, and retries on transient errors.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot"


class TelegramError(RuntimeError):
    """Raised when sending a Telegram message fails after all retries."""


class TelegramClient:
    """Minimal REST client for the Telegram Bot `sendMessage` API."""

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        max_retries: int = 3,
        max_message_length: int = 4096,
        timeout: int = 30,
    ) -> None:
        """Initialize the Telegram client.

        Args:
            bot_token: Telegram bot token from @BotFather.
            chat_id: Target chat/group/channel ID (or @username for channels).
            max_retries: Maximum retry attempts per message chunk.
            max_message_length: Telegram's hard per-message character limit.
            timeout: Per-request HTTP timeout in seconds.
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.max_retries = max_retries
        self.max_message_length = max_message_length
        self.timeout = timeout
        self._base_url = f"{TELEGRAM_API_BASE}{self.bot_token}"

    def send_markdown(self, text: str) -> None:
        """Send a Markdown-formatted message, splitting it if too long.

        Args:
            text: Markdown-formatted message body.

        Raises:
            TelegramError: If any chunk fails to send after all retries.
        """
        chunks = self._split_message(text)
        logger.info("Sending lesson to Telegram in %d chunk(s)", len(chunks))
        for index, chunk in enumerate(chunks, start=1):
            self._send_single(chunk)
            logger.debug("Sent chunk %d/%d", index, len(chunks))

    def _split_message(self, text: str) -> list[str]:
        """Split text into chunks that respect Telegram's length limit.

        Splits on paragraph boundaries where possible to avoid breaking
        Markdown formatting mid-element.

        Args:
            text: Full message text.

        Returns:
            A list of message chunks, each within `max_message_length`.
        """
        limit = self.max_message_length
        if len(text) <= limit:
            return [text]

        chunks: list[str] = []
        paragraphs = text.split("\n\n")
        current = ""
        for paragraph in paragraphs:
            candidate = f"{current}\n\n{paragraph}" if current else paragraph
            if len(candidate) <= limit:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                # If a single paragraph itself exceeds the limit, hard-split it.
                if len(paragraph) > limit:
                    for i in range(0, len(paragraph), limit):
                        chunks.append(paragraph[i : i + limit])
                    current = ""
                else:
                    current = paragraph
        if current:
            chunks.append(current)
        return chunks

    def _send_single(self, text: str) -> None:
        """Send a single message chunk, retrying on transient failures.

        Args:
            text: A single chunk of text within the length limit.

        Raises:
            TelegramError: If the chunk fails to send after all retries.
        """
        url = f"{self._base_url}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(url, json=payload, timeout=self.timeout)
                if response.status_code == 429:
                    retry_after = response.json().get("parameters", {}).get("retry_after", 5)
                    logger.warning("Telegram rate-limited. Waiting %ss", retry_after)
                    time.sleep(float(retry_after))
                    continue
                if response.status_code >= 500:
                    raise TelegramError(f"Telegram server error: {response.status_code}")
                response.raise_for_status()
                body = response.json()
                if not body.get("ok", False):
                    raise TelegramError(f"Telegram API returned error: {body}")
                return
            except (requests.RequestException, TelegramError) as exc:
                last_error = exc
                wait = min(2**attempt, 30)
                logger.warning(
                    "Telegram send failed (attempt %d/%d): %s — retrying in %ds",
                    attempt,
                    self.max_retries,
                    exc,
                    wait,
                )
                time.sleep(wait)

        raise TelegramError(
            f"Failed to send Telegram message after {self.max_retries} attempts: {last_error}"
        )
