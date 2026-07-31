"""Multi-tenancy — tenant isolation, configuration, scoped resources, lifecycle."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from app.enterprise.enums import TenantStatus


class Tenant:
    """Represents a tenant within an organization."""

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
        self.status = TenantStatus.ACTIVE
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


class TenantManager:
    """Manages tenants with thread-safe operations."""

    def __init__(self) -> None:
        self._tenants: dict[str, Tenant] = {}
        self._lock = threading.RLock()

    def create(
        self,
        org_id: str,
        name: str,
        config: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Tenant:
        tenant = Tenant(org_id=org_id, name=name, config=config, metadata=metadata)
        with self._lock:
            self._tenants[tenant.id] = tenant
        return tenant

    def get(self, tenant_id: str) -> Tenant | None:
        with self._lock:
            return self._tenants.get(tenant_id)

    def list_for_org(self, org_id: str) -> list[Tenant]:
        with self._lock:
            return [t for t in self._tenants.values() if t.org_id == org_id]

    def get_all(self) -> list[Tenant]:
        with self._lock:
            return list(self._tenants.values())

    def update_status(self, tenant_id: str, status: TenantStatus) -> bool:
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                return False
            tenant.status = status
            tenant.updated_at = time.time()
            return True

    def update_config(self, tenant_id: str, config: dict[str, Any]) -> bool:
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                return False
            tenant.config.update(config)
            tenant.updated_at = time.time()
            return True

    def delete(self, tenant_id: str) -> bool:
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                return False
            tenant.status = TenantStatus.DELETED
            tenant.updated_at = time.time()
            return True

    def count(self) -> int:
        with self._lock:
            return len(self._tenants)

    def count_active(self) -> int:
        with self._lock:
            return sum(1 for t in self._tenants.values() if t.status == TenantStatus.ACTIVE)
