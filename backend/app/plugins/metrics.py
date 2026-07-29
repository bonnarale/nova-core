"""Plugin metrics — tracks plugin-specific metrics."""

from __future__ import annotations

import threading
import time
from typing import Any


class PluginMetrics:
    """Tracks plugin system metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._timers: dict[str, list[float]] = {}
        self._created_at = time.time()

    def increment(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    def decrement(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) - value

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def record_timer(self, name: str, duration_ms: float, labels: dict[str, str] | None = None) -> None:
        key = self._make_key(name, labels)
        with self._lock:
            self._timers.setdefault(key, []).append(duration_ms)

    def get_counter(self, name: str, labels: dict[str, str] | None = None) -> float:
        key = self._make_key(name, labels)
        with self._lock:
            return self._counters.get(key, 0.0)

    def get_gauge(self, name: str, labels: dict[str, str] | None = None) -> float:
        key = self._make_key(name, labels)
        with self._lock:
            return self._gauges.get(key, 0.0)

    def get_timer_stats(self, name: str, labels: dict[str, str] | None = None) -> dict[str, float]:
        key = self._make_key(name, labels)
        with self._lock:
            timings = self._timers.get(key, [])
        if not timings:
            return {"count": 0, "avg_ms": 0.0, "min_ms": 0.0, "max_ms": 0.0}
        return {
            "count": len(timings),
            "avg_ms": sum(timings) / len(timings),
            "min_ms": min(timings),
            "max_ms": max(timings),
        }

    def get_all_counters(self) -> dict[str, float]:
        with self._lock:
            return dict(self._counters)

    def get_all_gauges(self) -> dict[str, float]:
        with self._lock:
            return dict(self._gauges)

    def get_all_timers(self) -> dict[str, dict[str, float]]:
        with self._lock:
            timers = dict(self._timers)
        result: dict[str, dict[str, float]] = {}
        for key, timings in timers.items():
            if timings:
                result[key] = {
                    "count": len(timings),
                    "avg_ms": sum(timings) / len(timings),
                    "min_ms": min(timings),
                    "max_ms": max(timings),
                }
        return result

    def get_all(self) -> dict[str, Any]:
        return {
            "counters": self.get_all_counters(),
            "gauges": self.get_all_gauges(),
            "timers": self.get_all_timers(),
        }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._timers.clear()

    def _make_key(self, name: str, labels: dict[str, str] | None) -> str:
        if labels:
            sorted_labels = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{name}{{{sorted_labels}}}"
        return name


_metrics_instance: PluginMetrics | None = None
_metrics_lock = threading.Lock()


def get_plugin_metrics() -> PluginMetrics:
    global _metrics_instance
    if _metrics_instance is None:
        with _metrics_lock:
            if _metrics_instance is None:
                _metrics_instance = PluginMetrics()
    return _metrics_instance
