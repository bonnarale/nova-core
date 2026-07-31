"""Resource manager monitoring CPU, memory, workers, queues, and cache."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from app.scaling.models import ResourceSnapshot

logger = logging.getLogger(__name__)


class ResourceManager:
    """Monitors and reports resource utilization."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snapshots: list[ResourceSnapshot] = []
        self._max_snapshots = 1000
        self._custom_metrics: dict[str, float] = {}

    def record_snapshot(
        self,
        cpu_percent: float = 0.0,
        memory_percent: float = 0.0,
        active_workers: int = 0,
        queue_size: int = 0,
        cache_usage: int = 0,
    ) -> None:
        snapshot = ResourceSnapshot(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            active_workers=active_workers,
            queue_size=queue_size,
            cache_usage=cache_usage,
        )
        with self._lock:
            self._snapshots.append(snapshot)
            if len(self._snapshots) > self._max_snapshots:
                self._snapshots = self._snapshots[-self._max_snapshots // 2:]

    def set_metric(self, name: str, value: float) -> None:
        with self._lock:
            self._custom_metrics[name] = value

    def get_metric(self, name: str) -> float:
        with self._lock:
            return self._custom_metrics.get(name, 0.0)

    def get_current(self) -> ResourceSnapshot:
        with self._lock:
            if self._snapshots:
                return self._snapshots[-1]
            return ResourceSnapshot()

    def get_history(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            return [s.to_dict() for s in self._snapshots[-limit:]]

    def get_statistics(self) -> dict[str, Any]:
        with self._lock:
            if not self._snapshots:
                return {
                    "snapshots": 0,
                    "avg_cpu": 0.0,
                    "avg_memory": 0.0,
                    "max_cpu": 0.0,
                    "max_memory": 0.0,
                    "custom_metrics": dict(self._custom_metrics),
                }
            cpus = [s.cpu_percent for s in self._snapshots]
            mems = [s.memory_percent for s in self._snapshots]
            return {
                "snapshots": len(self._snapshots),
                "avg_cpu": round(sum(cpus) / len(cpus), 2),
                "avg_memory": round(sum(mems) / len(mems), 2),
                "max_cpu": round(max(cpus), 2),
                "max_memory": round(max(mems), 2),
                "latest": self._snapshots[-1].to_dict(),
                "custom_metrics": dict(self._custom_metrics),
            }

    def clear(self) -> int:
        with self._lock:
            count = len(self._snapshots)
            self._snapshots.clear()
            return count
