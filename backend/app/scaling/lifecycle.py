"""Lifecycle state machine for the Scaling subsystem."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.scaling.enums import ScalingState

logger = logging.getLogger(__name__)


class ScalingLifecycle:
    """State machine managing the scaling subsystem lifecycle."""

    _TRANSITIONS: dict[ScalingState, set[ScalingState]] = {
        ScalingState.REGISTERED: {ScalingState.INITIALIZED},
        ScalingState.INITIALIZED: {ScalingState.READY, ScalingState.FAILED},
        ScalingState.READY: {ScalingState.RUNNING, ScalingState.FAILED, ScalingState.SHUTDOWN},
        ScalingState.RUNNING: {
            ScalingState.SCALING_UP,
            ScalingState.SCALING_DOWN,
            ScalingState.DEGRADED,
            ScalingState.FAILED,
            ScalingState.SHUTDOWN,
        },
        ScalingState.SCALING_UP: {ScalingState.RUNNING, ScalingState.DEGRADED, ScalingState.FAILED},
        ScalingState.SCALING_DOWN: {ScalingState.RUNNING, ScalingState.DEGRADED, ScalingState.FAILED},
        ScalingState.DEGRADED: {ScalingState.RUNNING, ScalingState.FAILED, ScalingState.SHUTDOWN},
        ScalingState.FAILED: {ScalingState.INITIALIZED, ScalingState.SHUTDOWN},
        ScalingState.SHUTDOWN: set(),
    }

    def __init__(self) -> None:
        self._state = ScalingState.REGISTERED
        self._history: list[dict[str, Any]] = []
        self._state_times: dict[str, float] = {
            ScalingState.REGISTERED.value: time.time(),
        }

    @property
    def state(self) -> ScalingState:
        return self._state

    def transition(self, target: ScalingState, reason: str = "") -> bool:
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
        logger.info("Scaling lifecycle: %s -> %s (%s)", old.value, target.value, reason)
        return True

    def is_running(self) -> bool:
        return self._state == ScalingState.RUNNING

    def is_scaling(self) -> bool:
        return self._state in (ScalingState.SCALING_UP, ScalingState.SCALING_DOWN)

    def can_operate(self) -> bool:
        return self._state in (ScalingState.RUNNING, ScalingState.DEGRADED, ScalingState.SCALING_UP, ScalingState.SCALING_DOWN)

    def get_history(self) -> list[dict[str, Any]]:
        return list(self._history)

    def get_status(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "is_running": self.is_running(),
            "is_scaling": self.is_scaling(),
            "can_operate": self.can_operate(),
            "transitions": len(self._history),
        }
