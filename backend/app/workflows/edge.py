"""Workflow edges — directed edges connecting nodes in a workflow graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EdgeType(str, Enum):
    NORMAL = "normal"
    CONDITIONAL = "conditional"
    ERROR = "error"
    FALLBACK = "fallback"


@dataclass
class WorkflowEdge:
    edge_id: str = ""
    source_node_id: str = ""
    target_node_id: str = ""
    edge_type: EdgeType = EdgeType.NORMAL
    condition: dict[str, Any] | None = None
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "edge_type": self.edge_type.value,
            "condition": self.condition,
            "label": self.label,
        }
