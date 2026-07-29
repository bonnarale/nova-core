"""System diagnostics for integration layer."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.integration.dependency_graph import DependencyGraph
from app.integration.enums import ComponentState
from app.integration.registry import IntegrationRegistry

logger = logging.getLogger(__name__)


class SystemDiagnostics:
    """Comprehensive system diagnostics collector."""

    def __init__(
        self,
        registry: IntegrationRegistry,
        graph: DependencyGraph,
        init_order: list[str] | None = None,
    ) -> None:
        self._registry = registry
        self._graph = graph
        self._init_order = init_order or []
        self._failures: list[dict[str, Any]] = []
        self._compatibility_issues: list[dict[str, Any]] = []

    def record_failure(self, component: str, error: str, context: str = "") -> None:
        self._failures.append({
            "component": component,
            "error": error,
            "context": context,
            "timestamp": time.time(),
        })

    def record_compatibility_issue(self, component_a: str, component_b: str, issue: str) -> None:
        self._compatibility_issues.append({
            "component_a": component_a,
            "component_b": component_b,
            "issue": issue,
            "timestamp": time.time(),
        })

    def collect(self) -> dict[str, Any]:
        engines: dict[str, Any] = {}
        providers: dict[str, Any] = {}
        services: dict[str, Any] = {}
        repositories: dict[str, Any] = {}
        for info in self._registry.list_all():
            entry = {
                "state": info.state.value,
                "version": info.version,
                "type": info.component_type,
            }
            if info.component_type == "engine":
                engines[info.name] = entry
            elif info.component_type == "provider":
                providers[info.name] = entry
            elif info.component_type == "service":
                services[info.name] = entry
            elif info.component_type == "repository":
                repositories[info.name] = entry
            else:
                services[info.name] = entry
        return {
            "engines": engines,
            "providers": providers,
            "services": services,
            "repositories": repositories,
            "dependency_graph": {
                "node_count": self._graph.node_count(),
                "edge_count": self._graph.edge_count(),
            },
            "initialization_order": list(self._init_order),
            "integration_failures": list(self._failures),
            "compatibility_issues": list(self._compatibility_issues),
        }

    def get_component_info(self, name: str) -> dict[str, Any] | None:
        info = self._registry.get(name)
        if info:
            deps = self._graph.get_dependencies(name)
            return {
                **info.to_dict(),
                "dependencies": deps,
            }
        return None

    def summary(self) -> dict[str, Any]:
        components = self._registry.list_all()
        failed = [c for c in components if c.state == ComponentState.FAILED]
        running = [c for c in components if c.state in (ComponentState.RUNNING, ComponentState.READY)]
        return {
            "total": len(components),
            "running": len(running),
            "failed": len(failed),
            "failure_count": len(self._failures),
            "compatibility_issue_count": len(self._compatibility_issues),
        }
