"""Enterprise metrics collection."""

from __future__ import annotations

import threading
import time
from typing import Any


class EnterpriseMetrics:
    """Snapshot of enterprise metrics."""

    __slots__ = (
        "organizations", "tenants", "workspaces", "users",
        "role_assignments", "permission_checks", "audit_events",
        "quota_usage", "uptime_seconds",
    )

    def __init__(self, **kwargs: Any) -> None:
        for slot in self.__slots__:
            setattr(self, slot, kwargs.get(slot, 0))

    def to_dict(self) -> dict[str, Any]:
        return {slot: getattr(self, slot) for slot in self.__slots__}


class EnterpriseMetricsCollector:
    """Thread-safe collector for enterprise metrics."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._organizations = 0
        self._tenants = 0
        self._workspaces = 0
        self._users = 0
        self._role_assignments = 0
        self._permission_checks = 0
        self._audit_events = 0
        self._quota_usage: dict[str, int] = {}
        self._start_time: float = 0.0

    def start(self) -> None:
        with self._lock:
            self._start_time = time.time()

    def record_organization_created(self) -> None:
        with self._lock:
            self._organizations += 1

    def record_organization_deleted(self) -> None:
        with self._lock:
            self._organizations = max(0, self._organizations - 1)

    def record_tenant_created(self) -> None:
        with self._lock:
            self._tenants += 1

    def record_tenant_deleted(self) -> None:
        with self._lock:
            self._tenants = max(0, self._tenants - 1)

    def record_workspace_created(self) -> None:
        with self._lock:
            self._workspaces += 1

    def record_workspace_deleted(self) -> None:
        with self._lock:
            self._workspaces = max(0, self._workspaces - 1)

    def record_user_created(self) -> None:
        with self._lock:
            self._users += 1

    def record_user_deleted(self) -> None:
        with self._lock:
            self._users = max(0, self._users - 1)

    def record_role_assignment(self) -> None:
        with self._lock:
            self._role_assignments += 1

    def record_permission_check(self) -> None:
        with self._lock:
            self._permission_checks += 1

    def record_audit_event(self) -> None:
        with self._lock:
            self._audit_events += 1

    def record_quota_usage(self, resource: str, amount: int = 1) -> None:
        with self._lock:
            self._quota_usage[resource] = self._quota_usage.get(resource, 0) + amount

    def snapshot(self) -> EnterpriseMetrics:
        with self._lock:
            uptime = time.time() - self._start_time if self._start_time else 0.0
            return EnterpriseMetrics(
                organizations=self._organizations,
                tenants=self._tenants,
                workspaces=self._workspaces,
                users=self._users,
                role_assignments=self._role_assignments,
                permission_checks=self._permission_checks,
                audit_events=self._audit_events,
                quota_usage=dict(self._quota_usage),
                uptime_seconds=uptime,
            )

    def reset(self) -> None:
        with self._lock:
            self._organizations = 0
            self._tenants = 0
            self._workspaces = 0
            self._users = 0
            self._role_assignments = 0
            self._permission_checks = 0
            self._audit_events = 0
            self._quota_usage.clear()
