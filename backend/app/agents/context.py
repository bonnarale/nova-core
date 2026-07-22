"""Execution context passed to agents during task execution."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentExecutionContext:
    """Immutable context object threaded through agent execution.

    Carries task data, user info, parent trace references, metadata,
    and cancellation state.
    """

    task_id: str = ""
    goal: str = ""
    user_id: str | None = None
    session_id: str | None = None
    trace_id: str | None = None
    parent_span_id: str | None = None
    assigned_agent: str | None = None
    delegated_from: str | None = None
    priority: int = 3
    timeout_seconds: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    _cancelled: bool = field(default=False, repr=False)
    _cancel_reason: str | None = field(default=None, repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any], **overrides: Any) -> AgentExecutionContext:
        """Create a context from a dictionary, ignoring unknown keys."""
        known = {
            "task_id", "goal", "user_id", "session_id", "trace_id",
            "parent_span_id", "assigned_agent", "delegated_from",
            "priority", "timeout_seconds", "metadata",
        }
        filtered = {k: v for k, v in data.items() if k in known}
        filtered.update(overrides)
        return cls(**filtered)

    def cancel(self, reason: str = "cancelled") -> None:
        self._cancelled = True
        self._cancel_reason = reason

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    @property
    def cancel_reason(self) -> str | None:
        return self._cancel_reason

    @property
    def elapsed(self) -> float:
        return time.time() - self.created_at

    @property
    def is_timed_out(self) -> bool:
        if self.timeout_seconds is None:
            return False
        return self.elapsed > self.timeout_seconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "assigned_agent": self.assigned_agent,
            "delegated_from": self.delegated_from,
            "priority": self.priority,
            "timeout_seconds": self.timeout_seconds,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "elapsed": round(self.elapsed, 3),
            "is_cancelled": self._cancelled,
            "is_timed_out": self.is_timed_out,
        }

    def with_agent(self, agent_id: str) -> AgentExecutionContext:
        """Return a shallow copy with a different assigned agent."""
        return AgentExecutionContext(
            task_id=self.task_id,
            goal=self.goal,
            user_id=self.user_id,
            session_id=self.session_id,
            trace_id=self.trace_id,
            parent_span_id=self.parent_span_id,
            assigned_agent=agent_id,
            delegated_from=self.assigned_agent,
            priority=self.priority,
            timeout_seconds=self.timeout_seconds,
            metadata=dict(self.metadata),
            created_at=self.created_at,
        )

    def child(self, child_id: str | None = None) -> AgentExecutionContext:
        """Return a child context for delegation."""
        cid = child_id or str(uuid.uuid4())
        return AgentExecutionContext(
            task_id=cid,
            goal=self.goal,
            user_id=self.user_id,
            session_id=self.session_id,
            trace_id=self.trace_id,
            parent_span_id=None,
            assigned_agent=None,
            delegated_from=self.assigned_agent,
            priority=self.priority,
            timeout_seconds=self.timeout_seconds,
            metadata={**self.metadata, "parent_task_id": self.task_id},
        )
