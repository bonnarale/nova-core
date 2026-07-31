"""Health checks for the Deployment subsystem."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.deployment.enums import HealthStatus
from app.deployment.models import DeploymentHealth, HealthCheck

logger = logging.getLogger(__name__)


class LivenessProbe:
    """Liveness probe — is the process alive?"""

    def __init__(self) -> None:
        self._started = False
        self._last_check: float = 0.0

    def mark_started(self) -> None:
        self._started = True

    async def check(self) -> HealthCheck:
        start = time.time()
        alive = self._started
        latency = (time.time() - start) * 1000
        self._last_check = time.time()
        return HealthCheck(
            name="liveness",
            status=HealthStatus.HEALTHY.value if alive else HealthStatus.UNHEALTHY.value,
            message="Process is alive" if alive else "Process not started",
            latency_ms=round(latency, 2),
            checked_at=self._last_check,
        )

    @property
    def is_alive(self) -> bool:
        return self._started


class StartupProbe:
    """Startup probe — has the application finished initializing?"""

    def __init__(self, timeout: float = 60.0) -> None:
        self._timeout = timeout
        self._started_at: float = 0.0
        self._completed_at: float = 0.0
        self._checks: list[dict[str, Any]] = []

    async def start(self) -> None:
        self._started_at = time.time()

    async def complete(self) -> None:
        self._completed_at = time.time()

    async def check(self) -> HealthCheck:
        start = time.time()
        elapsed = time.time() - self._started_at if self._started_at else 0.0
        completed = self._completed_at > 0.0
        timed_out = not completed and elapsed > self._timeout
        latency = (time.time() - start) * 1000

        if completed:
            status = HealthStatus.HEALTHY.value
            message = "Startup completed"
        elif timed_out:
            status = HealthStatus.UNHEALTHY.value
            message = f"Startup timed out after {self._timeout}s"
        else:
            status = HealthStatus.DEGRADED.value
            message = f"Startup in progress ({elapsed:.1f}s)"

        return HealthCheck(
            name="startup",
            status=status,
            message=message,
            latency_ms=round(latency, 2),
        )

    def add_check(self, name: str, passed: bool, message: str = "") -> None:
        self._checks.append({
            "name": name,
            "passed": passed,
            "message": message,
        })

    @property
    def is_complete(self) -> bool:
        return self._completed_at > 0.0


class ReadinessProbe:
    """Readiness probe — can the application serve traffic?"""

    def __init__(self) -> None:
        self._checks: dict[str, bool] = {}
        self._last_check: float = 0.0

    def register_check(self, name: str, healthy: bool) -> None:
        self._checks[name] = healthy

    def remove_check(self, name: str) -> bool:
        if name in self._checks:
            del self._checks[name]
            return True
        return False

    async def check(self) -> HealthCheck:
        start = time.time()
        all_healthy = all(self._checks.values()) if self._checks else True
        latency = (time.time() - start) * 1000
        self._last_check = time.time()
        return HealthCheck(
            name="readiness",
            status=HealthStatus.HEALTHY.value if all_healthy else HealthStatus.DEGRADED.value,
            message="Ready" if all_healthy else "Not ready",
            latency_ms=round(latency, 2),
            checked_at=self._last_check,
        )

    @property
    def is_ready(self) -> bool:
        return all(self._checks.values()) if self._checks else True
