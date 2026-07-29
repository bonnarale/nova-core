"""Pydantic schemas for the Deployment subsystem."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DeploymentHealthResponse(BaseModel):
    status: str = "healthy"
    startup: bool = False
    readiness: bool = False
    liveness: bool = False
    components: dict[str, bool] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)


class DeploymentStatisticsResponse(BaseModel):
    state: str = "registered"
    environment: str = "development"
    uptime_seconds: float = 0.0
    health_checks: int = 0
    restarts: int = 0


class EnvironmentResponse(BaseModel):
    variables: dict[str, str] = Field(default_factory=dict)
    count: int = 0


class ConfigurationResponse(BaseModel):
    environment: str = "development"
    items: dict[str, Any] = Field(default_factory=dict)
    valid: bool = True


class DiagnosticsResponse(BaseModel):
    python: dict[str, Any] = Field(default_factory=dict)
    platform: dict[str, Any] = Field(default_factory=dict)
    runtime: dict[str, Any] = Field(default_factory=dict)
    checks: dict[str, Any] = Field(default_factory=dict)


class DeploymentMetricsResponse(BaseModel):
    total_startups: int = 0
    total_shutdowns: int = 0
    total_health_checks: int = 0
    total_restarts: int = 0
    average_startup_time_ms: float = 0.0
    average_shutdown_time_ms: float = 0.0
    uptime_seconds: float = 0.0


class ReadinessResponse(BaseModel):
    status: str = "ready"
    ready: bool = True
    checks: dict[str, bool] = Field(default_factory=dict)
    timestamp: float = 0.0


class LivenessResponse(BaseModel):
    status: str = "alive"
    alive: bool = True
    timestamp: float = 0.0


class StartupResponse(BaseModel):
    status: str = "completed"
    started: bool = True
    completed: bool = True
    elapsed_seconds: float = 0.0
    timeout_seconds: float = 60.0
