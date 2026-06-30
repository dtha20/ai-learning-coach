"""Generic utility helpers used across AI Learning Coach modules."""

from __future__ import annotations

import time
from datetime import datetime
from functools import wraps
from typing import Callable, TypeVar

T = TypeVar("T")

WEEKDAY_NAMES = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def current_weekday_name(now: datetime | None = None) -> str:
    """Return the lowercase weekday name for the given (or current) datetime.

    Args:
        now: Optional datetime to use instead of the current time (useful
            for testing). Defaults to `datetime.now()`.

    Returns:
        Lowercase weekday name, e.g. "monday".
    """
    moment = now or datetime.now()
    return WEEKDAY_NAMES[moment.weekday()]


def timed(func: Callable[..., T]) -> Callable[..., tuple[T, float]]:
    """Decorator that returns (result, elapsed_seconds) instead of just result.

    Args:
        func: The function to wrap.

    Returns:
        A wrapped function returning a tuple of (original_result, elapsed_seconds).
    """

    @wraps(func)
    def wrapper(*args: object, **kwargs: object) -> tuple[T, float]:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        return result, elapsed

    return wrapper
