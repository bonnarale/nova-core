"""Integration enums and state definitions."""

from __future__ import annotations

from enum import Enum


class IntegrationState(str, Enum):
    """Lifecycle states for the integration layer."""

    REGISTERED = "registered"
    DISCOVERING = "discovering"
    VALIDATED = "validated"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    DEGRADED = "degraded"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN = "shutdown"
    FAILED = "failed"


class ComponentState(str, Enum):
    """State of a registered component."""

    REGISTERED = "registered"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    DEGRADED = "degraded"
    FAILED = "failed"
    SHUTDOWN = "shutdown"
    UNKNOWN = "unknown"


class HealthStatus(str, Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class DependencyType(str, Enum):
    """Types of dependencies between components."""

    REQUIRED = "required"
    OPTIONAL = "optional"
    SOFT = "soft"


class ValidationSeverity(str, Enum):
    """Severity levels for validation findings."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class CompatibilityLevel(str, Enum):
    """Compatibility check results."""

    COMPATIBLE = "compatible"
    DEPRECATED = "deprecated"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"
