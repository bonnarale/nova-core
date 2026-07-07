"""Event system for kernel operations."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of kernel events."""

    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    AGENT_STARTED = "agent_started"
    AGENT_STOPPED = "agent_stopped"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"


@dataclass
class KernelEvent:
    """Base kernel event."""

    event_type: EventType
    timestamp: datetime
    session_id: Optional[UUID]
    task_id: Optional[UUID]
    agent_id: Optional[str]
    payload: dict[str, Any]
    event_id: UUID

    @classmethod
    def create(
        cls,
        event_type: EventType,
        session_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        agent_id: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
    ) -> "KernelEvent":
        """Create a new kernel event."""
        return cls(
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            session_id=session_id,
            task_id=task_id,
            agent_id=agent_id,
            payload=payload or {},
            event_id=uuid4(),
        )


# Event handlers registry
_event_handlers: dict[EventType, list[Callable[[KernelEvent], None]]] = {}


def register_handler(
    event_type: EventType, handler: Callable[[KernelEvent], None]
) -> None:
    """Register an event handler for a specific event type."""
    if event_type not in _event_handlers:
        _event_handlers[event_type] = []
    _event_handlers[event_type].append(handler)


def emit(event: KernelEvent) -> None:
    """Emit a kernel event to all registered handlers."""
    logger.debug(
        "Emitting event: %s, session_id: %s, task_id: %s, agent_id: %s",
        event.event_type,
        event.session_id,
        event.task_id,
        event.agent_id,
    )
    handlers = _event_handlers.get(event.event_type, [])
    for handler in handlers:
        try:
            handler(event)
        except Exception:
            # Log but don't fail - event handlers should be resilient
            logger.exception("Event handler failed for event: %s", event.event_type)


def clear_handlers() -> None:
    """Clear all registered event handlers."""
    _event_handlers.clear()