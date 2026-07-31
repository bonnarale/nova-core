"""Domain models for the Scaling subsystem."""

from __future__ import annotations

import time
import uuid as _uuid_mod
from dataclasses import dataclass, field
from typing import Any

from app.scaling.enums import (
    LoadBalanceStrategy,
    QueuePriority,
    QueueState,
    ScalingState,
    WorkerState,
)


def _uuid() -> str:
    return str(_uuid_mod.uuid4())


def _ts() -> float:
    return time.time()


@dataclass
class ScalingMetrics:
    """Scaling metrics data."""

    requests_per_second: float = 0.0
    active_workers: int = 0
    queue_depth: int = 0
    cache_hit_ratio: float = 0.0
    scaling_events: int = 0
    execution_throughput: float = 0.0
    resource_utilization: float = 0.0
    uptime_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "requests_per_second": self.requests_per_second,
            "active_workers": self.active_workers,
            "queue_depth": self.queue_depth,
            "cache_hit_ratio": self.cache_hit_ratio,
            "scaling_events": self.scaling_events,
            "execution_throughput": self.execution_throughput,
            "resource_utilization": self.resource_utilization,
            "uptime_seconds": self.uptime_seconds,
        }


@dataclass
class ScalingHealth:
    """Scaling health data."""

    status: str = "healthy"
    workers_healthy: int = 0
    workers_total: int = 0
    queues_healthy: int = 0
    queues_total: int = 0
    cache_hit_ratio: float = 0.0
    last_check: float = field(default_factory=_ts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "workers_healthy": self.workers_healthy,
            "workers_total": self.workers_total,
            "queues_healthy": self.queues_healthy,
            "queues_total": self.queues_total,
            "cache_hit_ratio": self.cache_hit_ratio,
            "last_check": self.last_check,
        }


@dataclass
class ScalingStatistics:
    """Aggregate scaling statistics."""

    state: str = ScalingState.REGISTERED.value
    active_workers: int = 0
    total_workers: int = 0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    queue_depth: int = 0
    cache_size: int = 0
    cache_hit_ratio: float = 0.0
    total_scaling_events: int = 0
    uptime_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "active_workers": self.active_workers,
            "total_workers": self.total_workers,
            "total_tasks_completed": self.total_tasks_completed,
            "total_tasks_failed": self.total_tasks_failed,
            "queue_depth": self.queue_depth,
            "cache_size": self.cache_size,
            "cache_hit_ratio": self.cache_hit_ratio,
            "total_scaling_events": self.total_scaling_events,
            "uptime_seconds": self.uptime_seconds,
        }


@dataclass
class WorkerInfo:
    """Information about a worker."""

    worker_id: str = field(default_factory=_uuid)
    state: str = WorkerState.IDLE.value
    tasks_completed: int = 0
    tasks_failed: int = 0
    current_task: str = ""
    created_at: float = field(default_factory=_ts)
    last_active: float = field(default_factory=_ts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "state": self.state,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "current_task": self.current_task,
            "created_at": self.created_at,
            "last_active": self.last_active,
        }


@dataclass
class QueueInfo:
    """Information about a queue."""

    name: str = ""
    state: str = QueueState.ACTIVE.value
    depth: int = 0
    priority: str = QueuePriority.NORMAL.value
    total_enqueued: int = 0
    total_dequeued: int = 0
    total_failed: int = 0
    created_at: float = field(default_factory=_ts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state,
            "depth": self.depth,
            "priority": self.priority,
            "total_enqueued": self.total_enqueued,
            "total_dequeued": self.total_dequeued,
            "total_failed": self.total_failed,
            "created_at": self.created_at,
        }


@dataclass
class CacheStats:
    """Cache statistics."""

    hits: int = 0
    misses: int = 0
    size: int = 0
    hit_ratio: float = 0.0
    total_sets: int = 0
    total_deletes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "size": self.size,
            "hit_ratio": self.hit_ratio,
            "total_sets": self.total_sets,
            "total_deletes": self.total_deletes,
        }


@dataclass
class ResourceSnapshot:
    """Snapshot of resource usage."""

    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    active_workers: int = 0
    queue_size: int = 0
    cache_usage: int = 0
    timestamp: float = field(default_factory=_ts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "active_workers": self.active_workers,
            "queue_size": self.queue_size,
            "cache_usage": self.cache_usage,
            "timestamp": self.timestamp,
        }
