"""RBAC — Role-Based Access Control."""

from __future__ import annotations

import threading
from typing import Any

from app.security.enums import PermissionLevel
from app.security.models import Permission, Role, User


class RBACEngine:
    """Role-Based Access Control engine."""

    def __init__(self) -> None:
        self._roles: dict[str, Role] = {}
        self._permissions: dict[str, Permission] = {}
        self._user_roles: dict[str, set[str]] = {}
        self._lock = threading.Lock()

    def create_role(self, role: Role) -> Role:
        with self._lock:
            self._roles[role.role_id] = role
        return role

    def get_role(self, role_id: str) -> Role | None:
        return self._roles.get(role_id)

    def delete_role(self, role_id: str) -> bool:
        with self._lock:
            if role_id in self._roles:
                del self._roles[role_id]
                return True
        return False

    def list_roles(self) -> list[Role]:
        return list(self._roles.values())

    def assign_role(self, user_id: str, role_id: str) -> bool:
        with self._lock:
            if role_id not in self._roles:
                return False
            if user_id not in self._user_roles:
                self._user_roles[user_id] = set()
            self._user_roles[user_id].add(role_id)
        return True

    def unassign_role(self, user_id: str, role_id: str) -> bool:
        with self._lock:
            if user_id in self._user_roles:
                self._user_roles[user_id].discard(role_id)
                return True
        return False

    def get_user_roles(self, user_id: str) -> list[Role]:
        role_ids = self._user_roles.get(user_id, set())
        return [self._roles[rid] for rid in role_ids if rid in self._roles]

    def get_effective_permissions(self, user_id: str) -> set[str]:
        permissions: set[str] = set()
        role_ids = self._user_roles.get(user_id, set())
        for role_id in role_ids:
            role = self._roles.get(role_id)
            if role:
                permissions.update(role.permissions)
                for parent_id in role.parent_roles:
                    parent = self._roles.get(parent_id)
                    if parent:
                        permissions.update(parent.permissions)
        return permissions

    def check_permission(self, user_id: str, permission: str) -> bool:
        return permission in self.get_effective_permissions(user_id)

    def check_resource_access(
        self,
        user_id: str,
        resource: str,
        action: PermissionLevel,
    ) -> bool:
        effective = self.get_effective_permissions(user_id)
        required = f"{resource}:{action.value}"
        if required in effective:
            return True
        if f"{resource}:*" in effective:
            return True
        if f"*:{action.value}" in effective:
            return True
        if "*:*" in effective:
            return True
        return False

    def add_permission(self, permission: Permission) -> Permission:
        with self._lock:
            self._permissions[permission.permission_id] = permission
        return permission

    def get_permission(self, permission_id: str) -> Permission | None:
        return self._permissions.get(permission_id)

    def list_permissions(self) -> list[Permission]:
        return list(self._permissions.values())

    def count(self) -> dict[str, int]:
        return {"roles": len(self._roles), "permissions": len(self._permissions)}
