"""Health guard — continuous monitoring of critical subsystems."""

from __future__ import annotations

import threading
import time
from typing import Any

from app.resilience.enums import HealthStatus


class HealthGuard:
    """Continuously monitors critical subsystems and triggers recovery."""

    def __init__(self) -> None:
        self._checks: dict[str, dict[str, Any]] = {}
        self._results: dict[str, str] = {}
        self._interventions: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def register_check(self, name: str, check_fn: Any = None, interval: float = 30.0) -> None:
        with self._lock:
            self._checks[name] = {"check_fn": check_fn, "interval": interval, "last_check": 0.0}

    def unregister_check(self, name: str) -> None:
        with self._lock:
            self._checks.pop(name, None)
            self._results.pop(name, None)

    def run_check(self, name: str, healthy: bool = True, message: str = "") -> str:
        status = HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY
        with self._lock:
            self._results[name] = status.value
            if not healthy:
                self._interventions.append({
                    "component": name,
                    "status": status.value,
                    "message": message,
                    "timestamp": time.time(),
                })
        return status.value

    def get_status(self, name: str) -> str:
        with self._lock:
            return self._results.get(name, HealthStatus.UNKNOWN.value)

    def get_all_status(self) -> dict[str, str]:
        with self._lock:
            return dict(self._results)

    def get_interventions(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._interventions[-limit:])

    def is_healthy(self) -> bool:
        with self._lock:
            return all(s == HealthStatus.HEALTHY.value for s in self._results.values())

    def get_summary(self) -> dict[str, Any]:
        with self._lock:
            healthy = sum(1 for s in self._results.values() if s == HealthStatus.HEALTHY.value)
            unhealthy = sum(1 for s in self._results.values() if s == HealthStatus.UNHEALTHY.value)
            return {
                "total_checks": len(self._checks),
                "healthy": healthy,
                "unhealthy": unhealthy,
                "total_interventions": len(self._interventions),
            }
