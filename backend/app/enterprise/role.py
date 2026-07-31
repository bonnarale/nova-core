"""Roles — configurable roles with default enterprise roles."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from app.enterprise.enums import EnterpriseRole


class Role:
    """Represents an enterprise role."""

    __slots__ = (
        "id", "name", "display_name", "permissions", "is_default",
        "metadata", "created_at", "updated_at",
    )

    def __init__(
        self,
        name: str,
        display_name: str = "",
        permissions: list[str] | None = None,
        is_default: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.id = str(uuid.uuid4())[:12]
        self.name = name
        self.display_name = display_name or name.title()
        self.permissions = permissions or []
        self.is_default = is_default
        self.metadata = metadata or {}
        self.created_at = time.time()
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "permissions": self.permissions,
            "is_default": self.is_default,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class RoleManager:
    """Manages enterprise roles with thread-safe operations."""

    def __init__(self) -> None:
        self._roles: dict[str, Role] = {}
        self._lock = threading.RLock()
        self._setup_defaults()

    def _setup_defaults(self) -> None:
        defaults = [
            (EnterpriseRole.OWNER, ["*"], True),
            (EnterpriseRole.ADMINISTRATOR, ["manage", "create", "read", "update", "delete", "execute", "admin"], True),
            (EnterpriseRole.MANAGER, ["create", "read", "update", "execute", "manage"], True),
            (EnterpriseRole.DEVELOPER, ["create", "read", "update", "execute"], True),
            (EnterpriseRole.OPERATOR, ["read", "execute", "manage"], True),
            (EnterpriseRole.ANALYST, ["read", "execute"], True),
            (EnterpriseRole.VIEWER, ["read"], True),
        ]
        for role_enum, perms, is_default in defaults:
            role = Role(
                name=role_enum.value,
                display_name=role_enum.value.replace("_", " ").title(),
                permissions=perms,
                is_default=is_default,
            )
            self._roles[role.name] = role

    def create(
        self,
        name: str,
        display_name: str = "",
        permissions: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Role:
        role = Role(name=name, display_name=display_name, permissions=permissions, metadata=metadata)
        with self._lock:
            self._roles[role.name] = role
        return role

    def get(self, role_name: str) -> Role | None:
        with self._lock:
            return self._roles.get(role_name)

    def get_all(self) -> list[Role]:
        with self._lock:
            return list(self._roles.values())

    def update_permissions(self, role_name: str, permissions: list[str]) -> bool:
        with self._lock:
            role = self._roles.get(role_name)
            if not role:
                return False
            role.permissions = permissions
            role.updated_at = time.time()
            return True

    def delete(self, role_name: str) -> bool:
        with self._lock:
            role = self._roles.get(role_name)
            if not role or role.is_default:
                return False
            del self._roles[role_name]
            return True

    def count(self) -> int:
        with self._lock:
            return len(self._roles)

    def has_permission(self, role_name: str, permission: str) -> bool:
        with self._lock:
            role = self._roles.get(role_name)
            if not role:
                return False
            if "*" in role.permissions:
                return True
            return permission in role.permissions
