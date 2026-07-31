"""Lifecycle management for the Future subsystem."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.future.enums import CapabilityState


@dataclass
class LifecycleState:
    component: str
    state: str
    changed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component, "state": self.state,
            "changed_at": self.changed_at.isoformat(), "metadata": self.metadata,
        }


class LifecycleManager:
    VALID_TRANSITIONS: dict[str, list[str]] = {
        "registered": ["experimental"],
        "experimental": ["beta", "deprecated"],
        "beta": ["stable", "deprecated"],
        "stable": ["deprecated"],
        "deprecated": ["removed"],
        "removed": [],
    }

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._states: dict[str, LifecycleState] = {}
        self._history: dict[str, list[LifecycleState]] = {}

    def register(self, component: str, initial_state: str = "registered") -> LifecycleState:
        with self._lock:
            state = LifecycleState(component=component, state=initial_state)
            self._states[component] = state
            self._history[component] = [state]
        return state

    def transition(self, component: str, new_state: str) -> bool:
        with self._lock:
            current = self._states.get(component)
            if not current:
                return False
            allowed = self.VALID_TRANSITIONS.get(current.state, [])
            if new_state not in allowed:
                return False
            new = LifecycleState(component=component, state=new_state)
            self._states[component] = new
            self._history[component].append(new)
            return True

    def get_state(self, component: str) -> LifecycleState | None:
        return self._states.get(component)

    def get_history(self, component: str) -> list[LifecycleState]:
        return list(self._history.get(component, []))

    def is_valid_transition(self, from_state: str, to_state: str) -> bool:
        return to_state in self.VALID_TRANSITIONS.get(from_state, [])

    def list_components(self) -> list[LifecycleState]:
        return list(self._states.values())

    def summary(self) -> dict[str, Any]:
        states: dict[str, int] = {}
        for s in self._states.values():
            states[s.state] = states.get(s.state, 0) + 1
        return {"total": len(self._states), "by_state": states}
