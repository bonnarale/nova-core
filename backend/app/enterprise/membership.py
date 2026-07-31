"""Membership — team membership management and role tracking."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from app.enterprise.enums import MembershipRole


class Membership:
    """Represents a user's membership in a team."""

    __slots__ = (
        "id", "user_id", "team_id", "role", "joined_at", "metadata",
    )

    def __init__(
        self,
        user_id: str,
        team_id: str,
        role: MembershipRole = MembershipRole.MEMBER,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.id = str(uuid.uuid4())[:12]
        self.user_id = user_id
        self.team_id = team_id
        self.role = role
        self.joined_at = time.time()
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "team_id": self.team_id,
            "role": self.role.value,
            "joined_at": self.joined_at,
            "metadata": self.metadata,
        }


class MembershipManager:
    """Manages team memberships with thread-safe operations."""

    def __init__(self) -> None:
        self._memberships: dict[str, Membership] = {}
        self._lock = threading.RLock()

    def add_member(
        self,
        user_id: str,
        team_id: str,
        role: MembershipRole = MembershipRole.MEMBER,
        metadata: dict[str, Any] | None = None,
    ) -> Membership:
        membership = Membership(user_id=user_id, team_id=team_id, role=role, metadata=metadata)
        with self._lock:
            self._memberships[membership.id] = membership
        return membership

    def get(self, membership_id: str) -> Membership | None:
        with self._lock:
            return self._memberships.get(membership_id)

    def get_by_user_and_team(self, user_id: str, team_id: str) -> Membership | None:
        with self._lock:
            for m in self._memberships.values():
                if m.user_id == user_id and m.team_id == team_id:
                    return m
        return None

    def list_for_team(self, team_id: str) -> list[Membership]:
        with self._lock:
            return [m for m in self._memberships.values() if m.team_id == team_id]

    def list_for_user(self, user_id: str) -> list[Membership]:
        with self._lock:
            return [m for m in self._memberships.values() if m.user_id == user_id]

    def update_role(self, membership_id: str, role: MembershipRole) -> bool:
        with self._lock:
            m = self._memberships.get(membership_id)
            if not m:
                return False
            m.role = role
            return True

    def remove_member(self, user_id: str, team_id: str) -> bool:
        with self._lock:
            for mid, m in self._memberships.items():
                if m.user_id == user_id and m.team_id == team_id:
                    del self._memberships[mid]
                    return True
            return False

    def count(self) -> int:
        with self._lock:
            return len(self._memberships)

    def count_for_team(self, team_id: str) -> int:
        with self._lock:
            return sum(1 for m in self._memberships.values() if m.team_id == team_id)
