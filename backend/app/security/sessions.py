"""Session management."""

from __future__ import annotations

import threading
import time
from typing import Any

from app.security.crypto import TokenGenerator
from app.security.enums import SessionState
from app.security.models import Session


class SessionManager:
    """Manages user sessions."""

    def __init__(self, default_expiry: int = 3600) -> None:
        self._sessions: dict[str, Session] = {}
        self._user_sessions: dict[str, set[str]] = {}
        self._default_expiry = default_expiry
        self._lock = threading.Lock()

    def create_session(
        self,
        user_id: str,
        ip_address: str = "",
        user_agent: str = "",
        expires_in_seconds: int | None = None,
    ) -> Session:
        expiry = expires_in_seconds or self._default_expiry
        now = time.time()
        session = Session(
            session_id=TokenGenerator.generate_hex(24),
            user_id=user_id,
            state=SessionState.ACTIVE,
            created_at=now,
            expires_at=now + expiry,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        with self._lock:
            self._sessions[session.session_id] = session
            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = set()
            self._user_sessions[user_id].add(session.session_id)
        return session

    def validate_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        if session.state != SessionState.ACTIVE:
            return False
        if session.is_expired:
            session.state = SessionState.EXPIRED
            return False
        return True

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def destroy_session(self, session_id: str) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.state = SessionState.REVOKED
            return True

    def destroy_all_sessions(self, user_id: str) -> int:
        count = 0
        with self._lock:
            session_ids = self._user_sessions.get(user_id, set())
            for sid in session_ids:
                session = self._sessions.get(sid)
                if session and session.state == SessionState.ACTIVE:
                    session.state = SessionState.REVOKED
                    count += 1
        return count

    def get_user_sessions(self, user_id: str) -> list[Session]:
        with self._lock:
            session_ids = self._user_sessions.get(user_id, set())
            return [self._sessions[sid] for sid in session_ids if sid in self._sessions]

    def get_active_sessions(self, user_id: str) -> list[Session]:
        return [s for s in self.get_user_sessions(user_id) if s.state == SessionState.ACTIVE]

    def cleanup_expired(self) -> int:
        count = 0
        with self._lock:
            for session in self._sessions.values():
                if session.is_expired and session.state == SessionState.ACTIVE:
                    session.state = SessionState.EXPIRED
                    count += 1
        return count

    def count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def count_active(self) -> int:
        with self._lock:
            return sum(1 for s in self._sessions.values() if s.state == SessionState.ACTIVE)
