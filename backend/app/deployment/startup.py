"""Startup probe for the Deployment subsystem."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class StartupProbe:
    """Checks whether the application has successfully started."""

    def __init__(self, timeout: float = 60.0) -> None:
        self._timeout = timeout
        self._started_at: float = 0.0
        self._completed_at: float = 0.0
        self._checks: list[dict[str, Any]] = []
        self._started = False

    async def start(self) -> None:
        self._started_at = time.time()
        self._started = True
        logger.info("Startup probe initiated")

    async def complete(self) -> None:
        self._completed_at = time.time()
        logger.info(
            "Startup probe completed in %.2fms",
            (self._completed_at - self._started_at) * 1000,
        )

    async def check(self) -> dict[str, Any]:
        if not self._started:
            return {
                "status": "not_started",
                "started": False,
                "completed": False,
            }
        elapsed = time.time() - self._started_at
        timed_out = elapsed > self._timeout
        completed = self._completed_at > 0.0
        return {
            "status": "completed" if completed else ("timed_out" if timed_out else "in_progress"),
            "started": True,
            "completed": completed,
            "elapsed_seconds": round(elapsed, 2),
            "timeout_seconds": self._timeout,
            "checks": len(self._checks),
        }

    def add_check(self, name: str, passed: bool, message: str = "") -> None:
        self._checks.append({
            "name": name,
            "passed": passed,
            "message": message,
            "timestamp": time.time(),
        })

    @property
    def is_complete(self) -> bool:
        return self._completed_at > 0.0

    @property
    def is_healthy(self) -> bool:
        if not self._started:
            return False
        if self._completed_at > 0.0:
            return all(c["passed"] for c in self._checks) if self._checks else True
        elapsed = time.time() - self._started_at
        return elapsed <= self._timeout
