"""Health aggregation across all subsystems."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.integration.enums import ComponentState, HealthStatus
from app.integration.registry import IntegrationRegistry

logger = logging.getLogger(__name__)


class SystemHealthStatus:
    """Overall system health."""

    __slots__ = ("status", "component_count", "healthy_count", "degraded_count", "unhealthy_count", "unknown_count", "timestamp")

    def __init__(
        self,
        status: HealthStatus,
        component_count: int = 0,
        healthy_count: int = 0,
        degraded_count: int = 0,
        unhealthy_count: int = 0,
        unknown_count: int = 0,
    ) -> None:
        self.status = status
        self.component_count = component_count
        self.healthy_count = healthy_count
        self.degraded_count = degraded_count
        self.unhealthy_count = unhealthy_count
        self.unknown_count = unknown_count
        self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "component_count": self.component_count,
            "healthy_count": self.healthy_count,
            "degraded_count": self.degraded_count,
            "unhealthy_count": self.unhealthy_count,
            "unknown_count": self.unknown_count,
            "timestamp": self.timestamp,
        }


class SystemHealth:
    """Health check result for a single component."""

    __slots__ = ("name", "status", "message", "details")

    def __init__(
        self,
        name: str,
        status: HealthStatus,
        message: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
        }


class HealthAggregator:
    """Aggregates health checks from all registered components."""

    _STATE_HEALTH_MAP = {
        ComponentState.READY: HealthStatus.HEALTHY,
        ComponentState.RUNNING: HealthStatus.HEALTHY,
        ComponentState.DEGRADED: HealthStatus.DEGRADED,
        ComponentState.REGISTERED: HealthStatus.UNKNOWN,
        ComponentState.INITIALIZING: HealthStatus.UNKNOWN,
        ComponentState.FAILED: HealthStatus.UNHEALTHY,
        ComponentState.SHUTDOWN: HealthStatus.UNKNOWN,
        ComponentState.UNKNOWN: HealthStatus.UNKNOWN,
    }

    def __init__(self, registry: IntegrationRegistry) -> None:
        self._registry = registry
        self._custom_checks: dict[str, Any] = {}

    def set_health_check(self, name: str, check_fn: Any) -> None:
        self._custom_checks[name] = check_fn

    def check_component(self, name: str) -> SystemHealth:
        info = self._registry.get(name)
        if not info:
            return SystemHealth(name, HealthStatus.UNKNOWN, "Component not registered")
        if name in self._custom_checks:
            try:
                result = self._custom_checks[name](info.component)
                return SystemHealth(name, HealthStatus.HEALTHY, "Custom check passed", {"result": result})
            except Exception as exc:
                return SystemHealth(name, HealthStatus.UNHEALTHY, str(exc))
        status = self._STATE_HEALTH_MAP.get(info.state, HealthStatus.UNKNOWN)
        return SystemHealth(name, status, f"State: {info.state.value}")

    def check_all(self) -> dict[str, SystemHealth]:
        results: dict[str, SystemHealth] = {}
        for info in self._registry.list_all():
            results[info.name] = self.check_component(info.name)
        return results

    def aggregate(self) -> SystemHealthStatus:
        checks = self.check_all()
        healthy = sum(1 for h in checks.values() if h.status == HealthStatus.HEALTHY)
        degraded = sum(1 for h in checks.values() if h.status == HealthStatus.DEGRADED)
        unhealthy = sum(1 for h in checks.values() if h.status == HealthStatus.UNHEALTHY)
        unknown = sum(1 for h in checks.values() if h.status == HealthStatus.UNKNOWN)
        total = len(checks)
        if unhealthy > 0:
            overall = HealthStatus.UNHEALTHY
        elif degraded > 0:
            overall = HealthStatus.DEGRADED
        elif healthy > 0:
            overall = HealthStatus.HEALTHY
        else:
            overall = HealthStatus.UNKNOWN
        return SystemHealthStatus(
            status=overall,
            component_count=total,
            healthy_count=healthy,
            degraded_count=degraded,
            unhealthy_count=unhealthy,
            unknown_count=unknown,
        )
