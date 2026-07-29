"""Scheduler metrics — singleton metrics tracker for scheduler operations."""

from __future__ import annotations

import threading
import time
from typing import Any

from app.scheduler.schemas import SchedulerMetricsResponse


class SchedulerMetrics:
    """Thread-safe singleton tracking scheduler metrics."""

    _instance: SchedulerMetrics | None = None
    _lock = threading.Lock()

    def __new__(cls) -> SchedulerMetrics:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._total_scheduled = 0
        self._total_executed = 0
        self._total_failed = 0
        self._total_cancelled = 0
        self._execution_times: list[float] = []
        self._retry_count = 0
        self._timeout_count = 0
        self._started_at = time.monotonic()

    def record_scheduled(self) -> None:
        self._total_scheduled += 1

    def record_executed(self, duration_ms: float) -> None:
        self._total_executed += 1
        self._execution_times.append(duration_ms)

    def record_failed(self) -> None:
        self._total_failed += 1

    def record_cancelled(self) -> None:
        self._total_cancelled += 1

    def record_retry(self) -> None:
        self._retry_count += 1

    def record_timeout(self) -> None:
        self._timeout_count += 1

    @property
    def total_scheduled(self) -> int:
        return self._total_scheduled

    @property
    def total_executed(self) -> int:
        return self._total_executed

    @property
    def total_failed(self) -> int:
        return self._total_failed

    @property
    def total_cancelled(self) -> int:
        return self._total_cancelled

    @property
    def retry_count(self) -> int:
        return self._retry_count

    @property
    def timeout_count(self) -> int:
        return self._timeout_count

    @property
    def average_execution_time_ms(self) -> float:
        if not self._execution_times:
            return 0.0
        return sum(self._execution_times) / len(self._execution_times)

    @property
    def uptime_seconds(self) -> float:
        return time.monotonic() - self._started_at

    def to_response(self, queue_length: int = 0) -> SchedulerMetricsResponse:
        return SchedulerMetricsResponse(
            total_scheduled=self._total_scheduled,
            total_executed=self._total_executed,
            total_failed=self._total_failed,
            total_cancelled=self._total_cancelled,
            average_execution_time_ms=self.average_execution_time_ms,
            queue_length=queue_length,
            retry_count=self._retry_count,
            timeout_count=self._timeout_count,
        )

    def reset(self) -> None:
        self._total_scheduled = 0
        self._total_executed = 0
        self._total_failed = 0
        self._total_cancelled = 0
        self._execution_times.clear()
        self._retry_count = 0
        self._timeout_count = 0
        self._started_at = time.monotonic()

    @classmethod
    def reset_singleton(cls) -> None:
        with cls._lock:
            cls._instance = None


def get_scheduler_metrics() -> SchedulerMetrics:
    return SchedulerMetrics()
