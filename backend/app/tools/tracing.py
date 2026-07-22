"""Tool execution tracing."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolTrace:
    """A single tool execution trace."""

    execution_id: str = ""
    tool_id: str = ""
    agent_id: str = ""
    user_id: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    status: str = "pending"
    inputs_metadata: dict[str, Any] = field(default_factory=dict)
    outputs_metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    timed_out: bool = False
    retries: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def close(self, status: str = "success", error: str | None = None, timed_out: bool = False) -> None:
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
        self.error = error
        self.timed_out = timed_out

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "tool_id": self.tool_id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": round(self.duration_ms, 2),
            "status": self.status,
            "inputs_metadata": dict(self.inputs_metadata),
            "outputs_metadata": dict(self.outputs_metadata),
            "error": self.error,
            "timed_out": self.timed_out,
            "retries": self.retries,
            "metadata": dict(self.metadata),
        }


class ToolTracer:
    """Collects execution traces for tool activity."""

    def __init__(self, max_traces: int = 1000) -> None:
        self._traces: list[ToolTrace] = []
        self._traces_by_id: dict[str, ToolTrace] = {}
        self._traces_by_tool: dict[str, list[ToolTrace]] = {}
        self._max_traces = max_traces

    def start_trace(
        self,
        tool_id: str,
        agent_id: str = "",
        user_id: str = "",
        inputs_metadata: dict[str, Any] | None = None,
        execution_id: str | None = None,
    ) -> ToolTrace:
        trace = ToolTrace(
            execution_id=execution_id or str(uuid.uuid4()),
            tool_id=tool_id,
            agent_id=agent_id,
            user_id=user_id,
            start_time=time.time(),
            inputs_metadata=inputs_metadata or {},
        )
        self._traces.append(trace)
        self._traces_by_id[trace.execution_id] = trace

        if tool_id not in self._traces_by_tool:
            self._traces_by_tool[tool_id] = []
        self._traces_by_tool[tool_id].append(trace)

        if len(self._traces) > self._max_traces:
            removed = self._traces.pop(0)
            self._traces_by_id.pop(removed.execution_id, None)

        return trace

    def get_trace(self, execution_id: str) -> ToolTrace | None:
        return self._traces_by_id.get(execution_id)

    def get_traces_for_tool(self, tool_id: str) -> list[ToolTrace]:
        return list(self._traces_by_tool.get(tool_id, []))

    def get_all_traces(self) -> list[ToolTrace]:
        return list(self._traces)

    def to_dict(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self._traces]

    def clear(self) -> None:
        self._traces.clear()
        self._traces_by_id.clear()
        self._traces_by_tool.clear()
