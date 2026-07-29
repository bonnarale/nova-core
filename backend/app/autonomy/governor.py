"""Governor — controls and limits autonomous operations."""

from __future__ import annotations

import threading
import time
from typing import Any

from app.autonomy.enums import AutonomyLevel


class AutonomyGovernor:
    """Controls the degree of autonomous behavior allowed."""

    def __init__(self, level: AutonomyLevel = AutonomyLevel.SUPERVISED) -> None:
        self._level = level
        self._max_concurrent = 5
        self._active_actions = 0
        self._total_actions = 0
        self._blocked_actions = 0
        self._start_time = time.time()
        self._lock = threading.RLock()

    @property
    def level(self) -> AutonomyLevel:
        with self._lock:
            return self._level

    def set_level(self, level: AutonomyLevel) -> None:
        with self._lock:
            self._level = level

    def can_execute(self) -> bool:
        with self._lock:
            if self._level == AutonomyLevel.MANUAL:
                return False
            return self._active_actions < self._max_concurrent

    def begin_action(self) -> bool:
        with self._lock:
            if self._level == AutonomyLevel.MANUAL:
                self._blocked_actions += 1
                return False
            if self._active_actions >= self._max_concurrent:
                self._blocked_actions += 1
                return False
            self._active_actions += 1
            self._total_actions += 1
            return True

    def end_action(self) -> None:
        with self._lock:
            if self._active_actions > 0:
                self._active_actions -= 1

    def set_max_concurrent(self, max_concurrent: int) -> None:
        with self._lock:
            self._max_concurrent = max(1, max_concurrent)

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "level": self._level.value,
                "active_actions": self._active_actions,
                "max_concurrent": self._max_concurrent,
                "total_actions": self._total_actions,
                "blocked_actions": self._blocked_actions,
                "uptime_seconds": time.time() - self._start_time,
            }

    def requires_approval(self, action_type: str) -> bool:
        with self._lock:
            if self._level in (AutonomyLevel.MANUAL, AutonomyLevel.ASSISTED):
                return True
            if self._level == AutonomyLevel.SUPERVISED:
                return action_type in ("write", "delete", "deploy", "execute")
            if self._level == AutonomyLevel.AUTONOMOUS:
                return action_type in ("delete", "deploy")
            return False
