"""Timeout management."""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any, Callable, Coroutine


class TimeoutManager:
    """Configurable timeouts for different operation types."""

    _DEFAULT_TIMEOUTS: dict[str, float] = {
        "api_request": 30.0,
        "llm_call": 120.0,
        "tool_execution": 60.0,
        "workflow_execution": 300.0,
        "scheduler_job": 120.0,
        "database_operation": 15.0,
        "event_processing": 10.0,
    }

    def __init__(self) -> None:
        self._timeouts = dict(self._DEFAULT_TIMEOUTS)
        self._events: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def set_timeout(self, operation: str, timeout: float) -> None:
        with self._lock:
            self._timeouts[operation] = timeout

    def get_timeout(self, operation: str) -> float:
        with self._lock:
            return self._timeouts.get(operation, 30.0)

    async def execute(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        timeout: float | None = None,
        operation: str = "default",
        **kwargs: Any,
    ) -> Any:
        effective_timeout = timeout or self.get_timeout(operation)
        try:
            result = await asyncio.wait_for(func(*args, **kwargs), timeout=effective_timeout)
            return result
        except asyncio.TimeoutError:
            with self._lock:
                self._events.append({
                    "operation": operation,
                    "timeout": effective_timeout,
                    "timestamp": time.time(),
                })
            raise

    def get_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._events[-limit:])

    def get_all_timeouts(self) -> dict[str, float]:
        with self._lock:
            return dict(self._timeouts)

    def reset(self) -> None:
        with self._lock:
            self._timeouts = dict(self._DEFAULT_TIMEOUTS)
            self._events.clear()
