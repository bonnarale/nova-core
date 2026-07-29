"""Security policy engine."""

from __future__ import annotations

import threading
from typing import Any

from app.security.models import SecurityPolicy


class PolicyEngine:
    """Evaluates security policies against requests."""

    def __init__(self) -> None:
        self._policies: dict[str, SecurityPolicy] = {}
        self._lock = threading.Lock()

    def add_policy(self, policy: SecurityPolicy) -> None:
        with self._lock:
            self._policies[policy.policy_id] = policy

    def remove_policy(self, policy_id: str) -> bool:
        with self._lock:
            if policy_id in self._policies:
                del self._policies[policy_id]
                return True
        return False

    def get_policy(self, policy_id: str) -> SecurityPolicy | None:
        return self._policies.get(policy_id)

    def list_policies(self) -> list[SecurityPolicy]:
        policies = list(self._policies.values())
        policies.sort(key=lambda p: p.priority, reverse=True)
        return policies

    def evaluate(self, context: dict[str, Any]) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        for policy in self.list_policies():
            if not policy.enabled:
                continue
            for rule in policy.rules:
                match = self._match_rule(rule, context)
                results.append({
                    "policy_id": policy.policy_id,
                    "rule": rule,
                    "matched": match,
                })
        return {
            "results": results,
            "allowed": all(r["matched"] or not r["rule"].get("deny_on_match", False) for r in results),
        }

    def _match_rule(self, rule: dict[str, Any], context: dict[str, Any]) -> bool:
        conditions = rule.get("conditions", {})
        for key, expected in conditions.items():
            actual = context.get(key)
            operator = rule.get("operator", "eq")
            if operator == "eq" and actual != expected:
                return False
            if operator == "neq" and actual == expected:
                return False
            if operator == "in" and actual not in (expected if isinstance(expected, list) else [expected]):
                return False
            if operator == "contains" and isinstance(actual, str) and expected not in actual:
                return False
        return True

    def count(self) -> int:
        with self._lock:
            return len(self._policies)
