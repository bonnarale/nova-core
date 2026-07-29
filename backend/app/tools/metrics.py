"""Tool-specific metrics collector."""

from __future__ import annotations

import time
from typing import Any


class ToolMetrics:
    """Metrics collector for tool executions.

    Tracks per-tool: executions, failures, timeouts, latency, usage frequency, success rate.
    """

    def __init__(self) -> None:
        self._executions: dict[str, int] = {}
        self._failures: dict[str, int] = {}
        self._timeouts: dict[str, int] = {}
        self._latencies: dict[str, list[float]] = {}
        self._usage_frequency: dict[str, int] = {}
        self._last_used: dict[str, float] = {}
        self._global_executions = 0
        self._global_failures = 0

    def record_execution(self, tool_id: str, duration_ms: float, success: bool, timed_out: bool = False) -> None:
        self._executions[tool_id] = self._executions.get(tool_id, 0) + 1
        self._global_executions += 1

        if tool_id not in self._latencies:
            self._latencies[tool_id] = []
        self._latencies[tool_id].append(duration_ms)

        if not success:
            self._failures[tool_id] = self._failures.get(tool_id, 0) + 1
            self._global_failures += 1

        if timed_out:
            self._timeouts[tool_id] = self._timeouts.get(tool_id, 0) + 1

        self._usage_frequency[tool_id] = self._usage_frequency.get(tool_id, 0) + 1
        self._last_used[tool_id] = time.time()

    def get_executions(self, tool_id: str | None = None) -> int:
        if tool_id:
            return self._executions.get(tool_id, 0)
        return self._global_executions

    def get_failures(self, tool_id: str | None = None) -> int:
        if tool_id:
            return self._failures.get(tool_id, 0)
        return self._global_failures

    def get_timeouts(self, tool_id: str | None = None) -> int:
        if tool_id:
            return self._timeouts.get(tool_id, 0)
        return sum(self._timeouts.values())

    def get_latency(self, tool_id: str) -> dict[str, float]:
        values = self._latencies.get(tool_id, [])
        if not values:
            return {"avg_ms": 0.0, "min_ms": 0.0, "max_ms": 0.0, "count": 0}
        return {
            "avg_ms": round(sum(values) / len(values), 2),
            "min_ms": round(min(values), 2),
            "max_ms": round(max(values), 2),
            "count": len(values),
        }

    def get_success_rate(self, tool_id: str | None = None) -> float:
        if tool_id:
            total = self._executions.get(tool_id, 0)
            if total == 0:
                return 1.0
            failures = self._failures.get(tool_id, 0)
            return round(1.0 - (failures / total), 4)
        if self._global_executions == 0:
            return 1.0
        return round(1.0 - (self._global_failures / self._global_executions), 4)

    def get_usage_frequency(self, tool_id: str | None = None) -> int:
        if tool_id:
            return self._usage_frequency.get(tool_id, 0)
        return sum(self._usage_frequency.values())

    def get_last_used(self, tool_id: str) -> float | None:
        return self._last_used.get(tool_id)

    def snapshot(self) -> dict[str, Any]:
        tools: dict[str, Any] = {}
        all_tool_ids = set(self._executions.keys()) | set(self._failures.keys()) | set(self._timeouts.keys())
        for tool_id in sorted(all_tool_ids):
            tools[tool_id] = {
                "executions": self._executions.get(tool_id, 0),
                "failures": self._failures.get(tool_id, 0),
                "timeouts": self._timeouts.get(tool_id, 0),
                "latency": self.get_latency(tool_id),
                "success_rate": self.get_success_rate(tool_id),
                "usage_frequency": self._usage_frequency.get(tool_id, 0),
            }

        return {
            "global": {
                "executions": self._global_executions,
                "failures": self._global_failures,
                "success_rate": self.get_success_rate(),
                "total_usage": self.get_usage_frequency(),
            },
            "tools": tools,
        }

    def clear(self) -> None:
        self._executions.clear()
        self._failures.clear()
        self._timeouts.clear()
        self._latencies.clear()
        self._usage_frequency.clear()
        self._last_used.clear()
        self._global_executions = 0
        self._global_failures = 0
