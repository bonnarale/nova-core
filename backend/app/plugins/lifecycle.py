"""Plugin lifecycle state machine."""

from __future__ import annotations

import time
from typing import Any

from app.plugins.enums import PluginState


class PluginLifecycle:
    """Manages the lifecycle state of a single plugin."""

    _VALID_TRANSITIONS: dict[PluginState, set[PluginState]] = {
        PluginState.REGISTERED: {PluginState.LOADING, PluginState.DISABLED, PluginState.ERROR},
        PluginState.LOADING: {PluginState.LOADED, PluginState.ERROR},
        PluginState.LOADED: {PluginState.INITIALIZING, PluginState.ERROR, PluginState.DISABLED},
        PluginState.INITIALIZING: {PluginState.RUNNING, PluginState.ERROR},
        PluginState.RUNNING: {PluginState.STOPPING, PluginState.DISABLED},
        PluginState.STOPPING: {PluginState.STOPPED, PluginState.ERROR},
        PluginState.STOPPED: {PluginState.LOADING, PluginState.DISABLED},
        PluginState.ERROR: {PluginState.LOADING, PluginState.DISABLED, PluginState.REGISTERED},
        PluginState.DISABLED: {PluginState.REGISTERED, PluginState.LOADING},
    }

    def __init__(self, plugin_id: str) -> None:
        self._plugin_id = plugin_id
        self._state = PluginState.REGISTERED
        self._created_at = time.time()
        self._updated_at = time.time()
        self._state_history: list[dict[str, Any]] = []
        self._state_history.append({
            "state": self._state.value,
            "timestamp": self._created_at,
        })

    @property
    def plugin_id(self) -> str:
        return self._plugin_id

    @property
    def state(self) -> PluginState:
        return self._state

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    @property
    def state_history(self) -> list[dict[str, Any]]:
        return list(self._state_history)

    def transition(self, new_state: PluginState) -> None:
        valid = self._VALID_TRANSITIONS.get(self._state, set())
        if new_state not in valid:
            raise ValueError(
                f"Invalid transition for {self._plugin_id}: {self._state.value} -> {new_state.value}"
            )
        self._state = new_state
        self._updated_at = time.time()
        self._state_history.append({
            "state": self._state.value,
            "timestamp": self._updated_at,
        })

    def is_running(self) -> bool:
        return self._state == PluginState.RUNNING

    def is_error(self) -> bool:
        return self._state == PluginState.ERROR

    def is_initialized(self) -> bool:
        return self._state in {PluginState.RUNNING, PluginState.STOPPING, PluginState.STOPPED}

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin_id": self._plugin_id,
            "state": self._state.value,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "history": list(self._state_history),
        }
