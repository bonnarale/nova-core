"""Observability lifecycle — state machine for subsystem lifecycle."""

from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ObservabilityLifecycleState(str, Enum):
    REGISTERED = "registered"
    INITIALIZED = "initialized"
    READY = "ready"
    RUNNING = "running"
    DEGRADED = "degraded"
    FAILED = "failed"
    SHUTDOWN = "shutdown"


_VALID_TRANSITIONS: dict[ObservabilityLifecycleState, set[ObservabilityLifecycleState]] = {
    ObservabilityLifecycleState.REGISTERED: {
        ObservabilityLifecycleState.INITIALIZED,
        ObservabilityLifecycleState.SHUTDOWN,
    },
    ObservabilityLifecycleState.INITIALIZED: {
        ObservabilityLifecycleState.READY,
        ObservabilityLifecycleState.SHUTDOWN,
    },
    ObservabilityLifecycleState.READY: {
        ObservabilityLifecycleState.RUNNING,
        ObservabilityLifecycleState.SHUTDOWN,
    },
    ObservabilityLifecycleState.RUNNING: {
        ObservabilityLifecycleState.DEGRADED,
        ObservabilityLifecycleState.FAILED,
        ObservabilityLifecycleState.SHUTDOWN,
    },
    ObservabilityLifecycleState.DEGRADED: {
        ObservabilityLifecycleState.RUNNING,
        ObservabilityLifecycleState.FAILED,
        ObservabilityLifecycleState.SHUTDOWN,
    },
    ObservabilityLifecycleState.FAILED: {
        ObservabilityLifecycleState.RUNNING,
        ObservabilityLifecycleState.SHUTDOWN,
    },
    ObservabilityLifecycleState.SHUTDOWN: set(),
}


class ObservabilityLifecycle:
    """State machine managing observability subsystem lifecycle."""

    def __init__(self) -> None:
        self._state = ObservabilityLifecycleState.REGISTERED
        self._started_at: Optional[float] = None
        self._stopped_at: Optional[float] = None
        self._transition_history: list[tuple[ObservabilityLifecycleState, ObservabilityLifecycleState, float]] = []

    @property
    def state(self) -> ObservabilityLifecycleState:
        return self._state

    @property
    def started_at(self) -> Optional[float]:
        return self._started_at

    @property
    def stopped_at(self) -> Optional[float]:
        return self._stopped_at

    @property
    def uptime_seconds(self) -> float:
        if not self._started_at:
            return 0.0
        end = self._stopped_at or time.monotonic()
        return end - self._started_at

    @property
    def transition_history(self) -> list[tuple[ObservabilityLifecycleState, ObservabilityLifecycleState, float]]:
        return list(self._transition_history)

    def transition(self, target: ObservabilityLifecycleState) -> bool:
        if target == self._state:
            return True
        valid = _VALID_TRANSITIONS.get(self._state, set())
        if target not in valid:
            logger.warning(
                "Invalid observability lifecycle transition: %s -> %s",
                self._state.value,
                target.value,
            )
            return False
        now = time.monotonic()
        self._transition_history.append((self._state, target, now))
        self._state = target
        if target == ObservabilityLifecycleState.RUNNING and not self._started_at:
            self._started_at = now
        if target in (ObservabilityLifecycleState.FAILED, ObservabilityLifecycleState.SHUTDOWN):
            self._stopped_at = now
        logger.info("Observability lifecycle: %s -> %s", self._transition_history[-1][0].value, target.value)
        return True

    def can_transition(self, target: ObservabilityLifecycleState) -> bool:
        return target in _VALID_TRANSITIONS.get(self._state, set())

    def reset(self) -> None:
        self._state = ObservabilityLifecycleState.REGISTERED
        self._started_at = None
        self._stopped_at = None
        self._transition_history.clear()
