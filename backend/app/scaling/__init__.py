"""Scaling subsystem — Chapter 28.

Horizontal and vertical scaling capabilities.
"""

from app.scaling.autoscaler import Autoscaler
from app.scaling.base import (
    AutoscalerProvider,
    CacheProvider,
    DistributedLockProvider,
    LoadBalancerProvider,
    ScalingProvider,
    WorkerPoolProvider,
)
from app.scaling.cache import InMemoryCache, LRUCache, TTLCache
from app.scaling.distributed_lock import InMemoryDistributedLock
from app.scaling.engine import ScalingEngine
from app.scaling.enums import (
    AutoscaleMetric,
    CacheStrategy,
    LoadBalanceStrategy,
    LockState,
    QueuePriority,
    QueueState,
    ScalingState,
    ShardKey,
    WorkerState,
)
from app.scaling.factory import ScalingFactory
from app.scaling.health import ScalingHealthChecker
from app.scaling.lifecycle import ScalingLifecycle
from app.scaling.load_balancer import LoadBalancer
from app.scaling.manager import ScalingManager
from app.scaling.metrics import ScalingMetricsCollector
from app.scaling.models import (
    CacheStats,
    QueueInfo,
    ResourceSnapshot,
    ScalingHealth,
    ScalingMetrics,
    ScalingStatistics,
    WorkerInfo,
)
from app.scaling.partitioning import HashPartitioning, TimePartitioning
from app.scaling.queue_manager import QueueManager
from app.scaling.replication import ReplicationManager
from app.scaling.resource_manager import ResourceManager
from app.scaling.schemas import (
    CacheClearResponse,
    CacheResponse,
    QueuesResponse,
    ResourcesResponse,
    ScalingHealthResponse,
    ScalingMetricsResponse,
    ScalingStatisticsResponse,
    ScaleDownRequest,
    ScaleUpRequest,
    WorkersResponse,
)
from app.scaling.sharding import DomainSharding, ShardingStrategy
from app.scaling.tracing import ScalingTracer
from app.scaling.worker_pool import WorkerPool

__all__ = [
    # ABCs
    "ScalingProvider",
    "LoadBalancerProvider",
    "WorkerPoolProvider",
    "CacheProvider",
    "DistributedLockProvider",
    "AutoscalerProvider",
    # Enums
    "ScalingState",
    "LoadBalanceStrategy",
    "QueuePriority",
    "QueueState",
    "CacheStrategy",
    "ShardKey",
    "AutoscaleMetric",
    "LockState",
    "WorkerState",
    # Models
    "ScalingMetrics",
    "ScalingHealth",
    "ScalingStatistics",
    "WorkerInfo",
    "QueueInfo",
    "CacheStats",
    "ResourceSnapshot",
    # Core
    "ScalingEngine",
    "ScalingManager",
    "ScalingLifecycle",
    "ScalingHealthChecker",
    "ScalingMetricsCollector",
    "ScalingTracer",
    "ScalingFactory",
    # Components
    "LoadBalancer",
    "WorkerPool",
    "QueueManager",
    "InMemoryCache",
    "LRUCache",
    "TTLCache",
    "InMemoryDistributedLock",
    "Autoscaler",
    "ResourceManager",
    "DomainSharding",
    "ShardingStrategy",
    "HashPartitioning",
    "TimePartitioning",
    "ReplicationManager",
    # Schemas
    "ScalingHealthResponse",
    "ScalingMetricsResponse",
    "ScalingStatisticsResponse",
    "WorkersResponse",
    "QueuesResponse",
    "CacheResponse",
    "ResourcesResponse",
    "ScaleUpRequest",
    "ScaleDownRequest",
    "CacheClearResponse",
]
