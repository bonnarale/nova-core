"""Audit logging subsystem."""

from __future__ import annotations

import threading
import time
from typing import Any

from app.security.enums import AuditAction
from app.security.models import AuditEntry


class AuditLogger:
    """In-memory audit log."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []
        self._lock = threading.Lock()

    def log(self, entry: AuditEntry) -> None:
        with self._lock:
            self._entries.append(entry)

    def log_event(
        self,
        action: AuditAction,
        user_id: str = "",
        resource: str = "",
        detail: str = "",
        ip_address: str = "",
        user_agent: str = "",
        success: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            entry_id=f"audit_{int(time.time() * 1000)}_{len(self._entries)}",
            action=action,
            user_id=user_id,
            resource=resource,
            detail=detail,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=time.time(),
            success=success,
            metadata=metadata or {},
        )
        self.log(entry)
        return entry

    def query(
        self,
        user_id: str | None = None,
        action: AuditAction | None = None,
        resource: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        with self._lock:
            entries = list(self._entries)
        if user_id:
            entries = [e for e in entries if e.user_id == user_id]
        if action:
            entries = [e for e in entries if e.action == action]
        if resource:
            entries = [e for e in entries if e.resource == resource]
        return entries[-limit:]

    def count(self, user_id: str | None = None) -> int:
        with self._lock:
            if user_id:
                return sum(1 for e in self._entries if e.user_id == user_id)
            return len(self._entries)

    def get_recent(self, limit: int = 50) -> list[AuditEntry]:
        with self._lock:
            return list(self._entries[-limit:])

    def clear(self) -> int:
        with self._lock:
            count = len(self._entries)
            self._entries.clear()
        return count

    def get_failed_logins(self, since: float | None = None) -> list[AuditEntry]:
        cutoff = since or (time.time() - 86400)
        with self._lock:
            return [
                e for e in self._entries
                if e.action == AuditAction.LOGIN_FAILED and e.timestamp >= cutoff
            ]
