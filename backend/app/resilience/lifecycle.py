"""Resilience lifecycle management."""

from __future__ import annotations

import threading
import time
from typing import Any

from app.resilience.enums import ResilienceState


_VALID_TRANSITIONS: dict[ResilienceState, set[ResilienceState]] = {
    ResilienceState.REGISTERED: {ResilienceState.INITIALIZED, ResilienceState.FAILED},
    ResilienceState.INITIALIZED: {ResilienceState.READY, ResilienceState.FAILED},
    ResilienceState.READY: {ResilienceState.RUNNING, ResilienceState.SHUTDOWN, ResilienceState.FAILED},
    ResilienceState.RUNNING: {ResilienceState.DEGRADED, ResilienceState.RECOVERING, ResilienceState.SHUTDOWN, ResilienceState.FAILED},
    ResilienceState.DEGRADED: {ResilienceState.RUNNING, ResilienceState.RECOVERING, ResilienceState.SHUTDOWN, ResilienceState.FAILED},
    ResilienceState.RECOVERING: {ResilienceState.RUNNING, ResilienceState.DEGRADED, ResilienceState.FAILED},
    ResilienceState.FAILED: {ResilienceState.RECOVERING, ResilienceState.REGISTERED},
    ResilienceState.SHUTDOWN: set(),
}


class ResilienceLifecycle:
    """Thread-safe lifecycle for the resilience layer."""

    def __init__(self) -> None:
        self._state = ResilienceState.REGISTERED
        self._history: list[dict[str, Any]] = []
        self._state_times: dict[str, float] = {ResilienceState.REGISTERED.value: time.time()}
        self._lock = threading.RLock()

    @property
    def state(self) -> ResilienceState:
        with self._lock:
            return self._state

    def transition(self, target: ResilienceState, reason: str = "") -> bool:
        with self._lock:
            if target not in _VALID_TRANSITIONS.get(self._state, set()):
                return False
            old = self._state
            self._state = target
            self._state_times[target.value] = time.time()
            self._history.append({"from": old.value, "to": target.value, "reason": reason, "timestamp": time.time()})
            return True

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            now = time.time()
            uptime = now - self._state_times.get(ResilienceState.REGISTERED.value, now)
            return {"state": self._state.value, "uptime_seconds": uptime, "transitions": len(self._history)}

    def get_history(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._history)

    def is_running(self) -> bool:
        with self._lock:
            return self._state == ResilienceState.RUNNING
