"""Integration coordinator for subsystem communication."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.integration.dependency_graph import DependencyGraph
from app.integration.enums import ComponentState
from app.integration.registry import ComponentInfo, IntegrationRegistry

logger = logging.getLogger(__name__)


class IntegrationCoordinator:
    """Coordinates registration and communication between subsystems."""

    def __init__(self, registry: IntegrationRegistry, graph: DependencyGraph) -> None:
        self._registry = registry
        self._graph = graph
        self._event_log: list[dict[str, Any]] = []

    async def register_component(
        self,
        name: str,
        component: Any,
        component_type: str = "service",
        version: str = "0.1.0",
        dependencies: list[str] | None = None,
        config: dict[str, Any] | None = None,
    ) -> ComponentInfo:
        info = self._registry.register(
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
        self._log_event("register", name, {"type": component_type, "dependencies": dependencies or []})
        logger.info("Coordinator: registered component '%s'", name)
        return info

    async def unregister_component(self, name: str) -> bool:
        result = self._registry.unregister(name)
        if result:
            self._graph.remove_node(name)
            self._log_event("unregister", name, {})
            logger.info("Coordinator: unregistered component '%s'", name)
        return result

    async def get_component(self, name: str) -> Any | None:
        return self._registry.get_component(name)

    async def list_components(self) -> list[dict[str, Any]]:
        return [info.to_dict() for info in self._registry.list_all()]

    async def discover_components(self) -> list[str]:
        discovered: list[str] = []
        for info in self._registry.list_all():
            discovered.append(info.name)
        self._log_event("discover", "system", {"count": len(discovered)})
        return discovered

    def _log_event(self, event_type: str, target: str, data: dict[str, Any]) -> None:
        self._event_log.append({
            "type": event_type,
            "target": target,
            "data": data,
            "timestamp": time.time(),
        })

    def get_event_log(self) -> list[dict[str, Any]]:
        return list(self._event_log)


class SystemCoordinator(IntegrationCoordinator):
    """Extended coordinator with lifecycle management."""

    async def initialize_component(self, name: str) -> bool:
        info = self._registry.get(name)
        if not info:
            return False
        self._registry.update_state(name, ComponentState.INITIALIZING)
        try:
            component = info.component
            if component and hasattr(component, "start") and callable(component.start):
                await component.start()
            self._registry.update_state(name, ComponentState.READY)
            info.initialized_at = time.time()
            self._log_event("initialize", name, {"status": "success"})
            return True
        except Exception as exc:
            self._registry.update_state(name, ComponentState.FAILED, str(exc))
            self._log_event("initialize", name, {"status": "error", "error": str(exc)})
            logger.error("Failed to initialize '%s': %s", name, exc)
            return False

    async def shutdown_component(self, name: str) -> bool:
        info = self._registry.get(name)
        if not info:
            return False
        self._registry.update_state(name, ComponentState.SHUTDOWN)
        try:
            component = info.component
            if component and hasattr(component, "shutdown") and callable(component.shutdown):
                await component.shutdown()
            self._log_event("shutdown", name, {"status": "success"})
            return True
        except Exception as exc:
            self._log_event("shutdown", name, {"status": "error", "error": str(exc)})
            logger.error("Failed to shutdown '%s': %s", name, exc)
            return False
