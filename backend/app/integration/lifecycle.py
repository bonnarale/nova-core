"""Integration lifecycle management."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from app.integration.enums import IntegrationState

logger = logging.getLogger(__name__)

_VALID_TRANSITIONS: dict[IntegrationState, set[IntegrationState]] = {
    IntegrationState.REGISTERED: {IntegrationState.DISCOVERING, IntegrationState.FAILED},
    IntegrationState.DISCOVERING: {IntegrationState.VALIDATED, IntegrationState.FAILED},
    IntegrationState.VALIDATED: {IntegrationState.INITIALIZING, IntegrationState.FAILED},
    IntegrationState.INITIALIZING: {IntegrationState.READY, IntegrationState.FAILED},
    IntegrationState.READY: {IntegrationState.RUNNING, IntegrationState.SHUTTING_DOWN, IntegrationState.FAILED},
    IntegrationState.RUNNING: {IntegrationState.DEGRADED, IntegrationState.SHUTTING_DOWN, IntegrationState.FAILED},
    IntegrationState.DEGRADED: {IntegrationState.RUNNING, IntegrationState.SHUTTING_DOWN, IntegrationState.FAILED},
    IntegrationState.SHUTTING_DOWN: {IntegrationState.SHUTDOWN, IntegrationState.FAILED},
    IntegrationState.SHUTDOWN: set(),
    IntegrationState.FAILED: {IntegrationState.REGISTERED},
}


class IntegrationLifecycle:
    """Thread-safe lifecycle manager for the integration layer."""

    def __init__(self) -> None:
        self._state = IntegrationState.REGISTERED
        self._history: list[dict[str, Any]] = []
        self._state_times: dict[str, float] = {
            IntegrationState.REGISTERED.value: time.time(),
        }
        self._lock = threading.RLock()

    @property
    def state(self) -> IntegrationState:
        with self._lock:
            return self._state

    def transition(self, target: IntegrationState, reason: str = "") -> bool:
        with self._lock:
            if target not in _VALID_TRANSITIONS.get(self._state, set()):
                logger.warning(
                    "Invalid transition: %s -> %s", self._state.value, target.value
                )
                return False
            old = self._state
            self._state = target
            self._state_times[target.value] = time.time()
            entry = {
                "from": old.value,
                "to": target.value,
                "reason": reason,
                "timestamp": time.time(),
            }
            self._history.append(entry)
            logger.info("Transition: %s -> %s (%s)", old.value, target.value, reason)
            return True

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            now = time.time()
            uptime = now - self._state_times.get(IntegrationState.REGISTERED.value, now)
            return {
                "state": self._state.value,
                "uptime_seconds": uptime,
                "state_times": dict(self._state_times),
                "transitions": len(self._history),
            }

    def get_history(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._history)

    def is_running(self) -> bool:
        with self._lock:
            return self._state == IntegrationState.RUNNING

    def reset(self) -> None:
        with self._lock:
            self._state = IntegrationState.REGISTERED
            self._history.clear()
            self._state_times = {IntegrationState.REGISTERED.value: time.time()}
