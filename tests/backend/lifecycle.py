"""NOVA CORE Lifecycle Tests — Chapter 29.

Tests lifecycle management across subsystems including state transitions,
setup/teardown, and graceful shutdown.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LifecycleEvent:
    """A recorded lifecycle event."""
    component: str
    action: str
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=dict)


class LifecycleTracker:
    """Track lifecycle events for a component."""

    def __init__(self, component: str) -> None:
        self.component = component
        self._events: list[LifecycleEvent] = []

    def record(self, action: str, **metadata: Any) -> None:
        import time
        self._events.append(LifecycleEvent(component=self.component, action=action, timestamp=time.perf_counter(), metadata=metadata))

    @property
    def events(self) -> list[LifecycleEvent]:
        return list(self._events)

    def has_event(self, action: str) -> bool:
        return any(e.action == action for e in self._events)

    def count(self, action: str) -> int:
        return sum(1 for e in self._events if e.action == action)

    def sequence(self) -> list[str]:
        return [e.action for e in self._events]


class LifecycleValidator:
    """Validate lifecycle state transitions."""

    VALID_TRANSITIONS: dict[str, list[str]] = {
        "registered": ["initialized"],
        "initialized": ["ready", "failed"],
        "ready": ["running", "shutdown"],
        "running": ["scaling_up", "scaling_down", "degraded", "failed", "shutdown", "ready"],
        "scaling_up": ["running", "failed"],
        "scaling_down": ["running", "failed"],
        "degraded": ["running", "failed", "shutdown"],
        "failed": ["initialized", "shutdown"],
        "shutdown": ["registered"],
    }

    def __init__(self) -> None:
        self._history: list[str] = []

    def validate_transition(self, from_state: str, to_state: str) -> bool:
        allowed = self.VALID_TRANSITIONS.get(from_state, [])
        return to_state in allowed

    def record_transition(self, from_state: str, to_state: str) -> bool:
        valid = self.validate_transition(from_state, to_state)
        self._history.append(to_state)
        return valid

    @property
    def history(self) -> list[str]:
        return list(self._history)

    def is_valid_sequence(self) -> bool:
        if len(self._history) < 2:
            return True
        for i in range(1, len(self._history)):
            if not self.validate_transition(self._history[i - 1], self._history[i]):
                return False
        return True


async def test_component_lifecycle(component: str, states: list[str]) -> dict[str, Any]:
    """Test a component goes through expected lifecycle states."""
    tracker = LifecycleTracker(component)
    validator = LifecycleValidator()
    valid = True
    for state in states:
        if tracker.events:
            prev = tracker.sequence()[-1]
            valid = validator.record_transition(prev, state) and valid
        tracker.record(state)
    return {"component": component, "states": tracker.sequence(), "valid": valid, "event_count": len(tracker.events)}
