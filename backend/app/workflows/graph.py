"""Workflow graph — DAG representation of workflow nodes and edges."""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from typing import Any

from app.workflows.edge import EdgeType, WorkflowEdge
from app.workflows.node import NodeStatus, NodeType, WorkflowNode

logger = logging.getLogger(__name__)


class WorkflowGraph:
    """Directed acyclic graph for workflow execution."""

    def __init__(self) -> None:
        self._nodes: dict[str, WorkflowNode] = {}
        self._edges: dict[str, WorkflowEdge] = {}
        self._adjacency: dict[str, list[str]] = defaultdict(list)
        self._reverse_adjacency: dict[str, list[str]] = defaultdict(list)

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def add_node(self, node: WorkflowNode) -> None:
        self._nodes[node.node_id] = node

    def add_edge(self, edge: WorkflowEdge) -> None:
        self._edges[edge.edge_id] = edge
        self._adjacency[edge.source_node_id].append(edge.target_node_id)
        self._reverse_adjacency[edge.target_node_id].append(edge.source_node_id)

    def get_node(self, node_id: str) -> WorkflowNode | None:
        return self._nodes.get(node_id)

    def get_edge(self, edge_id: str) -> WorkflowEdge | None:
        return self._edges.get(edge_id)

    def get_all_nodes(self) -> list[WorkflowNode]:
        return list(self._nodes.values())

    def get_all_edges(self) -> list[WorkflowEdge]:
        return list(self._edges.values())

    def get_successors(self, node_id: str) -> list[WorkflowNode]:
        return [self._nodes[nid] for nid in self._adjacency.get(node_id, []) if nid in self._nodes]

    def get_predecessors(self, node_id: str) -> list[WorkflowNode]:
        return [self._nodes[nid] for nid in self._reverse_adjacency.get(node_id, []) if nid in self._nodes]

    def get_outgoing_edges(self, node_id: str) -> list[WorkflowEdge]:
        return [self._edges[eid] for eid, targets in self._adjacency.items() if eid in [e.edge_id for e in self._edges.values() if e.source_node_id == node_id]]

    def get_start_nodes(self) -> list[WorkflowNode]:
        return [n for n in self._nodes.values() if n.node_type == NodeType.START]

    def get_end_nodes(self) -> list[WorkflowNode]:
        return [n for n in self._nodes.values() if n.node_type == NodeType.END]

    def topological_sort(self) -> list[WorkflowNode]:
        in_degree: dict[str, int] = {nid: 0 for nid in self._nodes}
        for source, targets in self._adjacency.items():
            for target in targets:
                if target in in_degree:
                    in_degree[target] += 1

        queue: deque[str] = deque(nid for nid, deg in in_degree.items() if deg == 0)
        result: list[WorkflowNode] = []

        while queue:
            nid = queue.popleft()
            if nid in self._nodes:
                result.append(self._nodes[nid])
            for target in self._adjacency.get(nid, []):
                if target in in_degree:
                    in_degree[target] -= 1
                    if in_degree[target] == 0:
                        queue.append(target)

        return result

    def detect_cycles(self) -> list[list[str]]:
        visited: set[str] = set()
        rec_stack: set[str] = set()
        cycles: list[list[str]] = []

        def _dfs(node_id: str, path: list[str]) -> None:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            for target in self._adjacency.get(node_id, []):
                if target not in visited:
                    _dfs(target, path)
                elif target in rec_stack:
                    cycle_start = path.index(target)
                    cycles.append(path[cycle_start:] + [target])

            path.pop()
            rec_stack.discard(node_id)

        for nid in self._nodes:
            if nid not in visited:
                _dfs(nid, [])

        return cycles

    def is_valid_dag(self) -> tuple[bool, str]:
        cycles = self.detect_cycles()
        if cycles:
            return False, f"Cycle detected: {cycles[0]}"
        start_nodes = self.get_start_nodes()
        if not start_nodes:
            return False, "No start node found"
        if len(start_nodes) > 1:
            return False, f"Multiple start nodes found: {[n.node_id for n in start_nodes]}"
        end_nodes = self.get_end_nodes()
        if not end_nodes:
            return False, "No end node found"
        return True, "Valid DAG"

    def get_reachable_nodes(self, from_node_id: str) -> list[WorkflowNode]:
        visited: set[str] = set()
        result: list[WorkflowNode] = []
        queue: deque[str] = deque([from_node_id])

        while queue:
            nid = queue.popleft()
            if nid in visited or nid not in self._nodes:
                continue
            visited.add(nid)
            result.append(self._nodes[nid])
            for target in self._adjacency.get(nid, []):
                queue.append(target)

        return result

    def get_execution_paths(self) -> list[list[str]]:
        start_nodes = self.get_start_nodes()
        if not start_nodes:
            return []

        paths: list[list[str]] = []
        self._dfs_paths(start_nodes[0].node_id, [], set(), paths)
        return paths

    def _dfs_paths(self, current: str, path: list[str], visited: set[str], all_paths: list[list[str]]) -> None:
        visited.add(current)
        path.append(current)

        successors = self._adjacency.get(current, [])
        if not successors:
            all_paths.append(list(path))
        else:
            for target in successors:
                if target not in visited:
                    self._dfs_paths(target, path, visited, all_paths)

        path.pop()
        visited.discard(current)

    def clear(self) -> None:
        self._nodes.clear()
        self._edges.clear()
        self._adjacency.clear()
        self._reverse_adjacency.clear()
