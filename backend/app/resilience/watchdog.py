"""Watchdog — monitors stalled workflows, deadlocks, hung tasks."""

from __future__ import annotations

import threading
import time
from typing import Any


class Watchdog:
    """Monitors for stalled workflows, deadlocks, hung tasks, and unhealthy services."""

    def __init__(self, stall_threshold: float = 300.0) -> None:
        self._stall_threshold = stall_threshold
        self._monitored: dict[str, dict[str, Any]] = {}
        self._interventions: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def register(self, name: str, category: str = "task") -> None:
        with self._lock:
            self._monitored[name] = {
                "category": category,
                "start_time": time.time(),
                "last_heartbeat": time.time(),
                "status": "active",
            }

    def heartbeat(self, name: str) -> None:
        with self._lock:
            if name in self._monitored:
                self._monitored[name]["last_heartbeat"] = time.time()

    def unregister(self, name: str) -> None:
        with self._lock:
            self._monitored.pop(name, None)

    def check_stalled(self) -> list[str]:
        stalled: list[str] = []
        now = time.time()
        with self._lock:
            for name, info in self._monitored.items():
                if info["status"] == "active":
                    if now - info["last_heartbeat"] > self._stall_threshold:
                        stalled.append(name)
                        info["status"] = "stalled"
                        self._interventions.append({
                            "component": name,
                            "action": "stall_detected",
                            "category": info["category"],
                            "stalled_seconds": now - info["last_heartbeat"],
                            "timestamp": now,
                        })
        return stalled

    def mark_resolved(self, name: str) -> None:
        with self._lock:
            if name in self._monitored:
                self._monitored[name]["status"] = "active"
                self._monitored[name]["last_heartbeat"] = time.time()

    def get_monitored(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._monitored)

    def get_interventions(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._interventions[-limit:])

    def get_summary(self) -> dict[str, Any]:
        with self._lock:
            active = sum(1 for m in self._monitored.values() if m["status"] == "active")
            stalled = sum(1 for m in self._monitored.values() if m["status"] == "stalled")
            return {
                "total_monitored": len(self._monitored),
                "active": active,
                "stalled": stalled,
                "total_interventions": len(self._interventions),
            }
