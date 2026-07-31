"""Plugin dependency resolver — topological sort of plugin dependencies."""

from __future__ import annotations

import logging
from typing import Any

from app.plugins.exceptions import PluginDependencyError
from app.plugins.models import PluginManifest

logger = logging.getLogger(__name__)


class DependencyResolver:
    """Resolves plugin dependency order using topological sort."""

    def __init__(self) -> None:
        self._graph: dict[str, set[str]] = {}

    def add_plugin(self, manifest: PluginManifest) -> None:
        deps = {d.plugin_id for d in manifest.dependencies if d.required}
        self._graph[manifest.plugin_id] = deps

    def add_plugins(self, manifests: list[PluginManifest]) -> None:
        for manifest in manifests:
            self.add_plugin(manifest)

    def resolve(self) -> list[str]:
        in_degree: dict[str, int] = {node: 0 for node in self._graph}
        dependents: dict[str, set[str]] = {node: set() for node in self._graph}
        for node, deps in self._graph.items():
            for dep in deps:
                if dep in self._graph:
                    in_degree[node] = in_degree.get(node, 0) + 1
                    dependents.setdefault(dep, set()).add(node)
        queue = [n for n, d in in_degree.items() if d == 0]
        resolved: list[str] = []
        while queue:
            queue.sort()
            node = queue.pop(0)
            resolved.append(node)
            for dependent in dependents.get(node, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        if len(resolved) != len(self._graph):
            missing = set(self._graph.keys()) - set(resolved)
            raise PluginDependencyError(
                "system",
                f"Circular dependency detected involving: {', '.join(sorted(missing))}",
            )
        return resolved

    def check_missing(self, manifests: list[PluginManifest]) -> list[str]:
        available = {m.plugin_id for m in manifests}
        missing: list[str] = []
        for manifest in manifests:
            for dep in manifest.dependencies:
                if dep.required and dep.plugin_id not in available:
                    missing.append(f"{manifest.plugin_id} requires {dep.plugin_id}")
        return missing

    def get_dependency_tree(self, plugin_id: str) -> dict[str, Any]:
        deps = self._graph.get(plugin_id, set())
        tree: dict[str, Any] = {"plugin_id": plugin_id, "depends_on": []}
        for dep in deps:
            subtree = self.get_dependency_tree(dep) if dep in self._graph else {"plugin_id": dep}
            tree["depends_on"].append(subtree)
        return tree

    def clear(self) -> None:
        self._graph.clear()

    def count(self) -> int:
        return len(self._graph)
