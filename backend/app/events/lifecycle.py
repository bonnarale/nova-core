"""Event lifecycle — state machine for event bus lifecycle management."""

from __future__ import annotations

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class EventLifecycleState(str, Enum):
    REGISTERED = "registered"
    INITIALIZED = "initialized"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    SHUTDOWN = "shutdown"


class EventLifecycle:
    """Manages the state machine for the event system."""

    def __init__(self, name: str = "event_bus") -> None:
        self._name = name
        self._state = EventLifecycleState.REGISTERED

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> EventLifecycleState:
        return self._state

    @property
    def is_registered(self) -> bool:
        return self._state == EventLifecycleState.REGISTERED

    @property
    def is_initialized(self) -> bool:
        return self._state == EventLifecycleState.INITIALIZED

    @property
    def is_ready(self) -> bool:
        return self._state == EventLifecycleState.READY

    @property
    def is_running(self) -> bool:
        return self._state == EventLifecycleState.RUNNING

    @property
    def is_paused(self) -> bool:
        return self._state == EventLifecycleState.PAUSED

    @property
    def is_failed(self) -> bool:
        return self._state == EventLifecycleState.FAILED

    @property
    def is_shutdown(self) -> bool:
        return self._state == EventLifecycleState.SHUTDOWN

    def initialized(self) -> None:
        self._transition(EventLifecycleState.INITIALIZED)

    def ready(self) -> None:
        self._transition(EventLifecycleState.READY)

    def running(self) -> None:
        self._transition(EventLifecycleState.RUNNING)

    def paused(self) -> None:
        self._transition(EventLifecycleState.PAUSED)

    def failed(self, reason: str = "") -> None:
        self._state = EventLifecycleState.FAILED
        logger.error("EventBus %s failed: %s", self._name, reason)

    def shutdown(self) -> None:
        self._transition(EventLifecycleState.SHUTDOWN)

    def recover(self) -> None:
        if self._state == EventLifecycleState.FAILED:
            self._state = EventLifecycleState.REGISTERED
            logger.info("EventBus %s recovered to REGISTERED", self._name)

    def _transition(self, target: EventLifecycleState) -> None:
        logger.debug("EventBus %s: %s -> %s", self._name, self._state.value, target.value)
        self._state = target
