"""RAG lifecycle — state machine for RAG engine components."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RAGState(str, Enum):
    REGISTERED = "registered"
    INITIALIZED = "initialized"
    READY = "ready"
    INDEXING = "indexing"
    RETRIEVING = "retrieving"
    FAILED = "failed"
    SHUTDOWN = "shutdown"


VALID_RAG_TRANSITIONS: dict[RAGState, set[RAGState]] = {
    RAGState.REGISTERED: {RAGState.INITIALIZED, RAGState.FAILED, RAGState.SHUTDOWN},
    RAGState.INITIALIZED: {RAGState.READY, RAGState.FAILED, RAGState.SHUTDOWN},
    RAGState.READY: {RAGState.INDEXING, RAGState.RETRIEVING, RAGState.FAILED, RAGState.SHUTDOWN},
    RAGState.INDEXING: {RAGState.READY, RAGState.FAILED},
    RAGState.RETRIEVING: {RAGState.READY, RAGState.FAILED},
    RAGState.FAILED: {RAGState.REGISTERED, RAGState.SHUTDOWN},
    RAGState.SHUTDOWN: {RAGState.REGISTERED},
}


class RAGLifecycleError(Exception):
    """Raised on invalid lifecycle transition."""


class RAGLifecycle:
    """Manages lifecycle state for a RAG component."""

    def __init__(self, component_id: str) -> None:
        self._component_id = component_id
        self._state = RAGState.REGISTERED
        self._state_history: list[dict[str, Any]] = []
        self._error_count = 0
        self._last_error: Optional[str] = None

    @property
    def component_id(self) -> str:
        return self._component_id

    @property
    def state(self) -> RAGState:
        return self._state

    @property
    def is_ready(self) -> bool:
        return self._state == RAGState.READY

    @property
    def is_available(self) -> bool:
        return self._state in (RAGState.READY, RAGState.INDEXING, RAGState.RETRIEVING)

    @property
    def error_count(self) -> int:
        return self._error_count

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def transition_to(self, new_state: RAGState, reason: str = "") -> None:
        if new_state not in VALID_RAG_TRANSITIONS.get(self._state, set()):
            raise RAGLifecycleError(
                f"Invalid transition: {self._state.value} -> {new_state.value}"
            )
        old_state = self._state
        self._state = new_state
        entry = {
            "from": old_state.value,
            "to": new_state.value,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._state_history.append(entry)
        if new_state == RAGState.FAILED:
            self._error_count += 1
            self._last_error = reason
        logger.debug("RAG %s: %s -> %s (%s)", self._component_id, old_state.value, new_state.value, reason)

    def initialized(self) -> None:
        self.transition_to(RAGState.INITIALIZED, "Initialization complete")

    def ready(self) -> None:
        self.transition_to(RAGState.READY, "Ready for operations")

    def indexing(self) -> None:
        self.transition_to(RAGState.INDEXING, "Indexing documents")

    def retrieving(self) -> None:
        self.transition_to(RAGState.RETRIEVING, "Retrieving documents")

    def failed(self, reason: str = "Unknown error") -> None:
        self.transition_to(RAGState.FAILED, reason)

    def shutdown(self) -> None:
        self.transition_to(RAGState.SHUTDOWN, "Shutdown complete")

    def recover(self) -> None:
        if self._state in (RAGState.FAILED, RAGState.SHUTDOWN):
            self.transition_to(RAGState.REGISTERED, "Recovery")

    def get_history(self) -> list[dict[str, Any]]:
        return list(self._state_history)

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self._component_id,
            "state": self._state.value,
            "is_ready": self.is_ready,
            "is_available": self.is_available,
            "error_count": self._error_count,
            "last_error": self._last_error,
            "history": self._state_history[-10:],
        }
