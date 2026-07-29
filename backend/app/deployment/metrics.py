"""Metrics collection for the Deployment subsystem."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from app.deployment.models import DeploymentMetrics

logger = logging.getLogger(__name__)


class DeploymentMetricsCollector:
    """Collects deployment lifecycle metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._total_startups = 0
        self._total_shutdowns = 0
        self._total_health_checks = 0
        self._total_restarts = 0
        self._startup_times: list[float] = []
        self._shutdown_times: list[float] = []
        self._start_time = time.time()

    def record_startup(self, duration_ms: float = 0.0) -> None:
        with self._lock:
            self._total_startups += 1
            if duration_ms > 0:
                self._startup_times.append(duration_ms)
                if len(self._startup_times) > 1000:
                    self._startup_times = self._startup_times[-500:]

    def record_shutdown(self, duration_ms: float = 0.0) -> None:
        with self._lock:
            self._total_shutdowns += 1
            if duration_ms > 0:
                self._shutdown_times.append(duration_ms)
                if len(self._shutdown_times) > 1000:
                    self._shutdown_times = self._shutdown_times[-500:]

    def record_health_check(self) -> None:
        with self._lock:
            self._total_health_checks += 1

    def record_restart(self) -> None:
        with self._lock:
            self._total_restarts += 1

    def get_statistics(self) -> dict[str, Any]:
        with self._lock:
            avg_startup = (
                sum(self._startup_times) / len(self._startup_times)
                if self._startup_times
                else 0.0
            )
            avg_shutdown = (
                sum(self._shutdown_times) / len(self._shutdown_times)
                if self._shutdown_times
                else 0.0
            )
            return {
                "total_startups": self._total_startups,
                "total_shutdowns": self._total_shutdowns,
                "total_health_checks": self._total_health_checks,
                "total_restarts": self._total_restarts,
                "average_startup_time_ms": round(avg_startup, 2),
                "average_shutdown_time_ms": round(avg_shutdown, 2),
                "uptime_seconds": round(time.time() - self._start_time, 2),
            }

    def to_model(self) -> DeploymentMetrics:
        stats = self.get_statistics()
        return DeploymentMetrics(
            total_startups=stats["total_startups"],
            total_shutdowns=stats["total_shutdowns"],
            total_health_checks=stats["total_health_checks"],
            total_restarts=stats["total_restarts"],
            average_startup_time_ms=stats["average_startup_time_ms"],
            average_shutdown_time_ms=stats["average_shutdown_time_ms"],
            uptime_seconds=stats["uptime_seconds"],
            last_health_check=time.time() if self._total_health_checks > 0 else 0.0,
        )

    def reset(self) -> None:
        with self._lock:
            self._total_startups = 0
            self._total_shutdowns = 0
            self._total_health_checks = 0
            self._total_restarts = 0
            self._startup_times.clear()
            self._shutdown_times.clear()
            self._start_time = time.time()
