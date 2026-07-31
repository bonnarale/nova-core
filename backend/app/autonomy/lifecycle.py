"""Lifecycle management for the autonomy subsystem."""

from __future__ import annotations

import threading
import time
from typing import Any

from app.autonomy.enums import AutonomyState


_VALID_TRANSITIONS: dict[AutonomyState, set[AutonomyState]] = {
    AutonomyState.REGISTERED: {AutonomyState.INITIALIZED, AutonomyState.FAILED},
    AutonomyState.INITIALIZED: {AutonomyState.READY, AutonomyState.FAILED},
    AutonomyState.READY: {AutonomyState.OBSERVING, AutonomyState.SHUTDOWN, AutonomyState.FAILED},
    AutonomyState.OBSERVING: {AutonomyState.ANALYZING, AutonomyState.READY, AutonomyState.FAILED},
    AutonomyState.ANALYZING: {AutonomyState.RECOMMENDING, AutonomyState.OBSERVING, AutonomyState.FAILED},
    AutonomyState.RECOMMENDING: {AutonomyState.APPROVED, AutonomyState.ANALYZING, AutonomyState.FAILED},
    AutonomyState.APPROVED: {AutonomyState.EXECUTING, AutonomyState.RECOMMENDING, AutonomyState.FAILED},
    AutonomyState.EXECUTING: {AutonomyState.LEARNING, AutonomyState.READY, AutonomyState.FAILED},
    AutonomyState.LEARNING: {AutonomyState.OBSERVING, AutonomyState.READY, AutonomyState.FAILED},
    AutonomyState.FAILED: {AutonomyState.REGISTERED},
    AutonomyState.SHUTDOWN: set(),
}


class AutonomyLifecycle:
    """Thread-safe lifecycle for the autonomy layer."""

    def __init__(self) -> None:
        self._state = AutonomyState.REGISTERED
        self._history: list[dict[str, Any]] = []
        self._start_time = time.time()
        self._lock = threading.RLock()

    @property
    def state(self) -> AutonomyState:
        with self._lock:
            return self._state

    def transition(self, target: AutonomyState, reason: str = "") -> bool:
        with self._lock:
            allowed = _VALID_TRANSITIONS.get(self._state, set())
            if target not in allowed:
                return False
            old = self._state
            self._state = target
            self._history.append({
                "from": old.value,
                "to": target.value,
                "reason": reason,
                "timestamp": time.time(),
            })
            return True

    def is_running(self) -> bool:
        with self._lock:
            return self._state not in (AutonomyState.SHUTDOWN, AutonomyState.FAILED, AutonomyState.REGISTERED)

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "state": self._state.value,
                "uptime_seconds": time.time() - self._start_time,
                "transitions": len(self._history),
            }

    def get_history(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._history)
