"""Permissions — RBAC with system, organization, workspace, resource, and custom scopes."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from app.enterprise.enums import PermissionAction, PermissionScope


class Permission:
    """Represents a single permission entry."""

    __slots__ = (
        "id", "subject", "role", "scope", "scope_id",
        "actions", "created_at",
    )

    def __init__(
        self,
        subject: str,
        role: str,
        scope: PermissionScope,
        scope_id: str = "",
        actions: list[PermissionAction] | None = None,
    ) -> None:
        self.id = str(uuid.uuid4())[:12]
        self.subject = subject
        self.role = role
        self.scope = scope
        self.scope_id = scope_id
        self.actions = actions or list(PermissionAction)
        self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subject": self.subject,
            "role": self.role,
            "scope": self.scope.value,
            "scope_id": self.scope_id,
            "actions": [a.value for a in self.actions],
            "created_at": self.created_at,
        }


class PermissionManager:
    """Manages RBAC permissions with thread-safe operations."""

    def __init__(self) -> None:
        self._permissions: dict[str, Permission] = {}
        self._checks_count = 0
        self._lock = threading.RLock()

    def assign(
        self,
        subject: str,
        role: str,
        scope: PermissionScope,
        scope_id: str = "",
        actions: list[PermissionAction] | None = None,
    ) -> Permission:
        perm = Permission(subject=subject, role=role, scope=scope, scope_id=scope_id, actions=actions)
        with self._lock:
            self._permissions[perm.id] = perm
        return perm

    def revoke(self, permission_id: str) -> bool:
        with self._lock:
            if permission_id in self._permissions:
                del self._permissions[permission_id]
                return True
            return False

    def revoke_by_subject_role(
        self,
        subject: str,
        role: str,
        scope: PermissionScope,
        scope_id: str = "",
    ) -> bool:
        with self._lock:
            for pid, p in list(self._permissions.items()):
                if (
                    p.subject == subject
                    and p.role == role
                    and p.scope == scope
                    and p.scope_id == scope_id
                ):
                    del self._permissions[pid]
                    return True
            return False

    def check(
        self,
        subject: str,
        resource: str,
        action: str,
        scope: PermissionScope = PermissionScope.SYSTEM,
        scope_id: str = "",
    ) -> bool:
        with self._lock:
            self._checks_count += 1
            for p in self._permissions.values():
                if p.subject == subject and p.scope == scope:
                    if p.scope_id == "" or p.scope_id == scope_id:
                        if p.role == "*":
                            return True
                        action_match = any(a.value == action or a.value == "admin" for a in p.actions)
                        if action_match:
                            return True
            return False

    def get_for_subject(self, subject: str) -> list[Permission]:
        with self._lock:
            return [p for p in self._permissions.values() if p.subject == subject]

    def get_all(self) -> list[Permission]:
        with self._lock:
            return list(self._permissions.values())

    def count(self) -> int:
        with self._lock:
            return len(self._permissions)

    def get_checks_count(self) -> int:
        with self._lock:
            return self._checks_count
