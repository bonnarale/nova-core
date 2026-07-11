"""Session management for kernel operations."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from app.kernel.context import ExecutionContext
from app.kernel.events import EventType, KernelEvent, emit

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """A kernel session representing an execution context."""

    session_id: UUID
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    _context: Optional[ExecutionContext] = None

    def end(self) -> None:
        """End the session."""
        self.is_active = False
        logger.info("Session ended: %s", self.session_id)
        emit(
            KernelEvent.create(
                event_type=EventType.SESSION_ENDED,
                session_id=self.session_id,
            )
        )

    def get_context(self) -> ExecutionContext:
        """Get or create the execution context for this session."""
        if self._context is None:
            self._context = ExecutionContext(session_id=self.session_id)
        return self._context


# Session registry
_sessions: dict[UUID, Session] = {}


def create_session(
    metadata: Optional[dict[str, Any]] = None,
    session_id: Optional[UUID] = None,
) -> Session:
    """Create and register a new session.

    Args:
        metadata: Optional metadata dict.
        session_id: Optional explicit session UUID. If omitted, a random one
                    is generated. Use this to restore a session from persistent
                    storage (e.g. a database record).

    Returns:
        The newly created Session.
    """
    sid = session_id or uuid4()
    session = Session(
        session_id=sid,
        created_at=datetime.now(timezone.utc),
        metadata=metadata or {},
    )
    _sessions[sid] = session
    logger.info("Session created: %s", sid)
    emit(
        KernelEvent.create(
            event_type=EventType.SESSION_STARTED,
            session_id=sid,
            payload={"metadata": session.metadata},
        )
    )
    return session


def get_session(session_id: UUID) -> Optional[Session]:
    """Get a session by ID."""
    return _sessions.get(session_id)


def end_session(session_id: UUID) -> bool:
    """End a session by ID."""
    session = _sessions.get(session_id)
    if session:
        session.end()
        del _sessions[session_id]
        return True
    return False


def get_active_sessions() -> list[Session]:
    """Get all active sessions."""
    return [s for s in _sessions.values() if s.is_active]