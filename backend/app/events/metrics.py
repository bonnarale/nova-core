"""Event metrics — collect and report event system metrics."""

from __future__ import annotations

import logging
import statistics
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)


class EventMetrics:
    """Collects and reports performance metrics for the event system."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._published: int = 0
        self._processed: int = 0
        self._failed: int = 0
        self._retries: int = 0
        self._latencies: list[float] = []
        self._subscriber_count: int = 0
        self._queue_size: int = 0
        self._replay_count: int = 0
        self._dead_letter_count: int = 0
        self._max_samples: int = 1000

    def increment_published(self, count: int = 1) -> None:
        with self._lock:
            self._published += count

    def increment_processed(self, count: int = 1) -> None:
        with self._lock:
            self._processed += count

    def increment_failed(self, count: int = 1) -> None:
        with self._lock:
            self._failed += count

    def increment_retries(self, count: int = 1) -> None:
        with self._lock:
            self._retries += count

    def record_latency(self, ms: float) -> None:
        with self._lock:
            self._latencies.append(ms)
            if len(self._latencies) > self._max_samples:
                self._latencies = self._latencies[-self._max_samples:]

    def set_subscriber_count(self, count: int) -> None:
        with self._lock:
            self._subscriber_count = count

    def set_queue_size(self, size: int) -> None:
        with self._lock:
            self._queue_size = size

    def increment_replay_count(self) -> None:
        with self._lock:
            self._replay_count += 1

    def increment_dead_letter(self, count: int = 1) -> None:
        with self._lock:
            self._dead_letter_count += count

    def get_summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_published": self._published,
                "total_processed": self._processed,
                "total_failed": self._failed,
                "total_retries": self._retries,
                "average_latency_ms": self._average(self._latencies),
                "subscriber_count": self._subscriber_count,
                "queue_size": self._queue_size,
                "replay_count": self._replay_count,
                "dead_letter_count": self._dead_letter_count,
            }

    def reset(self) -> None:
        with self._lock:
            self._published = 0
            self._processed = 0
            self._failed = 0
            self._retries = 0
            self._latencies.clear()
            self._subscriber_count = 0
            self._queue_size = 0
            self._replay_count = 0
            self._dead_letter_count = 0

    @staticmethod
    def _average(values: list[float]) -> float:
        if not values:
            return 0.0
        return round(statistics.mean(values), 3)


_metrics_instance: EventMetrics | None = None


def get_event_metrics() -> EventMetrics:
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = EventMetrics()
    return _metrics_instance
