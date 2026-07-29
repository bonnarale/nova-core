"""Enums for the Scaling subsystem."""

from __future__ import annotations

from enum import Enum


class ScalingState(str, Enum):
    REGISTERED = "registered"
    INITIALIZED = "initialized"
    READY = "ready"
    RUNNING = "running"
    SCALING_UP = "scaling_up"
    SCALING_DOWN = "scaling_down"
    DEGRADED = "degraded"
    FAILED = "failed"
    SHUTDOWN = "shutdown"


class LoadBalanceStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    HEALTH_AWARE = "health_aware"


class QueuePriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class QueueState(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DRAINING = "draining"
    STOPPED = "stopped"


class CacheStrategy(str, Enum):
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"


class ShardKey(str, Enum):
    CONVERSATION = "conversation"
    VECTOR_MEMORY = "vector_memory"
    KNOWLEDGE = "knowledge"
    EVENTS = "events"
    USER = "user"


class AutoscaleMetric(str, Enum):
    CPU = "cpu"
    MEMORY = "memory"
    QUEUE_DEPTH = "queue_depth"
    REQUEST_RATE = "request_rate"
    EXECUTION_LATENCY = "execution_latency"


class LockState(str, Enum):
    AVAILABLE = "available"
    HELD = "held"
    EXPIRED = "expired"


class WorkerState(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    DRAINING = "draining"
    STOPPED = "stopped"
    FAILED = "failed"
