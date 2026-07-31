"""Safety engine — prevents unsafe execution, unauthorized actions, policy violations, recursive loops, uncontrolled retries."""

from __future__ import annotations

import threading
import time
from typing import Any

from app.autonomy.enums import SafetyLevel


class SafetyConstraint:
    """A single safety constraint."""

    __slots__ = ("name", "description", "level", "check_fn")

    def __init__(self, name: str, description: str = "", level: SafetyLevel = SafetyLevel.NORMAL) -> None:
        self.name = name
        self.description = description
        self.level = level

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "level": self.level.value}


class SafetyEngine:
    """Enforces safety constraints on autonomous operations."""

    def __init__(self, level: SafetyLevel = SafetyLevel.NORMAL) -> None:
        self._level = level
        self._constraints: list[SafetyConstraint] = []
        self._violations: list[dict[str, Any]] = []
        self._blocked_executions: int = 0
        self._recursive_depth: dict[str, int] = {}
        self._retry_counts: dict[str, int] = {}
        self._lock = threading.RLock()
        self._setup_defaults()

    def _setup_defaults(self) -> None:
        self._constraints.append(SafetyConstraint("no_unauthorized", "Prevent unauthorized actions", SafetyLevel.STRICT))
        self._constraints.append(SafetyConstraint("no_recursive", "Prevent recursive execution loops", SafetyLevel.NORMAL))
        self._constraints.append(SafetyConstraint("retry_limit", "Prevent uncontrolled retries", SafetyLevel.NORMAL))
        self._constraints.append(SafetyConstraint("policy_compliance", "Ensure policy compliance", SafetyLevel.NORMAL))

    @property
    def level(self) -> SafetyLevel:
        with self._lock:
            return self._level

    def check_action(self, action: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = context or {}
        violations: list[dict[str, Any]] = []
        max_depth = 10 if self._level == SafetyLevel.PERMISSIVE else 5
        action_id = ctx.get("action_id", action)
        with self._lock:
            depth = self._recursive_depth.get(action_id, 0)
            if depth >= max_depth:
                violations.append({"constraint": "no_recursive", "detail": f"depth={depth} >= max={max_depth}"})
                self._record_violation(action, "recursive_loop", f"depth={depth}")
            retry_count = self._retry_counts.get(action_id, 0)
            max_retries = 10 if self._level == SafetyLevel.PERMISSIVE else 3
            if retry_count >= max_retries:
                violations.append({"constraint": "retry_limit", "detail": f"retries={retry_count} >= max={max_retries}"})
                self._record_violation(action, "uncontrolled_retry", f"retries={retry_count}")
        if self._level in (SafetyLevel.STRICT, SafetyLevel.MAXIMUM):
            requires_auth = ctx.get("requires_auth", False)
            if not requires_auth and action not in ("read", "observe", "monitor"):
                violations.append({"constraint": "no_unauthorized", "detail": "action requires auth"})
                self._record_violation(action, "unauthorized", "no auth context")
        return {"safe": len(violations) == 0, "violations": violations}

    def begin_action(self, action_id: str) -> bool:
        with self._lock:
            if not self.check_action(action_id)["safe"]:
                self._blocked_executions += 1
                return False
            self._recursive_depth[action_id] = self._recursive_depth.get(action_id, 0) + 1
            return True

    def end_action(self, action_id: str) -> None:
        with self._lock:
            depth = self._recursive_depth.get(action_id, 0)
            if depth > 0:
                self._recursive_depth[action_id] = depth - 1
            else:
                self._recursive_depth.pop(action_id, None)

    def record_retry(self, action_id: str) -> bool:
        with self._lock:
            count = self._retry_counts.get(action_id, 0) + 1
            self._retry_counts[action_id] = count
            max_retries = 10 if self._level == SafetyLevel.PERMISSIVE else 3
            return count <= max_retries

    def reset_retries(self, action_id: str) -> None:
        with self._lock:
            self._retry_counts.pop(action_id, None)

    def add_constraint(self, constraint: SafetyConstraint) -> None:
        with self._lock:
            self._constraints.append(constraint)

    def get_constraints(self) -> list[dict[str, Any]]:
        with self._lock:
            return [c.to_dict() for c in self._constraints]

    def _record_violation(self, action: str, constraint: str, detail: str) -> None:
        with self._lock:
            self._violations.append({
                "action": action,
                "constraint": constraint,
                "detail": detail,
                "timestamp": time.time(),
            })

    def get_violations(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._violations[-limit:])

    def get_violation_count(self) -> int:
        with self._lock:
            return len(self._violations)

    def get_blocked_count(self) -> int:
        with self._lock:
            return self._blocked_executions
