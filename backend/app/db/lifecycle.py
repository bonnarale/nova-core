"""Lifecycle state machine for the Database Architecture."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.db.enums import LifecycleState

logger = logging.getLogger(__name__)


class DatabaseLifecycle:
    """State machine managing the database architecture lifecycle."""

    _TRANSITIONS: dict[LifecycleState, set[LifecycleState]] = {
        LifecycleState.REGISTERED: {LifecycleState.INITIALIZED},
        LifecycleState.INITIALIZED: {LifecycleState.READY, LifecycleState.FAILED},
        LifecycleState.READY: {LifecycleState.RUNNING, LifecycleState.FAILED, LifecycleState.SHUTDOWN},
        LifecycleState.RUNNING: {LifecycleState.DEGRADED, LifecycleState.FAILED, LifecycleState.SHUTDOWN, LifecycleState.READY},
        LifecycleState.DEGRADED: {LifecycleState.RUNNING, LifecycleState.FAILED, LifecycleState.SHUTDOWN},
        LifecycleState.FAILED: {LifecycleState.SHUTDOWN},
        LifecycleState.SHUTDOWN: set(),
    }

    def __init__(self) -> None:
        self._state = LifecycleState.REGISTERED
        self._history: list[dict[str, Any]] = []
        self._state_times: dict[str, float] = {LifecycleState.REGISTERED.value: time.time()}

    @property
    def state(self) -> LifecycleState:
        return self._state

    def transition(self, target: LifecycleState, reason: str = "") -> bool:
        if target not in self._TRANSITIONS.get(self._state, set()):
            return False
        old = self._state
        self._state = target
        self._state_times[target.value] = time.time()
        self._history.append({
            "from": old.value,
            "to": target.value,
            "reason": reason,
            "timestamp": time.time(),
        })
        return True

    def is_running(self) -> bool:
        return self._state == LifecycleState.RUNNING

    def is_ready(self) -> bool:
        return self._state in (LifecycleState.READY, LifecycleState.RUNNING)

    def can_accept_operations(self) -> bool:
        return self._state in (LifecycleState.RUNNING, LifecycleState.READY, LifecycleState.DEGRADED)

    def get_history(self) -> list[dict[str, Any]]:
        return list(self._history)

    def get_status(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "can_accept_operations": self.can_accept_operations(),
            "transitions": len(self._history),
        }
