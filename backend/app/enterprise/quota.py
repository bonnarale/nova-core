"""Quotas — configurable limits for users, agents, workflows, executions, storage, API requests, vector memory, plugins."""

from __future__ import annotations

import threading
from typing import Any

from app.enterprise.enums import QuotaType


_DEFAULT_LIMITS: dict[QuotaType, int] = {
    QuotaType.USERS: 10,
    QuotaType.AGENTS: 5,
    QuotaType.WORKFLOWS: 20,
    QuotaType.EXECUTIONS: 1000,
    QuotaType.STORAGE: 1073741824,  # 1 GB in bytes
    QuotaType.API_REQUESTS: 10000,
    QuotaType.VECTOR_MEMORY: 100000,
    QuotaType.PLUGINS: 10,
}


class Quota:
    """Represents a quota for a specific resource type."""

    __slots__ = ("resource_type", "limit", "used")

    def __init__(self, resource_type: QuotaType, limit: int) -> None:
        self.resource_type = resource_type
        self.limit = limit
        self.used = 0

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)

    @property
    def utilization(self) -> float:
        return self.used / self.limit if self.limit > 0 else 0.0

    def is_exceeded(self) -> bool:
        return self.used >= self.limit

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_type": self.resource_type.value,
            "limit": self.limit,
            "used": self.used,
            "remaining": self.remaining,
            "utilization": round(self.utilization, 3),
            "exceeded": self.is_exceeded(),
        }


class QuotaManager:
    """Manages quotas with thread-safe operations."""

    def __init__(self) -> None:
        self._quotas: dict[str, dict[QuotaType, Quota]] = {}
        self._lock = threading.RLock()
        self._setup_defaults()

    def _setup_defaults(self) -> None:
        self._quotas["default"] = {
            qt: Quota(qt, limit) for qt, limit in _DEFAULT_LIMITS.items()
        }

    def get_quota(self, org_id: str, resource_type: QuotaType) -> Quota | None:
        with self._lock:
            org_quotas = self._quotas.get(org_id, self._quotas.get("default", {}))
            return org_quotas.get(resource_type)

    def set_limit(self, org_id: str, resource_type: QuotaType, limit: int) -> None:
        with self._lock:
            if org_id not in self._quotas:
                self._quotas[org_id] = dict(self._quotas.get("default", {}))
            existing = self._quotas[org_id].get(resource_type)
            if existing:
                existing.limit = limit
            else:
                self._quotas[org_id][resource_type] = Quota(resource_type, limit)

    def _ensure_org_quotas(self, org_id: str) -> dict[QuotaType, Quota]:
        if org_id not in self._quotas:
            self._quotas[org_id] = {qt: Quota(qt, q.limit) for qt, q in self._quotas.get("default", {}).items()}
        return self._quotas[org_id]

    def check(self, org_id: str, resource_type: QuotaType, amount: int = 1) -> dict[str, Any]:
        with self._lock:
            org_quotas = self._ensure_org_quotas(org_id)
            quota = org_quotas.get(resource_type)
            if not quota:
                return {"allowed": True, "reason": "no_quota"}
            if quota.used + amount > quota.limit:
                return {
                    "allowed": False,
                    "reason": "quota_exceeded",
                    "used": quota.used,
                    "limit": quota.limit,
                    "requested": amount,
                }
            return {"allowed": True, "remaining": quota.remaining - amount}

    def consume(self, org_id: str, resource_type: QuotaType, amount: int = 1) -> bool:
        with self._lock:
            org_quotas = self._ensure_org_quotas(org_id)
            quota = org_quotas.get(resource_type)
            if not quota:
                return True
            if quota.used + amount > quota.limit:
                return False
            quota.used += amount
            return True

    def release(self, org_id: str, resource_type: QuotaType, amount: int = 1) -> None:
        with self._lock:
            org_quotas = self._ensure_org_quotas(org_id)
            quota = org_quotas.get(resource_type)
            if quota:
                quota.used = max(0, quota.used - amount)

    def get_all(self, org_id: str = "default") -> dict[str, Any]:
        with self._lock:
            org_quotas = self._quotas.get(org_id, self._quotas.get("default", {}))
            return {qt.value: q.to_dict() for qt, q in org_quotas.items()}

    def get_usage_summary(self, org_id: str = "default") -> dict[str, Any]:
        with self._lock:
            org_quotas = self._quotas.get(org_id, self._quotas.get("default", {}))
            total_used = sum(q.used for q in org_quotas.values())
            total_limit = sum(q.limit for q in org_quotas.values())
            exceeded = [qt.value for qt, q in org_quotas.items() if q.is_exceeded()]
            return {
                "total_used": total_used,
                "total_limit": total_limit,
                "utilization": round(total_used / total_limit, 3) if total_limit > 0 else 0.0,
                "exceeded": exceeded,
            }

    def reset(self, org_id: str, resource_type: QuotaType | None = None) -> None:
        with self._lock:
            org_quotas = self._quotas.get(org_id)
            if not org_quotas:
                return
            if resource_type:
                quota = org_quotas.get(resource_type)
                if quota:
                    quota.used = 0
            else:
                for q in org_quotas.values():
                    q.used = 0
