"""Session manager implementation for the Database Architecture."""

from __future__ import annotations

import logging
from typing import Any

from app.db.base import SessionProvider

logger = logging.getLogger(__name__)


class InMemorySessionProvider(SessionProvider):
    """In-memory session provider for testing and development."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._session_count = 0
        self._disposed = False

    async def get_session(self) -> dict[str, Any]:
        if self._disposed:
            raise RuntimeError("Session provider disposed")
        self._session_count += 1
        session_id = f"session-{self._session_count}"
        session = {"id": session_id, "active": True, "data": {}}
        self._sessions[session_id] = session
        return session

    async def close_session(self, session: Any) -> None:
        if isinstance(session, dict):
            sid = session.get("id", "")
            if sid in self._sessions:
                self._sessions[sid]["active"] = False

    async def dispose(self) -> None:
        self._disposed = True
        for session in self._sessions.values():
            session["active"] = False

    def get_active_count(self) -> int:
        return sum(1 for s in self._sessions.values() if s.get("active"))

    def get_total_count(self) -> int:
        return len(self._sessions)

    def is_disposed(self) -> bool:
        return self._disposed


class AsyncSessionFactory:
    """Factory for creating sessions."""

    def __init__(self, provider: SessionProvider | None = None) -> None:
        self._provider = provider or InMemorySessionProvider()

    async def __call__(self) -> Any:
        return await self._provider.get_session()

    def get_provider(self) -> SessionProvider:
        return self._provider
