"""Lifecycle state machine for the Deployment subsystem."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.deployment.enums import DeployState

logger = logging.getLogger(__name__)


class DeploymentLifecycle:
    """State machine managing the deployment lifecycle."""

    _TRANSITIONS: dict[DeployState, set[DeployState]] = {
        DeployState.REGISTERED: {DeployState.INITIALIZING},
        DeployState.INITIALIZING: {DeployState.STARTING, DeployState.FAILED},
        DeployState.STARTING: {DeployState.RUNNING, DeployState.FAILED},
        DeployState.RUNNING: {
            DeployState.DEGRADED,
            DeployState.SHUTTING_DOWN,
            DeployState.FAILED,
        },
        DeployState.DEGRADED: {
            DeployState.RUNNING,
            DeployState.SHUTTING_DOWN,
            DeployState.FAILED,
        },
        DeployState.SHUTTING_DOWN: {DeployState.STOPPED, DeployState.FAILED},
        DeployState.STOPPED: {DeployState.INITIALIZING},
        DeployState.FAILED: {DeployState.INITIALIZING, DeployState.SHUTTING_DOWN},
    }

    def __init__(self) -> None:
        self._state = DeployState.REGISTERED
        self._history: list[dict[str, Any]] = []
        self._state_times: dict[str, float] = {
            DeployState.REGISTERED.value: time.time(),
        }
        self._start_time: float = 0.0

    @property
    def state(self) -> DeployState:
        return self._state

    def transition(self, target: DeployState, reason: str = "") -> bool:
        if target not in self._TRANSITIONS.get(self._state, set()):
            return False
        old = self._state
        self._state = target
        self._state_times[target.value] = time.time()
        if target == DeployState.RUNNING and self._start_time == 0.0:
            self._start_time = time.time()
        self._history.append({
            "from": old.value,
            "to": target.value,
            "reason": reason,
            "timestamp": time.time(),
        })
        logger.info("Deployment lifecycle: %s -> %s (%s)", old.value, target.value, reason)
        return True

    def is_running(self) -> bool:
        return self._state == DeployState.RUNNING

    def is_ready(self) -> bool:
        return self._state in (DeployState.RUNNING, DeployState.DEGRADED)

    def can_accept_traffic(self) -> bool:
        return self._state in (DeployState.RUNNING, DeployState.DEGRADED)

    def uptime(self) -> float:
        if self._start_time == 0.0:
            return 0.0
        return time.time() - self._start_time

    def get_history(self) -> list[dict[str, Any]]:
        return list(self._history)

    def get_status(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "is_running": self.is_running(),
            "is_ready": self.is_ready(),
            "can_accept_traffic": self.can_accept_traffic(),
            "uptime_seconds": self.uptime(),
            "transitions": len(self._history),
        }
