"""Lifecycle management for the Vector Memory module."""

from __future__ import annotations

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class VectorMemoryState(str, Enum):
    REGISTERED = "registered"
    INITIALIZED = "initialized"
    READY = "ready"
    INDEXING = "indexing"
    SEARCHING = "searching"
    CONSOLIDATING = "consolidating"
    FAILED = "failed"
    SHUTDOWN = "shutdown"


class VectorMemoryLifecycle:
    """Manages the state machine for the Vector Memory module."""

    def __init__(self, name: str = "vector_memory") -> None:
        self._name = name
        self._state = VectorMemoryState.REGISTERED

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> VectorMemoryState:
        return self._state

    @property
    def is_registered(self) -> bool:
        return self._state == VectorMemoryState.REGISTERED

    @property
    def is_initialized(self) -> bool:
        return self._state == VectorMemoryState.INITIALIZED

    @property
    def is_ready(self) -> bool:
        return self._state == VectorMemoryState.READY

    @property
    def is_failed(self) -> bool:
        return self._state == VectorMemoryState.FAILED

    @property
    def is_shutdown(self) -> bool:
        return self._state == VectorMemoryState.SHUTDOWN

    def initialized(self) -> None:
        self._transition(VectorMemoryState.INITIALIZED)

    def ready(self) -> None:
        self._transition(VectorMemoryState.READY)

    def indexing(self) -> None:
        self._transition(VectorMemoryState.INDEXING)

    def searching(self) -> None:
        self._transition(VectorMemoryState.SEARCHING)

    def consolidating(self) -> None:
        self._transition(VectorMemoryState.CONSOLIDATING)

    def failed(self, reason: str = "") -> None:
        self._state = VectorMemoryState.FAILED
        logger.error("VectorMemory %s failed: %s", self._name, reason)

    def shutdown(self) -> None:
        self._transition(VectorMemoryState.SHUTDOWN)

    def recover(self) -> None:
        if self._state == VectorMemoryState.FAILED:
            self._state = VectorMemoryState.REGISTERED
            logger.info("VectorMemory %s recovered to REGISTERED", self._name)

    def _transition(self, target: VectorMemoryState) -> None:
        logger.debug("VectorMemory %s: %s -> %s", self._name, self._state.value, target.value)
        self._state = target
