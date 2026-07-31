"""Teams — team creation, membership, hierarchy, ownership."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from app.enterprise.enums import TeamStatus


class Team:
    """Represents a team within an organization."""

    __slots__ = (
        "id", "org_id", "name", "status", "parent_id",
        "owner_id", "metadata", "created_at", "updated_at",
    )

    def __init__(
        self,
        org_id: str,
        name: str,
        parent_id: str = "",
        owner_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.id = str(uuid.uuid4())[:12]
        self.org_id = org_id
        self.name = name
        self.status = TeamStatus.ACTIVE
        self.parent_id = parent_id
        self.owner_id = owner_id
        self.metadata = metadata or {}
        self.created_at = time.time()
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "name": self.name,
            "status": self.status.value,
            "parent_id": self.parent_id,
            "owner_id": self.owner_id,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class TeamManager:
    """Manages teams with thread-safe operations."""

    def __init__(self) -> None:
        self._teams: dict[str, Team] = {}
        self._lock = threading.RLock()

    def create(
        self,
        org_id: str,
        name: str,
        parent_id: str = "",
        owner_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Team:
        team = Team(org_id=org_id, name=name, parent_id=parent_id, owner_id=owner_id, metadata=metadata)
        with self._lock:
            self._teams[team.id] = team
        return team

    def get(self, team_id: str) -> Team | None:
        with self._lock:
            return self._teams.get(team_id)

    def list_for_org(self, org_id: str) -> list[Team]:
        with self._lock:
            return [t for t in self._teams.values() if t.org_id == org_id]

    def list_children(self, parent_id: str) -> list[Team]:
        with self._lock:
            return [t for t in self._teams.values() if t.parent_id == parent_id]

    def get_all(self) -> list[Team]:
        with self._lock:
            return list(self._teams.values())

    def dissolve(self, team_id: str) -> bool:
        with self._lock:
            team = self._teams.get(team_id)
            if not team:
                return False
            team.status = TeamStatus.DISSOLVED
            team.updated_at = time.time()
            return True

    def delete(self, team_id: str) -> bool:
        with self._lock:
            return self._teams.pop(team_id, None) is not None

    def count(self) -> int:
        with self._lock:
            return len(self._teams)

    def count_active(self) -> int:
        with self._lock:
            return sum(1 for t in self._teams.values() if t.status == TeamStatus.ACTIVE)
