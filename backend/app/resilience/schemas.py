"""Resilience API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ResetRequest(BaseModel):
    """Request to reset resilience state."""

    components: list[str] | None = Field(default=None, description="Components to reset, or all if None")


class RecoveryRequest(BaseModel):
    """Request to recover a component."""

    component: str = Field(..., description="Component to recover")
    force: bool = Field(default=False, description="Force recovery even if not failed")


class HealthResponse(BaseModel):
    """Resilience health response."""

    status: str = Field(..., description="Overall status")
    circuit_breakers: dict[str, str] = Field(..., description="Circuit breaker states")
    degraded_services: list[str] = Field(..., description="Degraded services")


class StatusResponse(BaseModel):
    """Resilience status response."""

    state: str = Field(..., description="Current state")
    uptime_seconds: float = Field(..., description="Uptime in seconds")
    total_protections: int = Field(..., description="Total protected components")
    active_circuit_breakers: int = Field(..., description="Active circuit breakers")


class CircuitBreakerResponse(BaseModel):
    """Circuit breaker status response."""

    breakers: list[dict[str, Any]] = Field(..., description="All circuit breakers")
    summary: dict[str, Any] = Field(..., description="Summary statistics")


class RetriesResponse(BaseModel):
    """Retry statistics response."""

    total_retries: int = Field(..., description="Total retries")
    by_policy: dict[str, int] = Field(..., description="Retries by policy")
    success_rate: float = Field(..., description="Retry success rate")


class FailoverResponse(BaseModel):
    """Failover events response."""

    events: list[dict[str, Any]] = Field(..., description="Failover events")
    total: int = Field(..., description="Total failover events")


class RecoveryResponse(BaseModel):
    """Recovery history response."""

    events: list[dict[str, Any]] = Field(..., description="Recovery events")
    total: int = Field(..., description="Total recovery events")


class DiagnosticsResponse(BaseModel):
    """Resilience diagnostics response."""

    circuit_breakers: dict[str, Any] = Field(..., description="Circuit breaker status")
    retry_stats: dict[str, Any] = Field(..., description="Retry statistics")
    timeout_events: list[dict[str, Any]] = Field(..., description="Timeout events")
    failover_events: list[dict[str, Any]] = Field(..., description="Failover events")
    degraded_services: list[str] = Field(..., description="Degraded services")
    recovery_history: list[dict[str, Any]] = Field(..., description="Recovery history")


class MetricsResponse(BaseModel):
    """Resilience metrics response."""

    retries: int = Field(..., description="Total retries")
    circuit_breaker_trips: int = Field(..., description="Circuit breaker trips")
    failovers: int = Field(..., description="Total failovers")
    recoveries: int = Field(..., description="Total recoveries")
    timeouts: int = Field(..., description="Total timeouts")
    degraded_operations: int = Field(..., description="Degraded operations")
    watchdog_interventions: int = Field(..., description="Watchdog interventions")


class TracesResponse(BaseModel):
    """Resilience traces response."""

    traces: list[dict[str, Any]] = Field(..., description="Recent traces")
    total: int = Field(..., description="Total traces recorded")
