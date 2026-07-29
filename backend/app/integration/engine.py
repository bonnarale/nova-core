"""Integration engine — top-level engine coordinating all integration components."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.integration.compatibility import CompatibilityChecker, CompatibilityReport
from app.integration.coordinator import SystemCoordinator
from app.integration.dependency_graph import DependencyGraph
from app.integration.diagnostics import SystemDiagnostics
from app.integration.enums import IntegrationState
from app.integration.health import HealthAggregator, SystemHealthStatus
from app.integration.lifecycle import IntegrationLifecycle
from app.integration.metrics import IntegrationMetrics, IntegrationMetricsCollector
from app.integration.orchestrator import SystemOrchestrator
from app.integration.registry import IntegrationRegistry
from app.integration.tracing import IntegrationTracer
from app.integration.validation import IntegrationValidator, ValidationResult

logger = logging.getLogger(__name__)


class IntegrationEngine:
    """Top-level integration engine coordinating all subsystems."""

    def __init__(self) -> None:
        self._registry = IntegrationRegistry()
        self._graph = DependencyGraph()
        self._coordinator = SystemCoordinator(self._registry, self._graph)
        self._orchestrator = SystemOrchestrator(self._coordinator)
        self._lifecycle = IntegrationLifecycle()
        self._health_aggregator = HealthAggregator(self._registry)
        self._validator = IntegrationValidator(self._registry, self._graph)
        self._compatibility = CompatibilityChecker(self._registry)
        self._diagnostics = SystemDiagnostics(self._registry, self._graph)
        self._metrics = IntegrationMetricsCollector()
        self._tracer = IntegrationTracer()
        self._start_time: float = 0.0
        self._initialized = False

    @property
    def registry(self) -> IntegrationRegistry:
        return self._registry

    @property
    def graph(self) -> DependencyGraph:
        return self._graph

    @property
    def coordinator(self) -> SystemCoordinator:
        return self._coordinator

    @property
    def orchestrator(self) -> SystemOrchestrator:
        return self._orchestrator

    @property
    def lifecycle(self) -> IntegrationLifecycle:
        return self._lifecycle

    @property
    def health(self) -> HealthAggregator:
        return self._health_aggregator

    @property
    def validator(self) -> IntegrationValidator:
        return self._validator

    @property
    def compatibility(self) -> CompatibilityChecker:
        return self._compatibility

    @property
    def diagnostics(self) -> SystemDiagnostics:
        return self._diagnostics

    @property
    def metrics(self) -> IntegrationMetricsCollector:
        return self._metrics

    @property
    def tracer(self) -> IntegrationTracer:
        return self._tracer

    async def start(self) -> None:
        if self._lifecycle.is_running():
            return
        trace_id = self._tracer.start_trace("integration.start")
        self._start_time = time.time()
        self._metrics.start()
        await self._orchestrator.discover_and_register()
        self._lifecycle.transition(IntegrationState.DISCOVERING, "discovered")
        await self._orchestrator.validate_dependencies()
        self._lifecycle.transition(IntegrationState.VALIDATED, "validated")
        self._lifecycle.transition(IntegrationState.INITIALIZING, "initializing")
        results = await self._orchestrator.initialize_components()
        self._diagnostics._init_order = self._orchestrator.init_order
        self._lifecycle.transition(IntegrationState.READY, "ready")
        failed = sum(1 for v in results.values() if not v)
        if failed:
            self._lifecycle.transition(IntegrationState.DEGRADED, f"{failed} failures")
        else:
            self._lifecycle.transition(IntegrationState.RUNNING, "running")
        self._initialized = True
        self._tracer.finish_trace(trace_id)
        logger.info("Integration engine started with %d components", len(results))

    async def shutdown(self) -> None:
        trace_id = self._tracer.start_trace("integration.shutdown")
        self._lifecycle.transition(IntegrationState.SHUTTING_DOWN, "shutdown")
        await self._orchestrator.shutdown_components()
        self._lifecycle.transition(IntegrationState.SHUTDOWN, "shutdown complete")
        self._tracer.finish_trace(trace_id)
        logger.info("Integration engine stopped")

    def register_component(
        self,
        name: str,
        component: Any = None,
        component_type: str = "service",
        version: str = "0.1.0",
        dependencies: list[str] | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self._orchestrator.register_component(
            name=name,
            component=component,
            component_type=component_type,
            version=version,
            dependencies=dependencies,
            config=config,
        )

    def unregister_component(self, name: str) -> bool:
        return self._orchestrator.unregister_component(name)

    async def discover_components(self) -> list[str]:
        return await self._orchestrator.discover_and_register()

    async def validate_integrations(self) -> list[ValidationResult]:
        trace_id = self._tracer.start_trace("integration.validate")
        results = self._validator.validate_all()
        self._tracer.finish_trace(trace_id)
        return results

    async def perform_health_check(self) -> SystemHealthStatus:
        trace_id = self._tracer.start_trace("integration.health")
        status = self._health_aggregator.aggregate()
        self._tracer.finish_trace(trace_id)
        return status

    def generate_dependency_graph(self) -> dict[str, Any]:
        return self._graph.to_dict()

    def generate_diagnostics(self) -> dict[str, Any]:
        trace_id = self._tracer.start_trace("integration.diagnostics")
        result = self._diagnostics.collect()
        self._tracer.finish_trace(trace_id)
        return result

    def get_compatibility_report(self) -> dict[str, Any]:
        reports = self._compatibility.check_all()
        issues = self._compatibility.get_issues()
        return {
            "compatible": len(issues) == 0,
            "checks": [r.to_dict() for r in reports],
            "issues": issues,
        }

    def get_status(self) -> dict[str, Any]:
        metrics = self._metrics.snapshot(self._registry.count())
        return {
            **self._lifecycle.get_status(),
            "registered_components": self._registry.count(),
            "metrics": metrics.to_dict(),
        }

    def get_metrics(self) -> IntegrationMetrics:
        return self._metrics.snapshot(self._registry.count())

    def get_traces(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._tracer.get_traces(limit)

    async def reinitialize(self, components: list[str] | None = None) -> dict[str, bool]:
        trace_id = self._tracer.start_trace("integration.reinitialize")
        results = await self._orchestrator.reinitialize(components)
        self._tracer.finish_trace(trace_id)
        return results

    def is_running(self) -> bool:
        return self._lifecycle.is_running()
