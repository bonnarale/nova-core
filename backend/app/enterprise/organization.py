"""Organization management — multi-org support, metadata, ownership, lifecycle."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from app.enterprise.enums import OrganizationStatus


class Organization:
    """Represents an organization."""

    __slots__ = (
        "id", "name", "status", "owner_id", "metadata",
        "created_at", "updated_at",
    )

    def __init__(
        self,
        name: str,
        owner_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.id = str(uuid.uuid4())[:12]
        self.name = name
        self.status = OrganizationStatus.ACTIVE
        self.owner_id = owner_id
        self.metadata = metadata or {}
        self.created_at = time.time()
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "owner_id": self.owner_id,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class OrganizationManager:
    """Manages organizations with thread-safe operations."""

    def __init__(self) -> None:
        self._organizations: dict[str, Organization] = {}
        self._lock = threading.RLock()

    def create(
        self,
        name: str,
        owner_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Organization:
        org = Organization(name=name, owner_id=owner_id, metadata=metadata)
        with self._lock:
            self._organizations[org.id] = org
        return org

    def get(self, org_id: str) -> Organization | None:
        with self._lock:
            return self._organizations.get(org_id)

    def get_all(self) -> list[Organization]:
        with self._lock:
            return list(self._organizations.values())

    def update_status(self, org_id: str, status: OrganizationStatus) -> bool:
        with self._lock:
            org = self._organizations.get(org_id)
            if not org:
                return False
            org.status = status
            org.updated_at = time.time()
            return True

    def delete(self, org_id: str) -> bool:
        with self._lock:
            org = self._organizations.get(org_id)
            if not org:
                return False
            org.status = OrganizationStatus.DELETED
            org.updated_at = time.time()
            return True

    def count(self) -> int:
        with self._lock:
            return len(self._organizations)

    def get_active(self) -> list[Organization]:
        with self._lock:
            return [o for o in self._organizations.values() if o.status == OrganizationStatus.ACTIVE]
