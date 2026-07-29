"""Scaling engine — coordinates all scaling components."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.scaling.autoscaler import Autoscaler
from app.scaling.cache import InMemoryCache
from app.scaling.distributed_lock import InMemoryDistributedLock
from app.scaling.enums import ScalingState
from app.scaling.health import ScalingHealthChecker
from app.scaling.lifecycle import ScalingLifecycle
from app.scaling.load_balancer import LoadBalancer
from app.scaling.metrics import ScalingMetricsCollector
from app.scaling.models import ScalingStatistics
from app.scaling.partitioning import HashPartitioning
from app.scaling.queue_manager import QueueManager
from app.scaling.replication import ReplicationManager
from app.scaling.resource_manager import ResourceManager
from app.scaling.sharding import DomainSharding
from app.scaling.tracing import ScalingTracer
from app.scaling.worker_pool import WorkerPool

logger = logging.getLogger(__name__)


class ScalingEngine:
    """Top-level scaling engine coordinating all scaling components."""

    def __init__(self) -> None:
        self._lifecycle = ScalingLifecycle()
        self._load_balancer = LoadBalancer()
        self._worker_pool = WorkerPool()
        self._queue_manager = QueueManager()
        self._cache = InMemoryCache()
        self._distributed_lock = InMemoryDistributedLock()
        self._autoscaler = Autoscaler()
        self._resource_manager = ResourceManager()
        self._sharding = DomainSharding()
        self._partitioning = HashPartitioning()
        self._replication = ReplicationManager()
        self._health_checker = ScalingHealthChecker()
        self._metrics = ScalingMetricsCollector()
        self._tracer = ScalingTracer()
        self._start_time: float = 0.0

    @property
    def lifecycle(self) -> ScalingLifecycle:
        return self._lifecycle

    @property
    def load_balancer(self) -> LoadBalancer:
        return self._load_balancer

    @property
    def worker_pool(self) -> WorkerPool:
        return self._worker_pool

    @property
    def queue_manager(self) -> QueueManager:
        return self._queue_manager

    @property
    def cache(self) -> InMemoryCache:
        return self._cache

    @property
    def distributed_lock(self) -> InMemoryDistributedLock:
        return self._distributed_lock

    @property
    def autoscaler(self) -> Autoscaler:
        return self._autoscaler

    @property
    def resource_manager(self) -> ResourceManager:
        return self._resource_manager

    @property
    def sharding(self) -> DomainSharding:
        return self._sharding

    @property
    def replication(self) -> ReplicationManager:
        return self._replication

    @property
    def metrics(self) -> ScalingMetricsCollector:
        return self._metrics

    @property
    def tracer(self) -> ScalingTracer:
        return self._tracer

    async def start(self) -> None:
        self._lifecycle.transition(ScalingState.INITIALIZED, "init")
        self._lifecycle.transition(ScalingState.READY, "ready")
        await self._worker_pool.start()
        self._start_time = time.time()
        self._lifecycle.transition(ScalingState.RUNNING, "started")
        logger.info("Scaling engine started")

    async def shutdown(self) -> None:
        self._lifecycle.transition(ScalingState.SHUTDOWN, "shutdown")
        await self._worker_pool.stop()
        logger.info("Scaling engine stopped")

    async def scale_up(self, amount: int = 1) -> dict[str, Any]:
        trace_id = self._tracer.start_trace("scaling.scale_up")
        self._lifecycle.transition(ScalingState.SCALING_UP, f"scale_up:{amount}")
        added = []
        for _ in range(amount):
            wid = await self._worker_pool.add_worker()
            added.append(wid)
        self._metrics.record_scaling_event()
        self._lifecycle.transition(ScalingState.RUNNING, "scaled_up")
        self._tracer.finish_trace(trace_id)
        return {"action": "scale_up", "added": added, "total": len(added)}

    async def scale_down(self, amount: int = 1) -> dict[str, Any]:
        trace_id = self._tracer.start_trace("scaling.scale_down")
        self._lifecycle.transition(ScalingState.SCALING_DOWN, f"scale_down:{amount}")
        workers = self._worker_pool.get_workers()
        removed = []
        for w in workers[:amount]:
            ok = await self._worker_pool.remove_worker(w["worker_id"])
            if ok:
                removed.append(w["worker_id"])
        self._metrics.record_scaling_event()
        self._lifecycle.transition(ScalingState.RUNNING, "scaled_down")
        self._tracer.finish_trace(trace_id)
        return {"action": "scale_down", "removed": removed, "total": len(removed)}

    async def health(self) -> dict[str, Any]:
        stats = await self._worker_pool.get_status()
        return await self._health_checker.check(
            workers_healthy=stats.get("idle_workers", 0) + stats.get("busy_workers", 0),
            workers_total=stats.get("pool_size", 0),
            queues_healthy=len(self._queue_manager.list_queues()),
            queues_total=len(self._queue_manager.list_queues()),
            cache_hit_ratio=self._cache.get_stats().hit_ratio,
            state=self._lifecycle.state,
        )

    async def statistics(self) -> ScalingStatistics:
        worker_stats = await self._worker_pool.get_status()
        cache_stats = self._cache.get_stats()
        metrics_stats = self._metrics.get_statistics()
        return ScalingStatistics(
            state=self._lifecycle.state.value,
            active_workers=worker_stats.get("busy_workers", 0),
            total_workers=worker_stats.get("pool_size", 0),
            total_tasks_completed=worker_stats.get("total_completed", 0),
            total_tasks_failed=worker_stats.get("total_failed", 0),
            queue_depth=sum(q.get("depth", 0) for q in self._queue_manager.list_queues()),
            cache_size=cache_stats.size,
            cache_hit_ratio=cache_stats.hit_ratio,
            total_scaling_events=metrics_stats["scaling_events"],
            uptime_seconds=metrics_stats["uptime_seconds"],
        )

    def is_running(self) -> bool:
        return self._lifecycle.is_running()
