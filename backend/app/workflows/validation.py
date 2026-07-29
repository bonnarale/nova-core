"""Workflow validation — validates workflow definitions and graphs."""

from __future__ import annotations

import logging
from typing import Any

from app.workflows.edge import WorkflowEdge
from app.workflows.graph import WorkflowGraph
from app.workflows.node import NodeType, WorkflowNode

logger = logging.getLogger(__name__)


class WorkflowValidator:
    """Validates workflow definitions, graphs, and configurations."""

    def __init__(self) -> None:
        self._custom_validators: list[Any] = []

    def register_validator(self, validator: Any) -> None:
        self._custom_validators.append(validator)

    def validate_definition(self, definition: dict[str, Any]) -> tuple[bool, list[str]]:
        errors: list[str] = []
        if not definition.get("name"):
            errors.append("Workflow name is required")
        if not definition.get("steps") and not definition.get("nodes"):
            errors.append("Workflow must have at least one step or node")
        for validator in self._custom_validators:
            if hasattr(validator, "validate_definition"):
                valid, errs = validator.validate_definition(definition)
                if not valid:
                    errors.extend(errs)
        return len(errors) == 0, errors

    def validate_graph(self, graph: WorkflowGraph) -> tuple[bool, list[str]]:
        errors: list[str] = []
        valid, msg = graph.is_valid_dag()
        if not valid:
            errors.append(msg)
        start_nodes = graph.get_start_nodes()
        end_nodes = graph.get_end_nodes()
        if len(start_nodes) != 1:
            errors.append(f"Expected exactly 1 start node, found {len(start_nodes)}")
        if len(end_nodes) < 1:
            errors.append("Expected at least 1 end node")
        for node in graph.get_all_nodes():
            if not node.node_id:
                errors.append("All nodes must have a node_id")
            if not node.name:
                errors.append(f"Node {node.node_id} must have a name")
        for edge in graph.get_all_edges():
            if edge.source_node_id not in {n.node_id for n in graph.get_all_nodes()}:
                errors.append(f"Edge {edge.edge_id} references unknown source node {edge.source_node_id}")
            if edge.target_node_id not in {n.node_id for n in graph.get_all_nodes()}:
                errors.append(f"Edge {edge.edge_id} references unknown target node {edge.target_node_id}")
        return len(errors) == 0, errors

    def validate_node(self, node: WorkflowNode) -> tuple[bool, list[str]]:
        errors: list[str] = []
        if not node.node_id:
            errors.append("Node ID is required")
        if not node.name:
            errors.append("Node name is required")
        if node.node_type in (NodeType.ACTION, NodeType.TOOL, NodeType.AGENT, NodeType.TASK, NodeType.GOAL) and not node.handler:
            errors.append(f"Node {node.node_id} of type {node.node_type.value} requires a handler")
        return len(errors) == 0, errors

    def validate_edge(self, edge: WorkflowEdge, node_ids: set[str]) -> tuple[bool, list[str]]:
        errors: list[str] = []
        if not edge.source_node_id:
            errors.append("Edge source node ID is required")
        if not edge.target_node_id:
            errors.append("Edge target node ID is required")
        if edge.source_node_id not in node_ids:
            errors.append(f"Edge references unknown source node {edge.source_node_id}")
        if edge.target_node_id not in node_ids:
            errors.append(f"Edge references unknown target node {edge.target_node_id}")
        if edge.source_node_id == edge.target_node_id:
            errors.append(f"Edge cannot be self-referencing: {edge.source_node_id}")
        return len(errors) == 0, errors
