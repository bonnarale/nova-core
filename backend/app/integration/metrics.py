"""Integration metrics collection."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)


class IntegrationMetrics:
    """Snapshot of integration metrics."""

    __slots__ = (
        "registered_components",
        "startup_time",
        "initialization_failures",
        "integration_failures",
        "dependency_resolution_time",
        "uptime_seconds",
    )

    def __init__(
        self,
        registered_components: int = 0,
        startup_time: float = 0.0,
        initialization_failures: int = 0,
        integration_failures: int = 0,
        dependency_resolution_time: float = 0.0,
        uptime_seconds: float = 0.0,
    ) -> None:
        self.registered_components = registered_components
        self.startup_time = startup_time
        self.initialization_failures = initialization_failures
        self.integration_failures = integration_failures
        self.dependency_resolution_time = dependency_resolution_time
        self.uptime_seconds = uptime_seconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "registered_components": self.registered_components,
            "startup_time": self.startup_time,
            "initialization_failures": self.initialization_failures,
            "integration_failures": self.integration_failures,
            "dependency_resolution_time": self.dependency_resolution_time,
            "uptime_seconds": self.uptime_seconds,
        }


class IntegrationMetricsCollector:
    """Collects and tracks integration metrics."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._start_time: float = 0.0
        self._startup_time: float = 0.0
        self._initialization_failures: int = 0
        self._integration_failures: int = 0
        self._dependency_resolution_time: float = 0.0

    def start(self) -> None:
        with self._lock:
            self._start_time = time.time()

    def record_startup(self, duration: float) -> None:
        with self._lock:
            self._startup_time = duration

    def record_initialization_failure(self) -> None:
        with self._lock:
            self._initialization_failures += 1

    def record_integration_failure(self) -> None:
        with self._lock:
            self._integration_failures += 1

    def record_dependency_resolution(self, duration: float) -> None:
        with self._lock:
            self._dependency_resolution_time = duration

    def snapshot(self, registered_components: int = 0) -> IntegrationMetrics:
        with self._lock:
            uptime = time.time() - self._start_time if self._start_time else 0.0
            return IntegrationMetrics(
                registered_components=registered_components,
                startup_time=self._startup_time,
                initialization_failures=self._initialization_failures,
                integration_failures=self._integration_failures,
                dependency_resolution_time=self._dependency_resolution_time,
                uptime_seconds=uptime,
            )
