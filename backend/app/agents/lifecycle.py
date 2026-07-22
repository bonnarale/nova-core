"""Agent lifecycle state machine."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    REGISTERED = "REGISTERED"
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SHUTDOWN = "SHUTDOWN"


_VALID_TRANSITIONS: dict[AgentState, set[AgentState]] = {
    AgentState.REGISTERED: {AgentState.INITIALIZING, AgentState.FAILED, AgentState.SHUTDOWN},
    AgentState.INITIALIZING: {AgentState.READY, AgentState.FAILED, AgentState.SHUTDOWN},
    AgentState.READY: {AgentState.RUNNING, AgentState.SHUTDOWN, AgentState.FAILED},
    AgentState.RUNNING: {
        AgentState.COMPLETED,
        AgentState.FAILED,
        AgentState.WAITING,
        AgentState.BLOCKED,
        AgentState.CANCELLED,
    },
    AgentState.WAITING: {AgentState.RUNNING, AgentState.FAILED, AgentState.CANCELLED},
    AgentState.BLOCKED: {AgentState.RUNNING, AgentState.FAILED, AgentState.CANCELLED},
    AgentState.COMPLETED: {AgentState.READY},
    AgentState.FAILED: {AgentState.READY, AgentState.SHUTDOWN},
    AgentState.CANCELLED: {AgentState.READY, AgentState.SHUTDOWN},
    AgentState.SHUTDOWN: set(),
}


class AgentLifecycle:
    """Manages the lifecycle state machine for a single agent instance."""

    def __init__(self, agent_id: str, initial: AgentState = AgentState.REGISTERED) -> None:
        self._agent_id = agent_id
        self._state = initial
        self._history: list[dict[str, Any]] = []
        self._transitions_count = 0

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def history(self) -> list[dict[str, Any]]:
        return list(self._history)

    @property
    def transitions_count(self) -> int:
        return self._transitions_count

    def can_transition_to(self, target: AgentState) -> bool:
        return target in _VALID_TRANSITIONS.get(self._state, set())

    def transition_to(self, target: AgentState, reason: str = "") -> bool:
        if not self.can_transition_to(target):
            logger.warning(
                "Lifecycle: %s invalid transition %s -> %s",
                self._agent_id, self._state.value, target.value,
            )
            return False

        previous = self._state
        self._state = target
        self._transitions_count += 1

        import time
        entry = {
            "from": previous.value,
            "to": target.value,
            "reason": reason,
            "timestamp": time.time(),
        }
        self._history.append(entry)

        logger.debug(
            "Lifecycle: %s %s -> %s (%s)",
            self._agent_id, previous.value, target.value, reason or "ok",
        )
        return True

    def register(self) -> bool:
        return self.transition_to(AgentState.INITIALIZING, "agent registered")

    def initialize(self) -> bool:
        return self.transition_to(AgentState.READY, "initialization complete")

    def start_running(self) -> bool:
        return self.transition_to(AgentState.RUNNING, "execution started")

    def wait(self, reason: str = "waiting") -> bool:
        return self.transition_to(AgentState.WAITING, reason)

    def unblock(self) -> bool:
        return self.transition_to(AgentState.RUNNING, "unblocked")

    def block(self, reason: str = "blocked") -> bool:
        return self.transition_to(AgentState.BLOCKED, reason)

    def complete(self) -> bool:
        return self.transition_to(AgentState.COMPLETED, "execution completed")

    def fail(self, reason: str = "failed") -> bool:
        return self.transition_to(AgentState.FAILED, reason)

    def cancel(self, reason: str = "cancelled") -> bool:
        return self.transition_to(AgentState.CANCELLED, reason)

    def shutdown(self, reason: str = "shutdown") -> bool:
        return self.transition_to(AgentState.SHUTDOWN, reason)

    def reset_to_ready(self) -> bool:
        if self._state in (AgentState.COMPLETED, AgentState.FAILED, AgentState.CANCELLED):
            return self.transition_to(AgentState.READY, "reset")
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self._agent_id,
            "state": self._state.value,
            "transitions_count": self._transitions_count,
            "history": list(self._history),
        }
