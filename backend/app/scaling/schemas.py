"""Pydantic schemas for the Scaling subsystem."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ScalingHealthResponse(BaseModel):
    status: str = "healthy"
    workers_healthy: int = 0
    workers_total: int = 0
    queues_healthy: int = 0
    queues_total: int = 0
    cache_hit_ratio: float = 0.0


class ScalingMetricsResponse(BaseModel):
    requests_per_second: float = 0.0
    active_workers: int = 0
    queue_depth: int = 0
    cache_hit_ratio: float = 0.0
    scaling_events: int = 0
    execution_throughput: float = 0.0
    resource_utilization: float = 0.0
    uptime_seconds: float = 0.0


class ScalingStatisticsResponse(BaseModel):
    state: str = "registered"
    active_workers: int = 0
    total_workers: int = 0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    queue_depth: int = 0
    cache_size: int = 0
    cache_hit_ratio: float = 0.0
    total_scaling_events: int = 0
    uptime_seconds: float = 0.0


class WorkersResponse(BaseModel):
    pool_size: int = 0
    running: bool = False
    idle_workers: int = 0
    busy_workers: int = 0
    workers: list[dict[str, Any]] = Field(default_factory=list)


class QueuesResponse(BaseModel):
    total_queues: int = 0
    total_depth: int = 0
    queues: list[dict[str, Any]] = Field(default_factory=list)


class CacheResponse(BaseModel):
    hits: int = 0
    misses: int = 0
    size: int = 0
    hit_ratio: float = 0.0
    total_sets: int = 0
    total_deletes: int = 0


class ResourcesResponse(BaseModel):
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    active_workers: int = 0
    queue_size: int = 0
    cache_usage: int = 0


class ScaleUpRequest(BaseModel):
    amount: int = 1


class ScaleDownRequest(BaseModel):
    amount: int = 1


class CacheClearResponse(BaseModel):
    cleared: int = 0
    success: bool = True
