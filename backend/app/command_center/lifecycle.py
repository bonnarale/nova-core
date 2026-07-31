from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

_VALID_PHASES: frozenset[str] = frozenset({
    "initializing",
    "ready",
    "running",
    "paused",
    "stopped",
    "error",
})

_TRANSITIONS: dict[str, set[str]] = {
    "initializing": {"ready", "error"},
    "ready": {"running", "stopped"},
    "running": {"paused", "stopped", "error"},
    "paused": {"running", "stopped"},
    "stopped": {"initializing"},
    "error": {"initializing"},
}


class CommandCenterLifecycle:
    def __init__(self) -> None:
        self.phase: str = "initializing"
        self.events: list[dict] = []
        self.started_at: float | None = None
        self.stopped_at: float | None = None
        self._phase_history: list[dict] = [
            {
                "phase": "initializing",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]

    def _transition(self, target: str) -> dict:
        allowed = _TRANSITIONS.get(self.phase, set())
        if target not in allowed:
            return {
                "success": False,
                "phase": self.phase,
                "error": f"Cannot transition from '{self.phase}' to '{target}'",
            }
        self.phase = target
        entry = {
            "phase": target,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._phase_history.append(entry)
        return {"success": True, "phase": target}

    def start(self) -> dict:
        now = time.time()
        self.started_at = now
        self.stopped_at = None
        result = self._transition("ready")
        if result["success"]:
            run_result = self._transition("running")
            if run_result["success"]:
                self.record_event("lifecycle_started")
                return {
                    "success": True,
                    "phase": "running",
                    "started_at": datetime.now(timezone.utc).isoformat(),
                }
            return run_result
        return result

    def stop(self) -> dict:
        result = self._transition("stopped")
        if result["success"]:
            self.stopped_at = time.time()
            self.record_event("lifecycle_stopped")
        return result

    def pause(self) -> dict:
        result = self._transition("paused")
        if result["success"]:
            self.record_event("lifecycle_paused")
        return result

    def resume(self) -> dict:
        result = self._transition("running")
        if result["success"]:
            self.record_event("lifecycle_resumed")
        return result

    def record_event(self, event_type: str, data: dict | None = None) -> dict:
        event = {
            "id": str(uuid.uuid4()),
            "event_type": event_type,
            "data": data or {},
            "phase": self.phase,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.events.append(event)
        return event

    def get_events(self, limit: int = 50) -> list[dict]:
        return self.events[-limit:]

    def get_phase(self) -> str:
        return self.phase

    def uptime(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.stopped_at if self.stopped_at is not None else time.time()
        return end - self.started_at

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "uptime": self.uptime(),
            "events_count": len(self.events),
            "phase_history": list(self._phase_history),
        }
