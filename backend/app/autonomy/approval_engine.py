from __future__ import annotations

import uuid
from datetime import datetime, timezone


class ApprovalEngine:
    def __init__(self) -> None:
        self._policies: dict[str, dict] = {}
        self._pending: list[dict] = []
        self._resolved: list[dict] = []
        self._init_default_policies()

    def _init_default_policies(self) -> None:
        defaults = {
            "autonomous_execution": {
                "require_approval": True,
                "timeout_seconds": 300,
                "risk_level": "medium",
            },
            "workflow_execution": {
                "require_approval": False,
                "timeout_seconds": 300,
                "risk_level": "low",
            },
            "task_execution": {
                "require_approval": False,
                "timeout_seconds": 300,
                "risk_level": "low",
            },
            "tool_execution": {
                "require_approval": False,
                "timeout_seconds": 600,
                "risk_level": "low",
            },
            "multi_agent": {
                "require_approval": True,
                "timeout_seconds": 300,
                "risk_level": "medium",
            },
            "system_modification": {
                "require_approval": True,
                "timeout_seconds": 600,
                "risk_level": "critical",
            },
            "self_improvement": {
                "require_approval": True,
                "timeout_seconds": 300,
                "risk_level": "high",
            },
            "project_creation": {
                "require_approval": False,
                "timeout_seconds": 300,
                "risk_level": "medium",
            },
        }
        for action_type, policy in defaults.items():
            self._policies[action_type] = {
                "action_type": action_type,
                **policy,
            }

    def set_policy(
        self,
        action_type: str,
        require_approval: bool,
        timeout_seconds: int = 300,
        risk_level: str = "low",
    ) -> dict:
        policy = {
            "action_type": action_type,
            "require_approval": require_approval,
            "timeout_seconds": timeout_seconds,
            "risk_level": risk_level,
        }
        self._policies[action_type] = policy
        return policy

    def get_policy(self, action_type: str) -> dict | None:
        return self._policies.get(action_type)

    def request_approval(
        self,
        action_type: str,
        description: str,
        metadata: dict | None = None,
    ) -> dict:
        approval_id = str(uuid.uuid4())
        policy = self._policies.get(action_type, {})
        request = {
            "id": approval_id,
            "action_type": action_type,
            "description": description,
            "metadata": metadata or {},
            "status": "pending",
            "risk_level": policy.get("risk_level", "low"),
            "timeout_seconds": policy.get("timeout_seconds", 300),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._pending.append(request)
        return request

    def approve(
        self,
        approval_id: str,
        reviewer: str = "user",
        reason: str | None = None,
    ) -> dict | None:
        for i, request in enumerate(self._pending):
            if request["id"] == approval_id:
                self._pending.pop(i)
                request["status"] = "approved"
                request["reviewer"] = reviewer
                request["reason"] = reason
                request["resolved_at"] = datetime.now(timezone.utc).isoformat()
                self._resolved.append(request)
                return request
        return None

    def reject(
        self,
        approval_id: str,
        reviewer: str = "user",
        reason: str | None = None,
    ) -> dict | None:
        for i, request in enumerate(self._pending):
            if request["id"] == approval_id:
                self._pending.pop(i)
                request["status"] = "rejected"
                request["reviewer"] = reviewer
                request["reason"] = reason
                request["resolved_at"] = datetime.now(timezone.utc).isoformat()
                self._resolved.append(request)
                return request
        return None

    def get_pending(self) -> list[dict]:
        return list(self._pending)

    def get_resolved(self) -> list[dict]:
        return list(self._resolved)

    def requires_approval(self, action_type: str) -> bool:
        policy = self._policies.get(action_type)
        if policy is None:
            return True
        return policy["require_approval"]

    def to_dict(self) -> dict:
        return {
            "policies": dict(self._policies),
            "pending": list(self._pending),
            "resolved": list(self._resolved),
        }
