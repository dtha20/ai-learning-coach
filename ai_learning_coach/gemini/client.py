"""Gemini API client for AI Learning Coach.

Wraps the Google Gemini "generateContent" REST endpoint with retry logic,
timeouts, and clean error handling. This client only ever generates
*content* for a topic chosen by the curriculum engine — it never decides
what topics to teach.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiError(RuntimeError):
    """Raised when the Gemini API fails after all retries are exhausted."""


class GeminiClient:
    """Minimal REST client for Google's Gemini `generateContent` API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        timeout: int = 60,
        max_retries: int = 3,
    ) -> None:
        """Initialize the Gemini client.

        Args:
            api_key: Gemini API key.
            model: Model name, e.g. "gemini-2.5-flash".
            timeout: Per-request HTTP timeout in seconds.
            max_retries: Maximum number of retry attempts on transient failure.
        """
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_output_tokens: int = 4096,
    ) -> str:
        """Generate text content from a prompt, with retries on failure.

        Args:
            prompt: The full prompt text to send to Gemini.
            temperature: Sampling temperature (higher = more creative).
            max_output_tokens: Maximum tokens in the generated response.

        Returns:
            The generated text content.

        Raises:
            GeminiError: If the request fails after all retry attempts.
        """
        url = f"{GEMINI_API_BASE}/{self.model}:generateContent"
        params = {"key": self.api_key}
        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            },
        }

        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug("Gemini request attempt %d/%d", attempt, self.max_retries)
                response = requests.post(
                    url, params=params, json=payload, timeout=self.timeout
                )
                if response.status_code == 429:
                    wait = min(2**attempt, 30)
                    logger.warning("Gemini rate-limited (429). Backing off %ds", wait)
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                data = response.json()
                return self._extract_text(data)
            except (requests.RequestException, GeminiError) as exc:
                last_error = exc
                wait = min(2**attempt, 30)
                logger.warning(
                    "Gemini request failed (attempt %d/%d): %s — retrying in %ds",
                    attempt,
                    self.max_retries,
                    exc,
                    wait,
                )
                time.sleep(wait)

        raise GeminiError(
            f"Gemini API failed after {self.max_retries} attempts: {last_error}"
        )

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        """Extract the generated text from a Gemini API JSON response.

        Args:
            data: Parsed JSON response body.

        Returns:
            The concatenated text of the first candidate's parts.

        Raises:
            GeminiError: If the response has no usable candidates/text.
        """
        try:
            candidates = data["candidates"]
            parts = candidates[0]["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts)
        except (KeyError, IndexError, TypeError) as exc:
            raise GeminiError(f"Unexpected Gemini response shape: {data}") from exc

        if not text.strip():
            raise GeminiError("Gemini returned an empty response")
        return text.strip()
