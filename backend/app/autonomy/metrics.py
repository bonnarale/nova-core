"""Autonomy metrics collection."""

from __future__ import annotations

import threading
import time
from typing import Any


class AutonomyMetrics:
    """Snapshot of autonomy metrics."""

    __slots__ = (
        "recommendations_generated", "approvals", "rejections",
        "optimization_gains", "policy_violations", "autonomous_executions",
        "uptime_seconds",
    )

    def __init__(self, **kwargs: Any) -> None:
        for slot in self.__slots__:
            setattr(self, slot, kwargs.get(slot, 0))

    def to_dict(self) -> dict[str, Any]:
        return {slot: getattr(self, slot) for slot in self.__slots__}


class AutonomyMetricsCollector:
    """Thread-safe collector for autonomy metrics."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._recommendations = 0
        self._approvals = 0
        self._rejections = 0
        self._optimization_gains = 0.0
        self._policy_violations = 0
        self._autonomous_executions = 0
        self._start_time: float = 0.0

    def start(self) -> None:
        with self._lock:
            self._start_time = time.time()

    def record_recommendation(self) -> None:
        with self._lock:
            self._recommendations += 1

    def record_approval(self) -> None:
        with self._lock:
            self._approvals += 1

    def record_rejection(self) -> None:
        with self._lock:
            self._rejections += 1

    def record_optimization_gain(self, gain: float) -> None:
        with self._lock:
            self._optimization_gains += gain

    def record_policy_violation(self) -> None:
        with self._lock:
            self._policy_violations += 1

    def record_autonomous_execution(self) -> None:
        with self._lock:
            self._autonomous_executions += 1

    def snapshot(self) -> AutonomyMetrics:
        with self._lock:
            uptime = time.time() - self._start_time if self._start_time else 0.0
            return AutonomyMetrics(
                recommendations_generated=self._recommendations,
                approvals=self._approvals,
                rejections=self._rejections,
                optimization_gains=self._optimization_gains,
                policy_violations=self._policy_violations,
                autonomous_executions=self._autonomous_executions,
                uptime_seconds=uptime,
            )

    def reset(self) -> None:
        with self._lock:
            self._recommendations = 0
            self._approvals = 0
            self._rejections = 0
            self._optimization_gains = 0.0
            self._policy_violations = 0
            self._autonomous_executions = 0
