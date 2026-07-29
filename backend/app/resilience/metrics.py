"""Resilience metrics collection."""

from __future__ import annotations

import threading
import time
from typing import Any


class ResilienceMetrics:
    """Snapshot of resilience metrics."""

    __slots__ = (
        "retries", "circuit_breaker_trips", "failovers", "recoveries",
        "timeouts", "degraded_operations", "watchdog_interventions", "uptime_seconds",
    )

    def __init__(self, **kwargs: Any) -> None:
        for slot in self.__slots__:
            setattr(self, slot, kwargs.get(slot, 0))

    def to_dict(self) -> dict[str, Any]:
        return {slot: getattr(self, slot) for slot in self.__slots__}


class ResilienceMetricsCollector:
    """Thread-safe collector for resilience metrics."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._retries = 0
        self._cb_trips = 0
        self._failovers = 0
        self._recoveries = 0
        self._timeouts = 0
        self._degraded = 0
        self._watchdog_interventions = 0
        self._start_time: float = 0.0

    def start(self) -> None:
        with self._lock:
            self._start_time = time.time()

    def record_retry(self) -> None:
        with self._lock:
            self._retries += 1

    def record_circuit_breaker_trip(self) -> None:
        with self._lock:
            self._cb_trips += 1

    def record_failover(self) -> None:
        with self._lock:
            self._failovers += 1

    def record_recovery(self) -> None:
        with self._lock:
            self._recoveries += 1

    def record_timeout(self) -> None:
        with self._lock:
            self._timeouts += 1

    def record_degraded(self) -> None:
        with self._lock:
            self._degraded += 1

    def record_watchdog_intervention(self) -> None:
        with self._lock:
            self._watchdog_interventions += 1

    def snapshot(self) -> ResilienceMetrics:
        with self._lock:
            uptime = time.time() - self._start_time if self._start_time else 0.0
            return ResilienceMetrics(
                retries=self._retries,
                circuit_breaker_trips=self._cb_trips,
                failovers=self._failovers,
                recoveries=self._recoveries,
                timeouts=self._timeouts,
                degraded_operations=self._degraded,
                watchdog_interventions=self._watchdog_interventions,
                uptime_seconds=uptime,
            )

    def reset(self) -> None:
        with self._lock:
            self._retries = 0
            self._cb_trips = 0
            self._failovers = 0
            self._recoveries = 0
            self._timeouts = 0
            self._degraded = 0
            self._watchdog_interventions = 0
