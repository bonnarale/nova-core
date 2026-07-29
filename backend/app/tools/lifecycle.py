"""Tool lifecycle state machine."""

from __future__ import annotations

import time
from enum import Enum
from typing import Any


class ToolState(str, Enum):
    REGISTERED = "registered"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    SUSPENDED = "suspended"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN = "shutdown"


VALID_TRANSITIONS: dict[ToolState, set[ToolState]] = {
    ToolState.REGISTERED: {ToolState.INITIALIZING, ToolState.SHUTDOWN},
    ToolState.INITIALIZING: {ToolState.READY, ToolState.ERROR},
    ToolState.READY: {ToolState.RUNNING, ToolState.SUSPENDED, ToolState.SHUTTING_DOWN, ToolState.ERROR},
    ToolState.RUNNING: {ToolState.READY, ToolState.ERROR, ToolState.SHUTTING_DOWN},
    ToolState.SUSPENDED: {ToolState.READY, ToolState.SHUTTING_DOWN},
    ToolState.ERROR: {ToolState.READY, ToolState.SHUTTING_DOWN},
    ToolState.SHUTTING_DOWN: {ToolState.SHUTDOWN},
    ToolState.SHUTDOWN: set(),
}


class ToolLifecycle:
    """Tracks the lifecycle of a single tool."""

    def __init__(self, tool_id: str) -> None:
        self.tool_id = tool_id
        self._state = ToolState.REGISTERED
        self._history: list[dict[str, Any]] = []
        self._created_at = time.time()
        self._last_transition = time.time()
        self._record(ToolState.REGISTERED)

    @property
    def state(self) -> ToolState:
        return self._state

    def transition(self, target: ToolState) -> bool:
        allowed = VALID_TRANSITIONS.get(self._state, set())
        if target not in allowed:
            return False
        self._state = target
        self._last_transition = time.time()
        self._record(target)
        return True

    def initialize(self) -> bool:
        return self.transition(ToolState.INITIALIZING)

    def ready(self) -> bool:
        return self.transition(ToolState.READY)

    def start(self) -> bool:
        return self.transition(ToolState.RUNNING)

    def complete(self) -> bool:
        return self.transition(ToolState.READY)

    def suspend(self) -> bool:
        return self.transition(ToolState.SUSPENDED)

    def resume(self) -> bool:
        return self.transition(ToolState.READY)

    def fail(self) -> bool:
        return self.transition(ToolState.ERROR)

    def recover(self) -> bool:
        return self.transition(ToolState.READY)

    def shutdown(self) -> bool:
        if self._state == ToolState.SHUTDOWN:
            return True
        if self._state in (ToolState.REGISTERED, ToolState.INITIALIZING):
            self._state = ToolState.SHUTDOWN
            self._record(ToolState.SHUTDOWN)
            return True
        return self.transition(ToolState.SHUTTING_DOWN) and self.transition(ToolState.SHUTDOWN)

    @property
    def is_ready(self) -> bool:
        return self._state == ToolState.READY

    @property
    def is_running(self) -> bool:
        return self._state == ToolState.RUNNING

    @property
    def is_terminal(self) -> bool:
        return self._state == ToolState.SHUTDOWN

    def _record(self, state: ToolState) -> None:
        self._history.append({
            "state": state.value,
            "timestamp": time.time(),
        })

    @property
    def history(self) -> list[dict[str, Any]]:
        return list(self._history)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "state": self._state.value,
            "created_at": self._created_at,
            "last_transition": self._last_transition,
            "history": list(self._history),
        }
