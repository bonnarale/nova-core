"""Workspaces — multiple workspaces, configuration, permissions."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from app.enterprise.enums import WorkspaceStatus


class Workspace:
    """Represents a workspace within an organization."""

    __slots__ = (
        "id", "org_id", "name", "status", "config",
        "metadata", "created_at", "updated_at",
    )

    def __init__(
        self,
        org_id: str,
        name: str,
        config: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.id = str(uuid.uuid4())[:12]
        self.org_id = org_id
        self.name = name
        self.status = WorkspaceStatus.ACTIVE
        self.config = config or {}
        self.metadata = metadata or {}
        self.created_at = time.time()
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "name": self.name,
            "status": self.status.value,
            "config": self.config,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class WorkspaceManager:
    """Manages workspaces with thread-safe operations."""

    def __init__(self) -> None:
        self._workspaces: dict[str, Workspace] = {}
        self._lock = threading.RLock()

    def create(
        self,
        org_id: str,
        name: str,
        config: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Workspace:
        ws = Workspace(org_id=org_id, name=name, config=config, metadata=metadata)
        with self._lock:
            self._workspaces[ws.id] = ws
        return ws

    def get(self, workspace_id: str) -> Workspace | None:
        with self._lock:
            return self._workspaces.get(workspace_id)

    def list_for_org(self, org_id: str) -> list[Workspace]:
        with self._lock:
            return [w for w in self._workspaces.values() if w.org_id == org_id]

    def get_all(self) -> list[Workspace]:
        with self._lock:
            return list(self._workspaces.values())

    def update_config(self, workspace_id: str, config: dict[str, Any]) -> bool:
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                return False
            ws.config.update(config)
            ws.updated_at = time.time()
            return True

    def archive(self, workspace_id: str) -> bool:
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                return False
            ws.status = WorkspaceStatus.ARCHIVED
            ws.updated_at = time.time()
            return True

    def delete(self, workspace_id: str) -> bool:
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                return False
            ws.status = WorkspaceStatus.DELETED
            ws.updated_at = time.time()
            return True

    def count(self) -> int:
        with self._lock:
            return len(self._workspaces)

    def count_active(self) -> int:
        with self._lock:
            return sum(1 for w in self._workspaces.values() if w.status == WorkspaceStatus.ACTIVE)
