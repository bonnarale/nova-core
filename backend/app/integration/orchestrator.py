"""System orchestrator — coordinates initialization and shutdown of all subsystems."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.integration.coordinator import SystemCoordinator
from app.integration.dependency_graph import DependencyGraph
from app.integration.enums import ComponentState
from app.integration.lifecycle import IntegrationLifecycle
from app.integration.metrics import IntegrationMetricsCollector
from app.integration.registry import IntegrationRegistry
from app.integration.tracing import IntegrationTracer

logger = logging.getLogger(__name__)


class SystemOrchestrator:
    """Orchestrates startup and shutdown order across all registered subsystems."""

    # Canonical dependency map for all NOVA CORE subsystems
    SUBSYSTEM_DEPENDENCIES: dict[str, list[str]] = {
        "cognitive_engine": ["memory", "events", "reasoning", "learning"],
        "memory": ["events"],
        "learning": ["memory", "events"],
        "knowledge_graph": ["events"],
        "reasoning": ["events"],
        "goal_engine": ["events"],
        "task_engine": ["events"],
        "planning_engine": ["events", "reasoning"],
        "execution_engine": ["events", "tools"],
        "multi_agent_runtime": ["events", "tools"],
        "tool_system": ["events"],
        "model_gateway": ["events", "security"],
        "rag": ["vector_memory", "knowledge_graph", "models"],
        "vector_memory": ["models", "events"],
        "event_system": [],
        "scheduler": ["events"],
        "workflow_engine": ["events", "tools", "scheduler"],
        "plugin_system": ["events", "security"],
        "security": ["events"],
        "observability": ["events"],
        "api_platform": [],
        "database_architecture": ["security"],
        "deployment": ["observability", "scaling"],
        "scaling": ["observability"],
        "future_roadmap": ["events"],
    }

    def __init__(self, coordinator: SystemCoordinator | None = None) -> None:
        self._coordinator = coordinator or SystemCoordinator(IntegrationRegistry(), DependencyGraph())
        self._registry = self._coordinator._registry
        self._graph = self._coordinator._graph
        self._lifecycle = IntegrationLifecycle()
        self._metrics = IntegrationMetricsCollector()
        self._tracer = IntegrationTracer()
        self._init_order: list[str] = []

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
    def lifecycle(self) -> IntegrationLifecycle:
        return self._lifecycle

    @property
    def metrics(self) -> IntegrationMetricsCollector:
        return self._metrics

    @property
    def tracer(self) -> IntegrationTracer:
        return self._tracer

    @property
    def init_order(self) -> list[str]:
        return list(self._init_order)

    async def discover_and_register(self) -> list[str]:
        """Register all canonical subsystems into the graph."""
        trace_id = self._tracer.start_trace("orchestrator.discover")
        for name, deps in self.SUBSYSTEM_DEPENDENCIES.items():
            if self._registry.get(name) is None:
                self._graph.add_node(name, "subsystem")
                for dep in deps:
                    self._graph.add_dependency(name, dep, "required")
        self._tracer.finish_trace(trace_id)
        return list(self.SUBSYSTEM_DEPENDENCIES.keys())

    def register_component(
        self,
        name: str,
        component: Any = None,
        component_type: str = "subsystem",
        version: str = "0.1.0",
        dependencies: list[str] | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Register a concrete component implementation."""
        trace_id = self._tracer.start_trace(f"orchestrator.register.{name}")
        self._registry.register(
            name=name,
            component=component,
            component_type=component_type,
            version=version,
            dependencies=dependencies,
            config=config,
        )
        self._graph.add_node(name, component_type)
        for dep in dependencies or []:
            self._graph.add_dependency(name, dep)
        self._tracer.finish_trace(trace_id)

    def unregister_component(self, name: str) -> bool:
        trace_id = self._tracer.start_trace(f"orchestrator.unregister.{name}")
        result = self._registry.unregister(name)
        self._graph.remove_node(name)
        self._tracer.finish_trace(trace_id)
        return result

    async def validate_dependencies(self) -> list[str]:
        """Detect circular dependencies and return topological order."""
        trace_id = self._tracer.start_trace("orchestrator.validate")
        start = time.time()
        cycles = self._graph.detect_cycles()
        if cycles:
            for cycle in cycles:
                logger.error("Circular dependency: %s", " -> ".join(cycle))
        order = self._graph.topological_sort()
        self._init_order = order
        duration = time.time() - start
        self._metrics.record_dependency_resolution(duration)
        self._tracer.finish_trace(trace_id)
        return order

    async def initialize_components(self) -> dict[str, bool]:
        """Initialize components in dependency order."""
        trace_id = self._tracer.start_trace("orchestrator.initialize")
        start = time.time()
        results: dict[str, bool] = {}
        order = self._init_order or self._graph.topological_sort()
        for name in order:
            info = self._registry.get(name)
            if info:
                success = await self._coordinator.initialize_component(name)
                results[name] = success
                if not success:
                    self._metrics.record_initialization_failure()
        duration = time.time() - start
        self._metrics.record_startup(duration)
        self._tracer.finish_trace(trace_id)
        return results

    async def shutdown_components(self) -> dict[str, bool]:
        """Shutdown components in reverse dependency order."""
        trace_id = self._tracer.start_trace("orchestrator.shutdown")
        results: dict[str, bool] = {}
        order = list(reversed(self._init_order or self._graph.topological_sort()))
        for name in order:
            info = self._registry.get(name)
            if info:
                success = await self._coordinator.shutdown_component(name)
                results[name] = success
        self._tracer.finish_trace(trace_id)
        return results

    async def reinitialize(self, components: list[str] | None = None) -> dict[str, bool]:
        """Reinitialize specific components or all."""
        trace_id = self._tracer.start_trace("orchestrator.reinitialize")
        targets = components or self._init_order
        results: dict[str, bool] = {}
        for name in targets:
            info = self._registry.get(name)
            if info:
                await self._coordinator.shutdown_component(name)
                self._registry.update_state(name, ComponentState.REGISTERED)
                success = await self._coordinator.initialize_component(name)
                results[name] = success
        self._tracer.finish_trace(trace_id)
        return results
