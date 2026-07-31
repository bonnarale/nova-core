"""Graceful shutdown for the Deployment subsystem."""

from __future__ import annotations

import logging
import signal
import time
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

ShutdownHandler = Callable[[], Coroutine[Any, Any, None]]


class GracefulShutdown:
    """Manages graceful shutdown with ordered handler execution."""

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout
        self._handlers: list[tuple[str, ShutdownHandler]] = []
        self._shutting_down = False
        self._completed: list[str] = []
        self._failed: list[str] = []
        self._start_time: float = 0.0
        self._end_time: float = 0.0

    @property
    def is_shutting_down(self) -> bool:
        return self._shutting_down

    @property
    def duration_ms(self) -> float:
        if self._start_time == 0.0:
            return 0.0
        end = self._end_time if self._end_time > 0.0 else time.time()
        return round((end - self._start_time) * 1000, 2)

    def register_handler(self, name: str, handler: ShutdownHandler) -> None:
        self._handlers.append((name, handler))
        logger.debug("Shutdown handler registered: %s", name)

    async def execute(self) -> dict[str, Any]:
        self._shutting_down = True
        self._start_time = time.time()
        self._completed.clear()
        self._failed.clear()
        logger.info("Graceful shutdown initiated (timeout=%.1fs)", self._timeout)

        for name, handler in self._handlers:
            try:
                await handler()
                self._completed.append(name)
                logger.debug("Shutdown handler completed: %s", name)
            except Exception as exc:
                self._failed.append(name)
                logger.error("Shutdown handler failed: %s — %s", name, exc)

        self._shutting_down = False
        self._end_time = time.time()

        return {
            "completed": list(self._completed),
            "failed": list(self._failed),
            "duration_ms": self.duration_ms,
            "handlers_total": len(self._handlers),
        }

    def get_status(self) -> dict[str, Any]:
        return {
            "shutting_down": self._shutting_down,
            "handlers_registered": len(self._handlers),
            "completed": list(self._completed),
            "failed": list(self._failed),
            "timeout_seconds": self._timeout,
            "duration_ms": self.duration_ms,
        }
