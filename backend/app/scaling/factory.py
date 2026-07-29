"""Factory for creating Scaling subsystem components."""

from __future__ import annotations

import logging
from typing import Any

from app.scaling.autoscaler import Autoscaler
from app.scaling.cache import InMemoryCache, LRUCache, TTLCache
from app.scaling.distributed_lock import InMemoryDistributedLock
from app.scaling.engine import ScalingEngine
from app.scaling.enums import LoadBalanceStrategy, CacheStrategy
from app.scaling.health import ScalingHealthChecker
from app.scaling.lifecycle import ScalingLifecycle
from app.scaling.load_balancer import LoadBalancer
from app.scaling.metrics import ScalingMetricsCollector
from app.scaling.partitioning import HashPartitioning, TimePartitioning
from app.scaling.queue_manager import QueueManager
from app.scaling.replication import ReplicationManager
from app.scaling.resource_manager import ResourceManager
from app.scaling.sharding import DomainSharding, ShardingStrategy
from app.scaling.tracing import ScalingTracer
from app.scaling.worker_pool import WorkerPool

logger = logging.getLogger(__name__)


class ScalingFactory:
    """Creates all Scaling subsystem components."""

    @staticmethod
    def create_all() -> dict[str, Any]:
        engine = ScalingEngine()
        return {
            "engine": engine,
            "lifecycle": engine.lifecycle,
            "load_balancer": engine.load_balancer,
            "worker_pool": engine.worker_pool,
            "queue_manager": engine.queue_manager,
            "cache": engine.cache,
            "distributed_lock": engine.distributed_lock,
            "autoscaler": engine.autoscaler,
            "resource_manager": engine.resource_manager,
            "sharding": engine.sharding,
            "replication": engine.replication,
            "metrics": engine.metrics,
            "tracer": engine.tracer,
        }

    @staticmethod
    def create_engine() -> ScalingEngine:
        return ScalingEngine()

    @staticmethod
    def create_lifecycle() -> ScalingLifecycle:
        return ScalingLifecycle()

    @staticmethod
    def create_load_balancer(strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN) -> LoadBalancer:
        return LoadBalancer(strategy)

    @staticmethod
    def create_worker_pool(pool_size: int = 4, max_queue_size: int = 100) -> WorkerPool:
        return WorkerPool(pool_size, max_queue_size)

    @staticmethod
    def create_queue_manager() -> QueueManager:
        return QueueManager()

    @staticmethod
    def create_cache(
        max_size: int = 1000,
        strategy: CacheStrategy = CacheStrategy.LRU,
        default_ttl: float | None = None,
    ) -> InMemoryCache:
        return InMemoryCache(max_size, strategy, default_ttl)

    @staticmethod
    def create_lru_cache(max_size: int = 1000, default_ttl: float | None = None) -> LRUCache:
        return LRUCache(max_size, default_ttl)

    @staticmethod
    def create_ttl_cache(max_size: int = 1000, default_ttl: float = 300.0) -> TTLCache:
        return TTLCache(max_size, default_ttl)

    @staticmethod
    def create_distributed_lock() -> InMemoryDistributedLock:
        return InMemoryDistributedLock()

    @staticmethod
    def create_autoscaler(
        min_workers: int = 1,
        max_workers: int = 10,
        scale_up_threshold: float = 80.0,
        scale_down_threshold: float = 20.0,
    ) -> Autoscaler:
        return Autoscaler(min_workers, max_workers, scale_up_threshold, scale_down_threshold)

    @staticmethod
    def create_resource_manager() -> ResourceManager:
        return ResourceManager()

    @staticmethod
    def create_sharding(domains: dict[str, int] | None = None) -> DomainSharding:
        return DomainSharding(domains)

    @staticmethod
    def create_sharding_strategy(num_shards: int = 8) -> ShardingStrategy:
        return ShardingStrategy(num_shards)

    @staticmethod
    def create_hash_partitioning(num_partitions: int = 8) -> HashPartitioning:
        return HashPartitioning(num_partitions)

    @staticmethod
    def create_time_partitioning(interval: str = "daily", max_partitions: int = 30) -> TimePartitioning:
        return TimePartitioning(interval, max_partitions)

    @staticmethod
    def create_replication(primary_id: str = "primary") -> ReplicationManager:
        return ReplicationManager(primary_id)

    @staticmethod
    def create_health_checker() -> ScalingHealthChecker:
        return ScalingHealthChecker()

    @staticmethod
    def create_metrics() -> ScalingMetricsCollector:
        return ScalingMetricsCollector()

    @staticmethod
    def create_tracer() -> ScalingTracer:
        return ScalingTracer()
