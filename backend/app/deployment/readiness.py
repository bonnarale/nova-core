"""Readiness checker for the Deployment subsystem."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.deployment.base import HealthProvider

logger = logging.getLogger(__name__)


class ReadinessChecker(HealthProvider):
    """Checks whether the application is ready to accept traffic."""

    def __init__(self) -> None:
        self._checks: dict[str, bool] = {}
        self._check_results: dict[str, dict[str, Any]] = {}
        self._last_check: float = 0.0

    async def check_startup(self) -> dict[str, Any]:
        return {
            "status": "ready",
            "timestamp": time.time(),
        }

    async def check_readiness(self) -> dict[str, Any]:
        start = time.time()
        all_healthy = all(self._checks.values()) if self._checks else True
        latency = (time.time() - start) * 1000
        self._last_check = time.time()
        return {
            "status": "ready" if all_healthy else "not_ready",
            "ready": all_healthy,
            "checks": dict(self._checks),
            "details": dict(self._check_results),
            "latency_ms": round(latency, 2),
            "timestamp": self._last_check,
        }

    async def check_liveness(self) -> dict[str, Any]:
        return {
            "status": "alive",
            "alive": True,
            "timestamp": time.time(),
        }

    async def check_all(self) -> dict[str, Any]:
        startup = await self.check_startup()
        readiness = await self.check_readiness()
        liveness = await self.check_liveness()
        return {
            "startup": startup,
            "readiness": readiness,
            "liveness": liveness,
        }

    def register_check(self, name: str, healthy: bool, details: dict[str, Any] | None = None) -> None:
        self._checks[name] = healthy
        self._check_results[name] = details or {"healthy": healthy}

    def remove_check(self, name: str) -> bool:
        if name in self._checks:
            del self._checks[name]
            self._check_results.pop(name, None)
            return True
        return False

    @property
    def is_ready(self) -> bool:
        return all(self._checks.values()) if self._checks else True

    @property
    def last_check(self) -> float:
        return self._last_check
