"""Tool execution context — carries user, session, agent, and metadata through tool calls."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolContext:
    """Context passed to every tool execution.

    Provides user identity, session, conversation memory, profile,
    permissions, agent identity, and execution metadata.
    """

    execution_id: str = ""
    tool_id: str = ""
    agent_id: str = ""
    user_id: str = ""
    session_id: str = ""
    conversation_memory: Any = None
    profile: Any = None
    permissions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    start_time: float = 0.0
    timeout: float | None = None
    trace_id: str | None = None
    parent_span_id: str | None = None

    def __post_init__(self) -> None:
        if not self.execution_id:
            self.execution_id = str(uuid.uuid4())
        if not self.start_time:
            self.start_time = time.time()

    def has_permission(self, permission: str) -> bool:
        if "*" in self.permissions:
            return True
        return permission in self.permissions

    def elapsed(self) -> float:
        return time.time() - self.start_time

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "tool_id": self.tool_id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "permissions": list(self.permissions),
            "metadata": dict(self.metadata),
            "timeout": self.timeout,
            "trace_id": self.trace_id,
        }

    def with_tool(self, tool_id: str) -> ToolContext:
        return ToolContext(
            execution_id=self.execution_id,
            tool_id=tool_id,
            agent_id=self.agent_id,
            user_id=self.user_id,
            session_id=self.session_id,
            conversation_memory=self.conversation_memory,
            profile=self.profile,
            permissions=list(self.permissions),
            metadata=dict(self.metadata),
            start_time=self.start_time,
            timeout=self.timeout,
            trace_id=self.trace_id,
            parent_span_id=self.parent_span_id,
        )
