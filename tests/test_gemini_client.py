"""Unit tests for ai_learning_coach.gemini.client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from ai_learning_coach.gemini.client import GeminiClient, GeminiError


def _mock_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data or {}
    if status_code >= 400:
        mock.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status_code}")
    else:
        mock.raise_for_status.return_value = None
    return mock


def test_generate_success() -> None:
    client = GeminiClient(api_key="fake-key", max_retries=1)
    payload = {"candidates": [{"content": {"parts": [{"text": "Hello world"}]}}]}

    with patch("ai_learning_coach.gemini.client.requests.post", return_value=_mock_response(200, payload)):
        result = client.generate("test prompt")

    assert result == "Hello world"


def test_generate_raises_after_retries_exhausted() -> None:
    client = GeminiClient(api_key="fake-key", max_retries=2)

    with patch("ai_learning_coach.gemini.client.requests.post", side_effect=requests.ConnectionError("boom")):
        with patch("ai_learning_coach.gemini.client.time.sleep"):
            with pytest.raises(GeminiError):
                client.generate("test prompt")


def test_extract_text_raises_on_malformed_response() -> None:
    with pytest.raises(GeminiError):
        GeminiClient._extract_text({"unexpected": "shape"})


def test_extract_text_raises_on_empty_text() -> None:
    with pytest.raises(GeminiError):
        GeminiClient._extract_text(
            {"candidates": [{"content": {"parts": [{"text": "   "}]}}]}
        )


def test_rate_limit_triggers_retry_then_succeeds() -> None:
    client = GeminiClient(api_key="fake-key", max_retries=2)
    payload = {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}

    responses = [_mock_response(429, {}), _mock_response(200, payload)]
    with patch("ai_learning_coach.gemini.client.requests.post", side_effect=responses):
        with patch("ai_learning_coach.gemini.client.time.sleep"):
            result = client.generate("prompt")

    assert result == "ok"
