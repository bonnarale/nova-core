"""Scheduler lifecycle — state machine for scheduler subsystem lifecycle."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from app.scheduler.schemas import SchedulerLifecycleState

logger = logging.getLogger(__name__)

_VALID_TRANSITIONS: dict[SchedulerLifecycleState, set[SchedulerLifecycleState]] = {
    SchedulerLifecycleState.REGISTERED: {SchedulerLifecycleState.INITIALIZED, SchedulerLifecycleState.SHUTDOWN},
    SchedulerLifecycleState.INITIALIZED: {SchedulerLifecycleState.READY, SchedulerLifecycleState.SHUTDOWN},
    SchedulerLifecycleState.READY: {SchedulerLifecycleState.RUNNING, SchedulerLifecycleState.PAUSED, SchedulerLifecycleState.STOPPED, SchedulerLifecycleState.SHUTDOWN},
    SchedulerLifecycleState.RUNNING: {SchedulerLifecycleState.PAUSED, SchedulerLifecycleState.STOPPED, SchedulerLifecycleState.FAILED, SchedulerLifecycleState.SHUTDOWN},
    SchedulerLifecycleState.PAUSED: {SchedulerLifecycleState.RUNNING, SchedulerLifecycleState.STOPPED, SchedulerLifecycleState.SHUTDOWN},
    SchedulerLifecycleState.FAILED: {SchedulerLifecycleState.RUNNING, SchedulerLifecycleState.SHUTDOWN},
    SchedulerLifecycleState.STOPPED: {SchedulerLifecycleState.RUNNING, SchedulerLifecycleState.SHUTDOWN},
    SchedulerLifecycleState.SHUTDOWN: set(),
}


class SchedulerLifecycle:
    """State machine managing scheduler subsystem lifecycle."""

    def __init__(self) -> None:
        self._state = SchedulerLifecycleState.REGISTERED
        self._started_at: Optional[datetime] = None
        self._stopped_at: Optional[datetime] = None
        self._transition_history: list[tuple[SchedulerLifecycleState, SchedulerLifecycleState, datetime]] = []

    @property
    def state(self) -> SchedulerLifecycleState:
        return self._state

    @property
    def started_at(self) -> Optional[datetime]:
        return self._started_at

    @property
    def stopped_at(self) -> Optional[datetime]:
        return self._stopped_at

    @property
    def uptime_seconds(self) -> float:
        if not self._started_at:
            return 0.0
        end = self._stopped_at or datetime.now(timezone.utc)
        return (end - self._started_at).total_seconds()

    @property
    def transition_history(self) -> list[tuple[SchedulerLifecycleState, SchedulerLifecycleState, datetime]]:
        return list(self._transition_history)

    def transition(self, target: SchedulerLifecycleState) -> bool:
        if target == self._state:
            return True
        valid = _VALID_TRANSITIONS.get(self._state, set())
        if target not in valid:
            logger.warning("Invalid lifecycle transition: %s -> %s", self._state.value, target.value)
            return False
        now = datetime.now(timezone.utc)
        self._transition_history.append((self._state, target, now))
        self._state = target
        if target == SchedulerLifecycleState.RUNNING and not self._started_at:
            self._started_at = now
        if target in (SchedulerLifecycleState.STOPPED, SchedulerLifecycleState.SHUTDOWN):
            self._stopped_at = now
        logger.info("Lifecycle transition: %s -> %s", self._transition_history[-1][0].value, target.value)
        return True

    def can_transition(self, target: SchedulerLifecycleState) -> bool:
        return target in _VALID_TRANSITIONS.get(self._state, set())

    def reset(self) -> None:
        self._state = SchedulerLifecycleState.REGISTERED
        self._started_at = None
        self._stopped_at = None
        self._transition_history.clear()
