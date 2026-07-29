"""System Integration — coordinates all subsystems into a cohesive platform."""

from __future__ import annotations

from app.integration.compatibility import CompatibilityChecker, CompatibilityReport
from app.integration.coordinator import IntegrationCoordinator, SystemCoordinator
from app.integration.dependency_graph import DependencyGraph, DependencyInfo, DependencyNode
from app.integration.diagnostics import SystemDiagnostics
from app.integration.engine import IntegrationEngine
from app.integration.factory import IntegrationFactory
from app.integration.health import HealthAggregator, SystemHealth, SystemHealthStatus
from app.integration.lifecycle import IntegrationLifecycle, IntegrationState
from app.integration.metrics import IntegrationMetrics, IntegrationMetricsCollector
from app.integration.orchestrator import SystemOrchestrator
from app.integration.registry import ComponentInfo, ComponentState, IntegrationRegistry
from app.integration.schemas import (
    ComponentRegistrationRequest,
    CompatibilityResponse,
    DependencyGraphResponse,
    DiagnosticsResponse,
    HealthCheckResponse,
    IntegrationMetricsResponse,
    IntegrationStatusResponse,
    ReinitializeRequest,
    TracesResponse,
    ValidationRequest,
    ValidationResponse,
)
from app.integration.tracing import IntegrationTracer
from app.integration.validation import IntegrationValidator, ValidationResult

__all__ = [
    "CompatibilityChecker",
    "CompatibilityReport",
    "ComponentRegistrationRequest",
    "ComponentInfo",
    "ComponentState",
    "ComponentRegistrationRequest",
    "CompatibilityResponse",
    "DependencyGraph",
    "DependencyGraphResponse",
    "DependencyInfo",
    "DependencyNode",
    "SystemDiagnostics",
    "DiagnosticsResponse",
    "HealthAggregator",
    "HealthCheckResponse",
    "IntegrationCoordinator",
    "IntegrationEngine",
    "IntegrationFactory",
    "IntegrationLifecycle",
    "IntegrationMetrics",
    "IntegrationMetricsCollector",
    "IntegrationMetricsResponse",
    "IntegrationRegistry",
    "IntegrationState",
    "IntegrationStatusResponse",
    "IntegrationTracer",
    "IntegrationValidator",
    "ReinitializeRequest",
    "SystemCoordinator",
    "SystemDiagnostics",
    "SystemHealth",
    "SystemHealthStatus",
    "SystemOrchestrator",
    "TracesResponse",
    "ValidationRequest",
    "ValidationResponse",
    "ValidationResult",
]
