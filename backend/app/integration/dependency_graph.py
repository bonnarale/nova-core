"""Dependency graph for system integration."""

from __future__ import annotations

import logging
import threading
from collections import defaultdict, deque
from typing import Any

from app.integration.enums import DependencyType

logger = logging.getLogger(__name__)


class DependencyNode:
    """A node in the dependency graph."""

    __slots__ = ("name", "component_type", "metadata")

    def __init__(self, name: str, component_type: str = "service", metadata: dict[str, Any] | None = None) -> None:
        self.name = name
        self.component_type = component_type
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "component_type": self.component_type,
            "metadata": self.metadata,
        }


class DependencyInfo:
    """An edge in the dependency graph."""

    __slots__ = ("source", "target", "dep_type")

    def __init__(self, source: str, target: str, dep_type: DependencyType = DependencyType.REQUIRED) -> None:
        self.source = source
        self.target = target
        self.dep_type = dep_type

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.dep_type.value,
        }


class DependencyGraph:
    """Directed dependency graph with cycle detection and topological sort."""

    def __init__(self) -> None:
        self._nodes: dict[str, DependencyNode] = {}
        self._edges: dict[str, list[DependencyInfo]] = defaultdict(list)
        self._reverse_edges: dict[str, list[DependencyInfo]] = defaultdict(list)
        self._lock = threading.RLock()

    def add_node(self, name: str, component_type: str = "service", metadata: dict[str, Any] | None = None) -> None:
        with self._lock:
            if name not in self._nodes:
                self._nodes[name] = DependencyNode(name, component_type, metadata)

    def remove_node(self, name: str) -> None:
        with self._lock:
            self._nodes.pop(name, None)
            edges = self._edges.pop(name, [])
            for edge in edges:
                self._reverse_edges[edge.target] = [
                    e for e in self._reverse_edges[edge.target] if e.source != name
                ]
            reverse = self._reverse_edges.pop(name, [])
            for edge in reverse:
                self._edges[edge.source] = [
                    e for e in self._edges[edge.source] if e.target != name
                ]

    def add_dependency(self, source: str, target: str, dep_type: str = "required") -> None:
        dt = DependencyType(dep_type)
        with self._lock:
            self.add_node(source)
            self.add_node(target)
            for existing in self._edges[source]:
                if existing.target == target:
                    return
            info = DependencyInfo(source, target, dt)
            self._edges[source].append(info)
            self._reverse_edges[target].append(info)

    def remove_dependency(self, source: str, target: str) -> None:
        with self._lock:
            self._edges[source] = [e for e in self._edges[source] if e.target != target]
            self._reverse_edges[target] = [
                e for e in self._reverse_edges[target] if e.source != source
            ]

    def get_dependencies(self, name: str) -> dict[str, list[str]]:
        with self._lock:
            required = [
                e.target for e in self._edges.get(name, []) if e.dep_type == DependencyType.REQUIRED
            ]
            optional = [
                e.target for e in self._edges.get(name, []) if e.dep_type == DependencyType.OPTIONAL
            ]
            soft = [
                e.target for e in self._edges.get(name, []) if e.dep_type == DependencyType.SOFT
            ]
            dependents = [e.source for e in self._reverse_edges.get(name, [])]
            return {
                "required": required,
                "optional": optional,
                "soft": soft,
                "dependents": dependents,
            }

    def get_direct_dependencies(self, name: str) -> list[str]:
        with self._lock:
            return [e.target for e in self._edges.get(name, [])]

    def get_direct_dependents(self, name: str) -> list[str]:
        with self._lock:
            return [e.source for e in self._reverse_edges.get(name, [])]

    def detect_cycles(self) -> list[list[str]]:
        with self._lock:
            visited: set[str] = set()
            rec_stack: set[str] = set()
            cycles: list[list[str]] = []

            def _dfs(node: str, path: list[str]) -> None:
                visited.add(node)
                rec_stack.add(node)
                path.append(node)
                for edge in self._edges.get(node, []):
                    if edge.target not in visited:
                        _dfs(edge.target, path)
                    elif edge.target in rec_stack:
                        cycle_start = path.index(edge.target)
                        cycles.append(path[cycle_start:] + [edge.target])
                path.pop()
                rec_stack.discard(node)

            for node in self._nodes:
                if node not in visited:
                    _dfs(node, [])

            return cycles

    def topological_sort(self) -> list[str]:
        with self._lock:
            # Count how many dependencies each node has (outgoing edges)
            dep_count: dict[str, int] = {}
            for name in self._nodes:
                dep_count[name] = len(self._edges.get(name, []))

            queue: deque[str] = deque()
            for name, count in dep_count.items():
                if count == 0:
                    queue.append(name)

            result: list[str] = []
            while queue:
                node = queue.popleft()
                result.append(node)
                # For each node that depends on this one (reverse edges)
                for edge in self._reverse_edges.get(node, []):
                    dep_count[edge.source] -= 1
                    if dep_count[edge.source] == 0:
                        queue.append(edge.source)

            return result

    def get_all_nodes(self) -> list[DependencyNode]:
        with self._lock:
            return list(self._nodes.values())

    def get_all_edges(self) -> list[DependencyInfo]:
        with self._lock:
            result = []
            for edges in self._edges.values():
                result.extend(edges)
            return result

    def node_count(self) -> int:
        with self._lock:
            return len(self._nodes)

    def edge_count(self) -> int:
        with self._lock:
            return sum(len(edges) for edges in self._edges.values())

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "nodes": [n.to_dict() for n in self._nodes.values()],
                "edges": [e.to_dict() for edges in self._edges.values() for e in edges],
                "node_count": len(self._nodes),
                "edge_count": self.edge_count(),
            }
