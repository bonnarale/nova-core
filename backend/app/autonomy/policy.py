"""Policy engine — autonomy levels, execution/approval policies, safety/resource constraints."""

from __future__ import annotations

import threading
from typing import Any

from app.autonomy.enums import AutonomyLevel, SafetyLevel


class PolicyRule:
    """A single policy rule."""

    __slots__ = ("name", "action_pattern", "allowed", "requires_approval", "conditions")

    def __init__(
        self,
        name: str,
        action_pattern: str = "*",
        allowed: bool = True,
        requires_approval: bool = False,
        conditions: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.action_pattern = action_pattern
        self.allowed = allowed
        self.requires_approval = requires_approval
        self.conditions = conditions or {}

    def matches(self, action: str) -> bool:
        if self.action_pattern == "*":
            return True
        return self.action_pattern in action

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "action_pattern": self.action_pattern,
            "allowed": self.allowed,
            "requires_approval": self.requires_approval,
            "conditions": self.conditions,
        }


class AutonomyPolicy:
    """Configuration for a specific autonomy policy."""

    __slots__ = (
        "name", "level", "safety_level", "max_concurrent_actions",
        "approval_threshold", "resource_limits", "rules",
    )

    def __init__(
        self,
        name: str = "default",
        level: AutonomyLevel = AutonomyLevel.SUPERVISED,
        safety_level: SafetyLevel = SafetyLevel.NORMAL,
        max_concurrent_actions: int = 5,
        approval_threshold: float = 0.7,
        resource_limits: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.level = level
        self.safety_level = safety_level
        self.max_concurrent_actions = max_concurrent_actions
        self.approval_threshold = approval_threshold
        self.resource_limits = resource_limits or {}
        self.rules: list[PolicyRule] = []

    def add_rule(self, rule: PolicyRule) -> None:
        self.rules.append(rule)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "level": self.level.value,
            "safety_level": self.safety_level.value,
            "max_concurrent_actions": self.max_concurrent_actions,
            "approval_threshold": self.approval_threshold,
            "resource_limits": self.resource_limits,
            "rules": [r.to_dict() for r in self.rules],
        }


class PolicyEngine:
    """Evaluates and enforces autonomy policies."""

    def __init__(self) -> None:
        self._policies: dict[str, AutonomyPolicy] = {}
        self._violations: list[dict[str, Any]] = []
        self._lock = threading.RLock()
        self._setup_defaults()

    def _setup_defaults(self) -> None:
        default = AutonomyPolicy(
            name="default",
            level=AutonomyLevel.SUPERVISED,
            safety_level=SafetyLevel.NORMAL,
        )
        default.add_rule(PolicyRule("read_ops", "read", allowed=True, requires_approval=False))
        default.add_rule(PolicyRule("write_ops", "write", allowed=True, requires_approval=True))
        default.add_rule(PolicyRule("delete_ops", "delete", allowed=True, requires_approval=True))
        default.add_rule(PolicyRule("deploy_ops", "deploy", allowed=False, requires_approval=True))
        self._policies["default"] = default

        strict = AutonomyPolicy(
            name="strict",
            level=AutonomyLevel.ASSISTED,
            safety_level=SafetyLevel.STRICT,
            max_concurrent_actions=2,
            approval_threshold=0.9,
        )
        strict.add_rule(PolicyRule("all_ops", "*", allowed=True, requires_approval=True))
        self._policies["strict"] = strict

        autonomous = AutonomyPolicy(
            name="autonomous",
            level=AutonomyLevel.AUTONOMOUS,
            safety_level=SafetyLevel.PERMISSIVE,
            max_concurrent_actions=10,
            approval_threshold=0.3,
        )
        autonomous.add_rule(PolicyRule("read_ops", "read", allowed=True, requires_approval=False))
        autonomous.add_rule(PolicyRule("write_ops", "write", allowed=True, requires_approval=False))
        autonomous.add_rule(PolicyRule("delete_ops", "delete", allowed=True, requires_approval=True))
        self._policies["autonomous"] = autonomous

    def register(self, policy: AutonomyPolicy) -> None:
        with self._lock:
            self._policies[policy.name] = policy

    def get(self, name: str) -> AutonomyPolicy:
        with self._lock:
            return self._policies.get(name, self._policies["default"])

    def get_all(self) -> dict[str, AutonomyPolicy]:
        with self._lock:
            return dict(self._policies)

    def evaluate(self, policy_name: str, action: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        policy = self.get(policy_name)
        for rule in policy.rules:
            if rule.matches(action):
                if not rule.allowed:
                    self._record_violation(policy_name, action, "action_not_allowed")
                    return {"allowed": False, "requires_approval": False, "reason": "action_not_allowed", "rule": rule.name}
                if rule.requires_approval:
                    return {"allowed": True, "requires_approval": True, "reason": "approval_required", "rule": rule.name}
                return {"allowed": True, "requires_approval": False, "reason": "allowed", "rule": rule.name}
        return {"allowed": True, "requires_approval": False, "reason": "default_allow"}

    def check_resource_constraints(self, policy_name: str, resources: dict[str, Any]) -> dict[str, Any]:
        policy = self.get(policy_name)
        violations = []
        for key, value in resources.items():
            limit = policy.resource_limits.get(key)
            if limit is not None and value > limit:
                violations.append({"resource": key, "used": value, "limit": limit})
        return {"within_constraints": len(violations) == 0, "violations": violations}

    def _record_violation(self, policy_name: str, action: str, reason: str) -> None:
        with self._lock:
            self._violations.append({
                "policy": policy_name,
                "action": action,
                "reason": reason,
            })

    def get_violations(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._violations[-limit:])

    def get_violation_count(self) -> int:
        with self._lock:
            return len(self._violations)

    def is_action_allowed(self, policy_name: str, action: str) -> bool:
        result = self.evaluate(policy_name, action)
        return result["allowed"]
