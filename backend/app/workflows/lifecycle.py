"""Workflow lifecycle — state machine for workflow engine subsystem lifecycle."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class WorkflowLifecycleState(str, Enum):
    REGISTERED = "registered"
    INITIALIZED = "initialized"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SHUTDOWN = "shutdown"


_VALID_TRANSITIONS: dict[WorkflowLifecycleState, set[WorkflowLifecycleState]] = {
    WorkflowLifecycleState.REGISTERED: {WorkflowLifecycleState.INITIALIZED, WorkflowLifecycleState.SHUTDOWN},
    WorkflowLifecycleState.INITIALIZED: {WorkflowLifecycleState.READY, WorkflowLifecycleState.SHUTDOWN},
    WorkflowLifecycleState.READY: {WorkflowLifecycleState.RUNNING, WorkflowLifecycleState.PAUSED, WorkflowLifecycleState.CANCELLED, WorkflowLifecycleState.SHUTDOWN},
    WorkflowLifecycleState.RUNNING: {WorkflowLifecycleState.WAITING, WorkflowLifecycleState.PAUSED, WorkflowLifecycleState.COMPLETED, WorkflowLifecycleState.FAILED, WorkflowLifecycleState.CANCELLED, WorkflowLifecycleState.SHUTDOWN},
    WorkflowLifecycleState.WAITING: {WorkflowLifecycleState.RUNNING, WorkflowLifecycleState.CANCELLED, WorkflowLifecycleState.SHUTDOWN},
    WorkflowLifecycleState.PAUSED: {WorkflowLifecycleState.RUNNING, WorkflowLifecycleState.CANCELLED, WorkflowLifecycleState.SHUTDOWN},
    WorkflowLifecycleState.COMPLETED: {WorkflowLifecycleState.SHUTDOWN},
    WorkflowLifecycleState.FAILED: {WorkflowLifecycleState.RUNNING, WorkflowLifecycleState.SHUTDOWN},
    WorkflowLifecycleState.CANCELLED: {WorkflowLifecycleState.SHUTDOWN},
    WorkflowLifecycleState.SHUTDOWN: set(),
}


class WorkflowLifecycle:
    """State machine managing workflow engine subsystem lifecycle."""

    def __init__(self) -> None:
        self._state = WorkflowLifecycleState.REGISTERED
        self._started_at: Optional[datetime] = None
        self._stopped_at: Optional[datetime] = None
        self._transition_history: list[tuple[WorkflowLifecycleState, WorkflowLifecycleState, datetime]] = []

    @property
    def state(self) -> WorkflowLifecycleState:
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
    def transition_history(self) -> list[tuple[WorkflowLifecycleState, WorkflowLifecycleState, datetime]]:
        return list(self._transition_history)

    def transition(self, target: WorkflowLifecycleState) -> bool:
        if target == self._state:
            return True
        valid = _VALID_TRANSITIONS.get(self._state, set())
        if target not in valid:
            logger.warning("Invalid workflow lifecycle transition: %s -> %s", self._state.value, target.value)
            return False
        now = datetime.now(timezone.utc)
        self._transition_history.append((self._state, target, now))
        self._state = target
        if target == WorkflowLifecycleState.RUNNING and not self._started_at:
            self._started_at = now
        if target in (WorkflowLifecycleState.CANCELLED, WorkflowLifecycleState.SHUTDOWN):
            self._stopped_at = now
        logger.info("Workflow lifecycle: %s -> %s", self._transition_history[-1][0].value, target.value)
        return True

    def can_transition(self, target: WorkflowLifecycleState) -> bool:
        return target in _VALID_TRANSITIONS.get(self._state, set())

    def reset(self) -> None:
        self._state = WorkflowLifecycleState.REGISTERED
        self._started_at = None
        self._stopped_at = None
        self._transition_history.clear()
