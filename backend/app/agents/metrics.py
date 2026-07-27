"""Metrics collection for agent activity."""

from __future__ import annotations

import time
from typing import Any


class MetricsCollector:
    """Simple in-memory metrics collector for agent operations.

    Tracks counters, timers, gauges and computes derived metrics
    (success_rate, average_execution_time, throughput, utilization).
    """

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._timers: dict[str, list[float]] = {}
        self._gauges: dict[str, float] = {}

    def increment(self, name: str, value: int = 1) -> None:
        self._counters[name] = self._counters.get(name, 0) + value

    def gauge(self, name: str, value: float) -> None:
        self._gauges[name] = value

    def time(self, name: str) -> _Timer:
        return _Timer(self, name)

    def record_duration(self, name: str, duration_ms: float) -> None:
        if name not in self._timers:
            self._timers[name] = []
        self._timers[name].append(duration_ms)

    # ------------------------------------------------------------------
    # Derived metrics
    # ------------------------------------------------------------------

    def get_executions(self) -> int:
        return self._counters.get("dispatch.total", 0)

    def get_failures(self) -> int:
        total_failures = 0
        for key, val in self._counters.items():
            if "error" in key or "failed" in key:
                total_failures += val
        return total_failures

    def get_success_rate(self) -> float:
        total = self.get_executions()
        if total == 0:
            return 1.0
        failures = self.get_failures()
        return round(1.0 - (failures / total), 4)

    def get_average_execution_time(self) -> float:
        total_ms = 0.0
        count = 0
        for name, values in self._timers.items():
            if "execute" in name.lower() or "dispatch" in name.lower():
                total_ms += sum(values)
                count += len(values)
        if count == 0:
            return 0.0
        return round(total_ms / count, 2)

    def get_throughput(self, window_seconds: float = 60.0) -> float:
        """Requests per second in the given window (approximation)."""
        total = self.get_executions()
        if total == 0:
            return 0.0
        return round(total / max(window_seconds, 1.0), 4)

    def get_utilization(self) -> float:
        running = self._gauges.get("agents.running", 0)
        total_agents = self._gauges.get("agents.total", 1)
        if total_agents == 0:
            return 0.0
        return round(min(running / total_agents, 1.0), 4)

    def get_queue_size(self) -> int:
        return int(self._gauges.get("scheduler.queue_size", 0))

    def snapshot(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
        }
        timers = {}
        for name, values in self._timers.items():
            if values:
                timers[name] = {
                    "count": len(values),
                    "avg_ms": round(sum(values) / len(values), 2),
                    "min_ms": round(min(values), 2),
                    "max_ms": round(max(values), 2),
                }
            else:
                timers[name] = {"count": 0, "avg_ms": 0, "min_ms": 0, "max_ms": 0}
        result["timers"] = timers

        result["derived"] = {
            "executions": self.get_executions(),
            "failures": self.get_failures(),
            "success_rate": self.get_success_rate(),
            "average_execution_time_ms": self.get_average_execution_time(),
            "queue_size": self.get_queue_size(),
            "utilization": self.get_utilization(),
        }
        return result

    def clear(self) -> None:
        self._counters.clear()
        self._timers.clear()
        self._gauges.clear()


class _Timer:
    def __init__(self, collector: MetricsCollector, name: str) -> None:
        self._collector = collector
        self._name = name
        self._start: float | None = None

    def __enter__(self) -> _Timer:
        self._start = time.time()
        return self

    def __exit__(self, *args: Any) -> None:
        if self._start is not None:
            elapsed = (time.time() - self._start) * 1000
            self._collector.record_duration(self._name, elapsed)
