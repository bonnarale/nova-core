"""Backpressure management."""

from __future__ import annotations

import threading
from typing import Any


class BackpressureManager:
    """Bounded queues, request throttling, and graceful rejection."""

    def __init__(self, max_queue_size: int = 1000, throttle_rate: float = 100.0) -> None:
        self._max_queue_size = max_queue_size
        self._throttle_rate = throttle_rate
        self._current_queue = 0
        self._total_accepted = 0
        self._total_rejected = 0
        self._total_throttled = 0
        self._lock = threading.Lock()

    def can_accept(self) -> bool:
        with self._lock:
            return self._current_queue < self._max_queue_size

    def accept(self) -> bool:
        with self._lock:
            if self._current_queue < self._max_queue_size:
                self._current_queue += 1
                self._total_accepted += 1
                return True
            self._total_rejected += 1
            return False

    def release(self) -> None:
        with self._lock:
            if self._current_queue > 0:
                self._current_queue -= 1

    def is_throttled(self) -> bool:
        with self._lock:
            return self._current_queue > self._max_queue_size * 0.8

    def record_throttle(self) -> None:
        with self._lock:
            self._total_throttled += 1

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "max_queue_size": self._max_queue_size,
                "current_queue": self._current_queue,
                "utilization": self._current_queue / self._max_queue_size if self._max_queue_size > 0 else 0,
                "total_accepted": self._total_accepted,
                "total_rejected": self._total_rejected,
                "total_throttled": self._total_throttled,
            }

    def reset(self) -> None:
        with self._lock:
            self._current_queue = 0
