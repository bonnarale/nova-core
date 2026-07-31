"""Observability health — health checks for the observability subsystem and dependencies."""

from __future__ import annotations

import time
from typing import Any

from app.observability.models import HealthCheck, HealthStatus
from app.observability.lifecycle import ObservabilityLifecycle, ObservabilityLifecycleState


class HealthChecker:
    """Health check system — readiness, liveness, startup, dependency health."""

    def __init__(self, lifecycle: ObservabilityLifecycle | None = None) -> None:
        self._lifecycle = lifecycle or ObservabilityLifecycle()
        self._checks: dict[str, HealthCheck] = {}
        self._dependency_health: dict[str, HealthCheck] = {}
        self._started_at = time.monotonic()

    def register_check(self, name: str, check: HealthCheck) -> None:
        self._checks[name] = check

    def unregister_check(self, name: str) -> bool:
        return self._checks.pop(name, None) is not None

    def register_dependency(self, name: str, check: HealthCheck) -> None:
        self._dependency_health[name] = check

    def unregister_dependency(self, name: str) -> bool:
        return self._dependency_health.pop(name, None) is not None

    async def check_readiness(self) -> dict[str, Any]:
        state = self._lifecycle.state
        ready = state in (
            ObservabilityLifecycleState.READY,
            ObservabilityLifecycleState.RUNNING,
        )
        return {
            "status": "ok" if ready else "not ready",
            "ready": ready,
            "lifecycle_state": state.value,
            "checks": {name: c.to_dict() for name, c in self._checks.items()},
        }

    async def check_liveness(self) -> dict[str, Any]:
        state = self._lifecycle.state
        alive = state != ObservabilityLifecycleState.SHUTDOWN
        return {
            "status": "ok" if alive else "not alive",
            "alive": alive,
            "uptime_seconds": time.monotonic() - self._started_at,
            "lifecycle_state": state.value,
        }

    async def check_startup(self) -> dict[str, Any]:
        state = self._lifecycle.state
        started = state in (
            ObservabilityLifecycleState.READY,
            ObservabilityLifecycleState.RUNNING,
            ObservabilityLifecycleState.DEGRADED,
        )
        return {
            "status": "ok" if started else "not started",
            "started": started,
            "lifecycle_state": state.value,
        }

    async def get_dependency_health(self) -> dict[str, Any]:
        return {name: c.to_dict() for name, c in self._dependency_health.items()}

    def get_all_checks(self) -> dict[str, HealthCheck]:
        return dict(self._checks)

    def clear_checks(self) -> int:
        count = len(self._checks)
        self._checks.clear()
        return count

    def clear_dependencies(self) -> int:
        count = len(self._dependency_health)
        self._dependency_health.clear()
        return count

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": {name: c.to_dict() for name, c in self._checks.items()},
            "dependencies": {name: c.to_dict() for name, c in self._dependency_health.items()},
        }
