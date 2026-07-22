"""Lifecycle management for model providers."""

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class ProviderState(str, Enum):
    """States in the provider lifecycle."""

    REGISTERED = "registered"
    INITIALIZING = "initializing"
    READY = "ready"
    HEALTH_CHECKING = "health_checking"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN = "shutdown"
    ERROR = "error"


class ProviderTransitionError(Exception):
    """Raised when an invalid lifecycle transition is attempted."""


VALID_TRANSITIONS = {
    ProviderState.REGISTERED: {ProviderState.INITIALIZING, ProviderState.ERROR},
    ProviderState.INITIALIZING: {ProviderState.READY, ProviderState.ERROR},
    ProviderState.READY: {ProviderState.HEALTH_CHECKING, ProviderState.SHUTTING_DOWN, ProviderState.ERROR},
    ProviderState.HEALTH_CHECKING: {ProviderState.READY, ProviderState.DEGRADED, ProviderState.UNHEALTHY},
    ProviderState.DEGRADED: {ProviderState.HEALTH_CHECKING, ProviderState.READY, ProviderState.SHUTTING_DOWN, ProviderState.ERROR},
    ProviderState.UNHEALTHY: {ProviderState.HEALTH_CHECKING, ProviderState.SHUTTING_DOWN, ProviderState.REGISTERED},
    ProviderState.SHUTTING_DOWN: {ProviderState.SHUTDOWN, ProviderState.ERROR},
    ProviderState.SHUTDOWN: {ProviderState.REGISTERED},
    ProviderState.ERROR: {ProviderState.REGISTERED, ProviderState.SHUTTING_DOWN},
}


class ProviderLifecycle:
    """Manages the lifecycle of a model provider."""

    def __init__(self, provider_id: str) -> None:
        self._provider_id = provider_id
        self._state = ProviderState.REGISTERED
        self._state_history: list[dict[str, Any]] = []
        self._transitions: dict[tuple[ProviderState, ProviderState], Callable] = {}
        self._health_check_interval: float = 60.0
        self._last_health_check: Optional[datetime] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._error_message: Optional[str] = None
        self._error_count: int = 0

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def state(self) -> ProviderState:
        return self._state

    @property
    def is_healthy(self) -> bool:
        return self._state in (ProviderState.READY, ProviderState.HEALTH_CHECKING, ProviderState.DEGRADED)

    @property
    def is_available(self) -> bool:
        return self._state in (ProviderState.READY,)

    @property
    def error_message(self) -> Optional[str]:
        return self._error_message

    @property
    def error_count(self) -> int:
        return self._error_count

    def transition_to(self, new_state: ProviderState, reason: str = "") -> None:
        if new_state not in VALID_TRANSITIONS.get(self._state, set()):
            raise ProviderTransitionError(
                f"Invalid transition: {self._state.value} -> {new_state.value}"
            )
        old_state = self._state
        self._state = new_state
        self._state_history.append({
            "from": old_state.value,
            "to": new_state.value,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Provider %s: %s -> %s (%s)", self._provider_id, old_state.value, new_state.value, reason)
        if new_state == ProviderState.ERROR:
            self._error_count += 1
            self._error_message = reason

    def initialize(self) -> None:
        self.transition_to(ProviderState.INITIALIZING, "Initialization started")

    def ready(self) -> None:
        self.transition_to(ProviderState.READY, "Initialization complete")

    def health_checking(self) -> None:
        self.transition_to(ProviderState.HEALTH_CHECKING, "Health check started")

    def degraded(self, reason: str = "Health check degraded") -> None:
        self.transition_to(ProviderState.DEGRADED, reason)

    def unhealthy(self, reason: str = "Health check failed") -> None:
        self.transition_to(ProviderState.UNHEALTHY, reason)

    def shutting_down(self) -> None:
        self.transition_to(ProviderState.SHUTTING_DOWN, "Shutdown started")

    def shutdown(self) -> None:
        self.transition_to(ProviderState.SHUTDOWN, "Shutdown complete")

    def error(self, reason: str = "Unknown error") -> None:
        self.transition_to(ProviderState.ERROR, reason)

    def recover(self) -> None:
        if self._state == ProviderState.UNHEALTHY:
            self.transition_to(ProviderState.REGISTERED, "Recovery initiated")
        elif self._state == ProviderState.ERROR:
            self.transition_to(ProviderState.REGISTERED, "Recovery from error")

    def set_health_check_interval(self, interval: float) -> None:
        self._health_check_interval = interval

    def get_state_history(self) -> list[dict[str, Any]]:
        return list(self._state_history)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self._provider_id,
            "state": self._state.value,
            "is_healthy": self.is_healthy,
            "is_available": self.is_available,
            "error_message": self._error_message,
            "error_count": self._error_count,
            "state_history": self._state_history[-10:],
        }


def get_provider_lifecycle(provider_id: str) -> ProviderLifecycle:
    return ProviderLifecycle(provider_id)
