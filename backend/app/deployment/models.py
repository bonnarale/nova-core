"""Domain models for the Deployment subsystem."""

from __future__ import annotations

import time
import uuid as _uuid_mod
from dataclasses import dataclass, field
from typing import Any

from app.deployment.enums import (
    DeployEnvironment,
    DeployState,
    HealthStatus,
    SecretSource,
)


def _uuid() -> str:
    return str(_uuid_mod.uuid4())


def _ts() -> float:
    return time.time()


@dataclass
class DeploymentMetrics:
    """Deployment metrics data."""

    total_startups: int = 0
    total_shutdowns: int = 0
    total_health_checks: int = 0
    total_restarts: int = 0
    average_startup_time_ms: float = 0.0
    average_shutdown_time_ms: float = 0.0
    uptime_seconds: float = 0.0
    last_health_check: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_startups": self.total_startups,
            "total_shutdowns": self.total_shutdowns,
            "total_health_checks": self.total_health_checks,
            "total_restarts": self.total_restarts,
            "average_startup_time_ms": self.average_startup_time_ms,
            "average_shutdown_time_ms": self.average_shutdown_time_ms,
            "uptime_seconds": self.uptime_seconds,
            "last_health_check": self.last_health_check,
        }


@dataclass
class DeploymentHealth:
    """Deployment health data."""

    status: str = HealthStatus.HEALTHY.value
    startup: bool = False
    readiness: bool = False
    liveness: bool = False
    components: dict[str, bool] = field(default_factory=dict)
    last_check: float = field(default_factory=_ts)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "startup": self.startup,
            "readiness": self.readiness,
            "liveness": self.liveness,
            "components": dict(self.components),
            "last_check": self.last_check,
            "details": dict(self.details),
        }


@dataclass
class DeploymentStatistics:
    """Aggregate deployment statistics."""

    state: str = DeployState.REGISTERED.value
    environment: str = DeployEnvironment.DEVELOPMENT.value
    uptime_seconds: float = 0.0
    total_requests: int = 0
    total_errors: int = 0
    health_checks: int = 0
    restarts: int = 0
    config_items: int = 0
    environment_variables: int = 0
    secrets_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "environment": self.environment,
            "uptime_seconds": self.uptime_seconds,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "health_checks": self.health_checks,
            "restarts": self.restarts,
            "config_items": self.config_items,
            "environment_variables": self.environment_variables,
            "secrets_count": self.secrets_count,
        }


@dataclass
class ConfigurationItem:
    """A configuration entry."""

    key: str = ""
    value: Any = None
    section: str = "default"
    source: str = "config"
    created_at: float = field(default_factory=_ts)
    updated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "section": self.section,
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class EnvironmentVariable:
    """An environment variable entry."""

    key: str = ""
    value: str = ""
    required: bool = False
    default: str = ""
    source: str = "environment"
    validated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "required": self.required,
            "default": self.default,
            "source": self.source,
            "validated": self.validated,
        }


@dataclass
class HealthCheck:
    """A health check result."""

    name: str = ""
    status: str = HealthStatus.UNKNOWN.value
    message: str = ""
    latency_ms: float = 0.0
    checked_at: float = field(default_factory=_ts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "latency_ms": self.latency_ms,
            "checked_at": self.checked_at,
        }


@dataclass
class SecretInfo:
    """Metadata about a secret (never stores the value)."""

    key: str = ""
    source: str = SecretSource.ENVIRONMENT.value
    created_at: float = field(default_factory=_ts)
    rotated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "source": self.source,
            "created_at": self.created_at,
            "rotated_at": self.rotated_at,
        }
