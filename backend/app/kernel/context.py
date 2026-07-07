"""Execution context for kernel operations."""

import logging
from contextvars import ContextVar
from typing import Any, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class ExecutionContext:
    """Context for a single execution within the kernel."""

    def __init__(
        self,
        session_id: Optional[UUID] = None,
        agent_id: Optional[str] = None,
        task_id: Optional[UUID] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        self.session_id = session_id or uuid4()
        self.agent_id = agent_id
        self.task_id = task_id or uuid4()
        self.metadata = metadata or {}
        self._variables: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        """Set a context variable."""
        self._variables[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a context variable."""
        return self._variables.get(key, default)

    def update(self, updates: dict[str, Any]) -> None:
        """Update multiple context variables."""
        self._variables.update(updates)


# Context variable for current execution context
current_context: ContextVar[Optional[ExecutionContext]] = ContextVar(
    "current_context", default=None
)


def get_current_context() -> Optional[ExecutionContext]:
    """Get the current execution context."""
    return current_context.get()


def set_current_context(context: ExecutionContext) -> None:
    """Set the current execution context."""
    current_context.set(context)