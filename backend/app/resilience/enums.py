"""Resilience enums and state definitions."""

from __future__ import annotations

from enum import Enum


class ResilienceState(str, Enum):
    """Lifecycle states for the resilience layer."""

    REGISTERED = "registered"
    INITIALIZED = "initialized"
    READY = "ready"
    RUNNING = "running"
    DEGRADED = "degraded"
    RECOVERING = "recovering"
    FAILED = "failed"
    SHUTDOWN = "shutdown"


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class RetryStrategy(str, Enum):
    """Retry backoff strategies."""

    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


class FallbackStrategy(str, Enum):
    """Fallback strategies."""

    DEFAULT = "default"
    CACHE = "cache"
    STALE = "stale"
    ALTERNATIVE = "alternative"
    SKIP = "skip"
    DEGRADED = "degraded"


class RecoveryPolicy(str, Enum):
    """Recovery policies."""

    RESTART = "restart"
    RESUME = "resume"
    CHECKPOINT = "checkpoint"
    ROLLBACK = "rollback"
    SKIP = "skip"


class HealthStatus(str, Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class DegradationLevel(str, Enum):
    """Graceful degradation levels."""

    NONE = "none"
    PARTIAL = "partial"
    SEVERE = "severe"
    EMERGENCY = "emergency"
