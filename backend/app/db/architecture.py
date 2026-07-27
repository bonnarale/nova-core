"""Database architecture orchestrator."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.db.enums import LifecycleState

logger = logging.getLogger(__name__)


class DatabaseArchitecture:
    """Top-level orchestrator for the database architecture subsystem."""

    def __init__(self) -> None:
        self._state = LifecycleState.REGISTERED
        self._start_time: float = 0.0
        self._repositories: dict[str, Any] = {}
        self._history: list[dict[str, Any]] = []

    @property
    def state(self) -> LifecycleState:
        return self._state

    async def start(self) -> None:
        self._start_time = time.time()
        self._transition(LifecycleState.INITIALIZED, "init")
        self._transition(LifecycleState.READY, "ready")
        self._transition(LifecycleState.RUNNING, "running")
        logger.info("Database Architecture started")

    async def shutdown(self) -> None:
        self._transition(LifecycleState.SHUTDOWN, "shutdown")
        logger.info("Database Architecture shut down")

    def _transition(self, target: LifecycleState, reason: str = "") -> None:
        old = self._state
        self._state = target
        self._history.append({
            "from": old.value,
            "to": target.value,
            "reason": reason,
            "timestamp": time.time(),
        })

    def is_running(self) -> bool:
        return self._state == LifecycleState.RUNNING

    def register_repository(self, name: str, repo: Any) -> None:
        self._repositories[name] = repo

    def get_repository(self, name: str) -> Any | None:
        return self._repositories.get(name)

    def list_repositories(self) -> list[str]:
        return sorted(self._repositories.keys())

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.is_running() else self._state.value,
            "state": self._state.value,
            "repositories": len(self._repositories),
            "uptime_seconds": time.time() - self._start_time if self._start_time else 0.0,
        }

    def get_statistics(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "repositories": len(self._repositories),
            "repository_names": self.list_repositories(),
            "history": self._history,
        }

    def get_history(self) -> list[dict[str, Any]]:
        return list(self._history)
