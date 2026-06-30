"""Unit tests for ai_learning_coach.telegram.client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from ai_learning_coach.telegram.client import TelegramClient, TelegramError


def _mock_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data if json_data is not None else {"ok": True}
    mock.raise_for_status.return_value = None
    return mock


def test_send_markdown_single_chunk() -> None:
    client = TelegramClient(bot_token="fake", chat_id="123", max_retries=1)
    with patch(
        "ai_learning_coach.telegram.client.requests.post", return_value=_mock_response(200, {"ok": True})
    ) as mock_post:
        client.send_markdown("hello world")
    assert mock_post.call_count == 1


def test_split_message_respects_limit() -> None:
    client = TelegramClient(bot_token="fake", chat_id="123", max_message_length=50)
    text = "\n\n".join(["paragraph " + str(i) * 10 for i in range(10)])
    chunks = client._split_message(text)
    assert all(len(chunk) <= 50 for chunk in chunks)
    assert len(chunks) > 1


def test_send_markdown_raises_after_retries_exhausted() -> None:
    client = TelegramClient(bot_token="fake", chat_id="123", max_retries=2)
    with patch(
        "ai_learning_coach.telegram.client.requests.post",
        side_effect=requests.ConnectionError("network down"),
    ):
        with patch("ai_learning_coach.telegram.client.time.sleep"):
            with pytest.raises(TelegramError):
                client.send_markdown("hello")


def test_telegram_api_error_response_raises() -> None:
    client = TelegramClient(bot_token="fake", chat_id="123", max_retries=1)
    with patch(
        "ai_learning_coach.telegram.client.requests.post",
        return_value=_mock_response(200, {"ok": False, "description": "bad request"}),
    ):
        with patch("ai_learning_coach.telegram.client.time.sleep"):
            with pytest.raises(TelegramError):
                client.send_markdown("hello")


def test_rate_limit_retries_then_succeeds() -> None:
    client = TelegramClient(bot_token="fake", chat_id="123", max_retries=2)
    rate_limited = _mock_response(429, {"parameters": {"retry_after": 0}})
    success = _mock_response(200, {"ok": True})

    with patch(
        "ai_learning_coach.telegram.client.requests.post", side_effect=[rate_limited, success]
    ):
        with patch("ai_learning_coach.telegram.client.time.sleep"):
            client.send_markdown("hello")
