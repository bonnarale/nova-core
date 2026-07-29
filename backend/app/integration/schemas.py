"""Integration API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ComponentRegistrationRequest(BaseModel):
    """Request to register a component."""

    name: str = Field(..., description="Component name")
    component_type: str = Field(default="service", description="Component type")
    dependencies: list[str] = Field(default_factory=list, description="Dependency names")
    version: str = Field(default="0.1.0", description="Component version")
    config: dict[str, Any] = Field(default_factory=dict, description="Configuration")


class ReinitializeRequest(BaseModel):
    """Request to reinitialize the integration layer."""

    components: list[str] | None = Field(
        default=None, description="Specific components to reinitialize, or all if None"
    )


class ValidationRequest(BaseModel):
    """Request to validate integrations."""

    checks: list[str] | None = Field(
        default=None, description="Specific checks to run, or all if None"
    )


class IntegrationStatusResponse(BaseModel):
    """System integration status response."""

    state: str = Field(..., description="Current integration state")
    registered_components: int = Field(..., description="Number of registered components")
    initialized_components: int = Field(..., description="Number of initialized components")
    uptime_seconds: float = Field(..., description="Uptime in seconds")
    health_status: str = Field(..., description="Overall health status")


class HealthCheckResponse(BaseModel):
    """Unified health check response."""

    status: str = Field(..., description="Overall status")
    components: dict[str, Any] = Field(..., description="Per-component health")
    timestamp: float = Field(..., description="Check timestamp")


class ComponentInfoResponse(BaseModel):
    """Component information."""

    name: str
    state: str
    component_type: str
    version: str
    dependencies: list[str]
    registered_at: float
    initialized_at: float | None


class DependencyGraphResponse(BaseModel):
    """Dependency graph response."""

    nodes: list[dict[str, Any]] = Field(..., description="Graph nodes")
    edges: list[dict[str, Any]] = Field(..., description="Graph edges")
    topological_order: list[str] = Field(..., description="Initialization order")
    cycles: list[list[str]] = Field(..., description="Circular dependencies found")


class ValidationResponse(BaseModel):
    """Validation response."""

    valid: bool = Field(..., description="Overall validity")
    findings: list[dict[str, Any]] = Field(..., description="Validation findings")
    summary: dict[str, Any] = Field(..., description="Validation summary")


class CompatibilityResponse(BaseModel):
    """Compatibility check response."""

    compatible: bool = Field(..., description="Overall compatibility")
    checks: list[dict[str, Any]] = Field(..., description="Individual checks")
    issues: list[str] = Field(..., description="Compatibility issues")


class DiagnosticsResponse(BaseModel):
    """System diagnostics response."""

    engines: dict[str, Any] = Field(..., description="Registered engines")
    providers: dict[str, Any] = Field(..., description="Registered providers")
    services: dict[str, Any] = Field(..., description="Registered services")
    repositories: dict[str, Any] = Field(..., description="Registered repositories")
    dependency_graph: dict[str, Any] = Field(..., description="Dependency graph info")
    initialization_order: list[str] = Field(..., description="Startup order")
    integration_failures: list[dict[str, Any]] = Field(..., description="Integration failures")
    compatibility_issues: list[dict[str, Any]] = Field(..., description="Compatibility issues")


class IntegrationMetricsResponse(BaseModel):
    """Integration metrics response."""

    registered_components: int = Field(..., description="Total registered components")
    startup_time: float = Field(..., description="Startup time in seconds")
    initialization_failures: int = Field(..., description="Initialization failures")
    integration_failures: int = Field(..., description="Integration failures")
    dependency_resolution_time: float = Field(
        ..., description="Dependency resolution time in seconds"
    )
    uptime_seconds: float = Field(..., description="Total uptime")


class TracesResponse(BaseModel):
    """Integration traces response."""

    traces: list[dict[str, Any]] = Field(..., description="Recent traces")
    total: int = Field(..., description="Total traces recorded")
