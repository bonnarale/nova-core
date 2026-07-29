"""Workflow compiler — compiles workflow definitions into executable graphs."""

from __future__ import annotations

import logging
from typing import Any

from app.workflows.edge import EdgeType, WorkflowEdge
from app.workflows.graph import WorkflowGraph
from app.workflows.node import (
    ActionNode,
    AgentNode,
    ConditionNode,
    DecisionNode,
    DelayNode,
    EndNode,
    EventNode,
    GoalNode,
    HumanApprovalNode,
    LoopNode,
    MergeNode,
    NodeType,
    ParallelNode,
    StartNode,
    SubworkflowNode,
    TaskNode,
    ToolNode,
    WaitNode,
    WorkflowNode,
)

logger = logging.getLogger(__name__)

_NODE_TYPE_MAP: dict[str, type[WorkflowNode]] = {
    "start": StartNode,
    "end": EndNode,
    "action": ActionNode,
    "tool": ToolNode,
    "agent": AgentNode,
    "task": TaskNode,
    "goal": GoalNode,
    "decision": DecisionNode,
    "condition": ConditionNode,
    "loop": LoopNode,
    "parallel": ParallelNode,
    "merge": MergeNode,
    "wait": WaitNode,
    "delay": DelayNode,
    "event": EventNode,
    "human_approval": HumanApprovalNode,
    "subworkflow": SubworkflowNode,
}


class WorkflowCompiler:
    """Compiles workflow step definitions into executable WorkflowGraph instances."""

    def __init__(self) -> None:
        self._compiled_cache: dict[str, WorkflowGraph] = {}

    def compile_from_steps(self, steps: list[dict[str, Any]], workflow_id: str = "") -> WorkflowGraph:
        graph = WorkflowGraph()

        start = StartNode(node_id=f"{workflow_id}-start", name="Start")
        graph.add_node(start)

        step_nodes: dict[str, WorkflowNode] = {}
        for step_def in steps:
            node = self._create_node_from_step(step_def, workflow_id)
            graph.add_node(node)
            step_nodes[node.node_id] = node

        for node in graph.get_all_nodes():
            if node.node_type == NodeType.START:
                continue
            predecessors = getattr(node, "depends_on", step_nodes.get(node.node_id, node).config.get("depends_on", []))
            if not predecessors:
                graph.add_edge(WorkflowEdge(
                    edge_id=f"e-{start.node_id}-{node.node_id}",
                    source_node_id=start.node_id,
                    target_node_id=node.node_id,
                ))

        end = EndNode(node_id=f"{workflow_id}-end", name="End")
        graph.add_node(end)

        end_candidates = [n for n in graph.get_all_nodes() if n.node_type != NodeType.START and n.node_type != NodeType.END]
        if end_candidates:
            for node in end_candidates:
                successors = graph.get_successors(node.node_id)
                if not successors:
                    graph.add_edge(WorkflowEdge(
                        edge_id=f"e-{node.node_id}-{end.node_id}",
                        source_node_id=node.node_id,
                        target_node_id=end.node_id,
                    ))

        self._compiled_cache[workflow_id] = graph
        return graph

    def compile_from_graph_def(self, nodes: list[dict[str, Any]], edges: list[dict[str, Any]], workflow_id: str = "") -> WorkflowGraph:
        graph = WorkflowGraph()
        for node_def in nodes:
            node_type_str = node_def.get("node_type", "action")
            node_cls = _NODE_TYPE_MAP.get(node_type_str, ActionNode)
            node = node_cls(
                node_id=node_def.get("node_id", ""),
                name=node_def.get("name", ""),
                handler=node_def.get("handler", ""),
                config=node_def.get("config", {}),
            )
            graph.add_node(node)

        for edge_def in edges:
            edge = WorkflowEdge(
                edge_id=edge_def.get("edge_id", ""),
                source_node_id=edge_def.get("source_node_id", ""),
                target_node_id=edge_def.get("target_node_id", ""),
                edge_type=EdgeType(edge_def.get("edge_type", "normal")),
                condition=edge_def.get("condition"),
                label=edge_def.get("label", ""),
            )
            graph.add_edge(edge)

        self._compiled_cache[workflow_id] = graph
        return graph

    def get_compiled(self, workflow_id: str) -> WorkflowGraph | None:
        return self._compiled_cache.get(workflow_id)

    def invalidate(self, workflow_id: str) -> bool:
        return self._compiled_cache.pop(workflow_id, None) is not None

    def _create_node_from_step(self, step_def: dict[str, Any], workflow_id: str) -> WorkflowNode:
        step_type = step_def.get("step_type", "TASK").lower()
        node_cls = _NODE_TYPE_MAP.get(step_type, ActionNode)
        return node_cls(
            node_id=step_def.get("id", ""),
            name=step_def.get("name", ""),
            handler=step_def.get("handler", ""),
            config=step_def.get("config", {}),
        )
