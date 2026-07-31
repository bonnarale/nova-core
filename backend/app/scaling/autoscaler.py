"""Autoscaler with metric-based policies."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from app.scaling.base import AutoscalerProvider
from app.scaling.enums import AutoscaleMetric

logger = logging.getLogger(__name__)


class _MetricWindow:
    __slots__ = ("values", "max_size")

    def __init__(self, max_size: int = 60) -> None:
        self.values: list[tuple[float, float]] = []
        self.max_size = max_size

    def add(self, value: float) -> None:
        self.values.append((time.time(), value))
        if len(self.values) > self.max_size:
            self.values = self.values[-self.max_size:]

    @property
    def current(self) -> float:
        return self.values[-1][1] if self.values else 0.0

    @property
    def average(self) -> float:
        if not self.values:
            return 0.0
        return sum(v for _, v in self.values) / len(self.values)


class Autoscaler(AutoscalerProvider):
    """Metric-based autoscaler with configurable thresholds."""

    def __init__(
        self,
        min_workers: int = 1,
        max_workers: int = 10,
        scale_up_threshold: float = 80.0,
        scale_down_threshold: float = 20.0,
        cooldown_seconds: float = 60.0,
    ) -> None:
        self._lock = threading.Lock()
        self._min_workers = min_workers
        self._max_workers = max_workers
        self._scale_up_threshold = scale_up_threshold
        self._scale_down_threshold = scale_down_threshold
        self._cooldown = cooldown_seconds
        self._current_workers = min_workers
        self._metrics: dict[str, _MetricWindow] = {
            m.value: _MetricWindow() for m in AutoscaleMetric
        }
        self._last_scale_time = 0.0
        self._scale_events: list[dict[str, Any]] = []
        self._enabled = True

    @property
    def current_workers(self) -> int:
        return self._current_workers

    async def record_metric(self, metric: str, value: float) -> None:
        with self._lock:
            if metric in self._metrics:
                self._metrics[metric].add(value)

    async def evaluate(self) -> dict[str, Any]:
        with self._lock:
            if not self._enabled:
                return {"action": "none", "reason": "autoscaler_disabled"}

            now = time.time()
            if now - self._last_scale_time < self._cooldown:
                return {"action": "none", "reason": "cooldown_active"}

            recommendation = self._compute_recommendation()
            if recommendation["action"] == "scale_up":
                self._current_workers = min(
                    self._current_workers + 1, self._max_workers
                )
                self._last_scale_time = now
                self._record_event("scale_up", self._current_workers)
            elif recommendation["action"] == "scale_down":
                self._current_workers = max(
                    self._current_workers - 1, self._min_workers
                )
                self._last_scale_time = now
                self._record_event("scale_down", self._current_workers)

            return recommendation

    async def get_recommendation(self) -> dict[str, Any]:
        return self._compute_recommendation()

    def get_config(self) -> dict[str, Any]:
        return {
            "min_workers": self._min_workers,
            "max_workers": self._max_workers,
            "scale_up_threshold": self._scale_up_threshold,
            "scale_down_threshold": self._scale_down_threshold,
            "cooldown_seconds": self._cooldown,
            "current_workers": self._current_workers,
            "enabled": self._enabled,
        }

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def set_current_workers(self, count: int) -> None:
        self._current_workers = max(self._min_workers, min(count, self._max_workers))

    def get_metric_values(self) -> dict[str, float]:
        with self._lock:
            return {k: v.current for k, v in self._metrics.items()}

    def get_events(self) -> list[dict[str, Any]]:
        return list(self._scale_events[-100:])

    def _compute_recommendation(self) -> dict[str, Any]:
        cpu = self._metrics[AutoscaleMetric.CPU.value].current
        memory = self._metrics[AutoscaleMetric.MEMORY.value].current
        queue_depth = self._metrics[AutoscaleMetric.QUEUE_DEPTH.value].current
        max_utilization = max(cpu, memory)

        if max_utilization > self._scale_up_threshold or queue_depth > 100:
            return {
                "action": "scale_up",
                "reason": f"high_utilization(cpu={cpu:.1f}, mem={memory:.1f}, queue={queue_depth:.0f})",
                "current_workers": self._current_workers,
                "target_workers": min(self._current_workers + 1, self._max_workers),
            }
        elif max_utilization < self._scale_down_threshold and queue_depth < 10:
            return {
                "action": "scale_down",
                "reason": f"low_utilization(cpu={cpu:.1f}, mem={memory:.1f}, queue={queue_depth:.0f})",
                "current_workers": self._current_workers,
                "target_workers": max(self._current_workers - 1, self._min_workers),
            }
        return {
            "action": "none",
            "reason": "within_thresholds",
            "current_workers": self._current_workers,
        }

    def _record_event(self, action: str, workers: int) -> None:
        self._scale_events.append({
            "action": action,
            "workers": workers,
            "timestamp": time.time(),
        })
