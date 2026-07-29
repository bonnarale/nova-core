"""Lifecycle management for the enterprise subsystem."""

from __future__ import annotations

import threading
import time
from typing import Any

from app.enterprise.enums import EnterpriseState


_VALID_TRANSITIONS: dict[EnterpriseState, set[EnterpriseState]] = {
    EnterpriseState.REGISTERED: {EnterpriseState.INITIALIZED, EnterpriseState.DELETED},
    EnterpriseState.INITIALIZED: {EnterpriseState.READY, EnterpriseState.DELETED},
    EnterpriseState.READY: {EnterpriseState.ACTIVE, EnterpriseState.SUSPENDED, EnterpriseState.ARCHIVED, EnterpriseState.DELETED},
    EnterpriseState.ACTIVE: {EnterpriseState.SUSPENDED, EnterpriseState.ARCHIVED, EnterpriseState.DELETED},
    EnterpriseState.SUSPENDED: {EnterpriseState.ACTIVE, EnterpriseState.ARCHIVED, EnterpriseState.DELETED},
    EnterpriseState.ARCHIVED: {EnterpriseState.DELETED},
    EnterpriseState.DELETED: set(),
}


class EnterpriseLifecycle:
    """Thread-safe lifecycle for the enterprise layer."""

    def __init__(self) -> None:
        self._state = EnterpriseState.REGISTERED
        self._history: list[dict[str, Any]] = []
        self._start_time = time.time()
        self._lock = threading.RLock()

    @property
    def state(self) -> EnterpriseState:
        with self._lock:
            return self._state

    def transition(self, target: EnterpriseState, reason: str = "") -> bool:
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
            return self._state not in (EnterpriseState.SHUTDOWN if hasattr(EnterpriseState, "SHUTDOWN") else EnterpriseState.DELETED, EnterpriseState.DELETED, EnterpriseState.REGISTERED)

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
