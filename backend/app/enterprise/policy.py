"""Policies — access, execution, security, and retention policies."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from app.enterprise.enums import PolicyType


class EnterprisePolicy:
    """Represents an enterprise policy."""

    __slots__ = (
        "id", "name", "policy_type", "rules",
        "enabled", "metadata", "created_at", "updated_at",
    )

    def __init__(
        self,
        name: str,
        policy_type: PolicyType,
        rules: list[dict[str, Any]] | None = None,
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.id = str(uuid.uuid4())[:12]
        self.name = name
        self.policy_type = policy_type
        self.rules = rules or []
        self.enabled = enabled
        self.metadata = metadata or {}
        self.created_at = time.time()
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "policy_type": self.policy_type.value,
            "rules": self.rules,
            "enabled": self.enabled,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class PolicyManager:
    """Manages enterprise policies with thread-safe operations."""

    def __init__(self) -> None:
        self._policies: dict[str, EnterprisePolicy] = {}
        self._lock = threading.RLock()
        self._setup_defaults()

    def _setup_defaults(self) -> None:
        self._policies["default_access"] = EnterprisePolicy(
            name="default_access",
            policy_type=PolicyType.ACCESS,
            rules=[{"action": "read", "allowed": True}, {"action": "write", "allowed": True, "requires_approval": True}],
        )
        self._policies["default_execution"] = EnterprisePolicy(
            name="default_execution",
            policy_type=PolicyType.EXECUTION,
            rules=[{"max_concurrent": 10, "timeout_seconds": 3600}],
        )
        self._policies["default_security"] = EnterprisePolicy(
            name="default_security",
            policy_type=PolicyType.SECURITY,
            rules=[{"require_mfa": False, "session_timeout": 86400}],
        )
        self._policies["default_retention"] = EnterprisePolicy(
            name="default_retention",
            policy_type=PolicyType.RETENTION,
            rules=[{"audit_retention_days": 90, "data_retention_days": 365}],
        )

    def create(
        self,
        name: str,
        policy_type: PolicyType,
        rules: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EnterprisePolicy:
        policy = EnterprisePolicy(name=name, policy_type=policy_type, rules=rules, metadata=metadata)
        with self._lock:
            self._policies[policy.id] = policy
            self._policies[name] = policy
        return policy

    def get(self, name_or_id: str) -> EnterprisePolicy | None:
        with self._lock:
            return self._policies.get(name_or_id)

    def list_by_type(self, policy_type: PolicyType) -> list[EnterprisePolicy]:
        with self._lock:
            return [p for p in self._policies.values() if p.policy_type == policy_type]

    def get_all(self) -> list[EnterprisePolicy]:
        with self._lock:
            seen: set[str] = set()
            result = []
            for p in self._policies.values():
                if p.id not in seen:
                    seen.add(p.id)
                    result.append(p)
            return result

    def evaluate(self, policy_name: str, context: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            policy = self._policies.get(policy_name)
            if not policy or not policy.enabled:
                return {"allowed": True, "reason": "no_policy"}
            for rule in policy.rules:
                action = context.get("action", "")
                if rule.get("action") == action or rule.get("action") == "*":
                    if not rule.get("allowed", True):
                        return {"allowed": False, "reason": "policy_denied", "rule": rule}
                    if rule.get("requires_approval"):
                        return {"allowed": True, "requires_approval": True, "reason": "approval_required", "rule": rule}
                    return {"allowed": True, "reason": "allowed", "rule": rule}
            return {"allowed": True, "reason": "no_matching_rule"}

    def toggle(self, policy_name: str, enabled: bool) -> bool:
        with self._lock:
            policy = self._policies.get(policy_name)
            if not policy:
                return False
            policy.enabled = enabled
            policy.updated_at = time.time()
            return True

    def delete(self, policy_name: str) -> bool:
        with self._lock:
            policy = self._policies.get(policy_name)
            if not policy:
                return False
            del self._policies[policy_name]
            if policy.id in self._policies:
                del self._policies[policy.id]
            return True

    def count(self) -> int:
        with self._lock:
            seen: set[str] = set()
            return sum(1 for p in self._policies.values() if p.id not in seen and not seen.add(p.id))
