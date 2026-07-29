from __future__ import annotations

import asyncio
import time
from typing import Any, Callable


class RetryHandler:
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 30.0,
        backoff: float = 2.0,
        retryable_status_codes: set[int] | None = None,
    ) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff = backoff
        self.retryable_status_codes = retryable_status_codes or {429, 500, 502, 503, 504}

    def calculate_delay(self, attempt: int, retry_after: float | None = None) -> float:
        if retry_after is not None:
            return retry_after
        delay = self.base_delay * (self.backoff ** attempt)
        return min(delay, self.max_delay)

    def should_retry(self, attempt: int, status_code: int | None) -> bool:
        if attempt >= self.max_retries:
            return False
        if status_code is None:
            return True
        return status_code in self.retryable_status_codes

    async def execute_with_retry(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        last_exception: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                last_exception = exc
                if not self.should_retry(attempt, getattr(exc, "status_code", None)):
                    raise
                delay = self.calculate_delay(attempt, getattr(exc, "retry_after", None))
                await asyncio.sleep(delay)
        raise last_exception  # type: ignore[misc]

    def execute_sync(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        last_exception: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                last_exception = exc
                if not self.should_retry(attempt, getattr(exc, "status_code", None)):
                    raise
                delay = self.calculate_delay(attempt, getattr(exc, "retry_after", None))
                time.sleep(delay)
        raise last_exception  # type: ignore[misc]
