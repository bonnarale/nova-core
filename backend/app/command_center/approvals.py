from __future__ import annotations

import time
from typing import Any

from .schemas import ApprovalRequest


_MANDATORY_CATEGORIES: dict[str, dict[str, Any]] = {
    "architectural": {
        "description": "Architectural modifications (modules, packages, dependencies)",
        "risk_level": "critical",
        "timeout_seconds": 600,
        "keywords": ["architecture", "module", "package", "dependency", "refactor",
                     "restructure", "migrate", "redesign"],
    },
    "destructive": {
        "description": "Destructive operations (delete, remove, drop, purge)",
        "risk_level": "critical",
        "timeout_seconds": 300,
        "keywords": ["delete", "remove", "drop", "purge", "destroy", "wipe",
                     "truncate", "nuke"],
    },
    "security": {
        "description": "Security changes (auth, permissions, encryption, secrets)",
        "risk_level": "critical",
        "timeout_seconds": 600,
        "keywords": ["security", "auth", "permission", "encrypt", "secret",
                     "credential", "token", "certificate", "vulnerability"],
    },
    "production": {
        "description": "Production deployments and infrastructure changes",
        "risk_level": "critical",
        "timeout_seconds": 900,
        "keywords": ["deploy", "production", "release", "launch", "rollout",
                     "rollback", "infrastructure", "server"],
    },
    "data": {
        "description": "Persistent data modifications (migrations, transforms)",
        "risk_level": "high",
        "timeout_seconds": 600,
        "keywords": ["migrate", "transform", "data", "database", "schema",
                     "backup", "restore", "import", "export"],
    },
    "strategic": {
        "description": "Strategic objective modifications (scope, goals, priorities)",
        "risk_level": "high",
        "timeout_seconds": 600,
        "keywords": ["objective", "strategy", "priority", "scope", "roadmap",
                     "milestone", "goal"],
    },
}


class ApprovalsManager:
    def __init__(self) -> None:
        self.requests: dict[str, ApprovalRequest] = {}
        self.policies: dict[str, dict] = {
            "system_config": {"require_approval": True, "timeout_seconds": 300, "risk_level": "medium"},
            "data_access": {"require_approval": True, "timeout_seconds": 300, "risk_level": "high"},
            "deploy": {"require_approval": True, "timeout_seconds": 600, "risk_level": "critical"},
            "execute_code": {"require_approval": True, "timeout_seconds": 300, "risk_level": "high"},
            "modify_objective": {"require_approval": False, "timeout_seconds": 300, "risk_level": "low"},
            "create_project": {"require_approval": False, "timeout_seconds": 300, "risk_level": "low"},
            "governor_action": {"require_approval": True, "timeout_seconds": 300, "risk_level": "medium"},
            "autonomous_task": {"require_approval": True, "timeout_seconds": 300, "risk_level": "medium"},
        }
        self._audit_log: list[dict] = []

    def request(
        self,
        action_type: str,
        description: str,
        risk_level: str = "low",
        requester: str = "nova",
        metadata: dict | None = None,
    ) -> ApprovalRequest:
        policy = self.policies.get(action_type, {})
        effective_risk = risk_level if risk_level != "low" else policy.get("risk_level", "low")
        mandatory_cat = self._detect_mandatory_category(description)
        if mandatory_cat:
            cat_info = _MANDATORY_CATEGORIES[mandatory_cat]
            effective_risk = cat_info["risk_level"]
            metadata = (metadata or {})
            metadata["mandatory_category"] = mandatory_cat
            metadata["mandatory_description"] = cat_info["description"]
        approval = ApprovalRequest(
            action_type=action_type,
            description=description,
            risk_level=effective_risk,
            requester=requester,
            metadata=metadata or {},
        )
        self.requests[approval.id] = approval
        self._log_audit("request", approval.id, {
            "action_type": action_type,
            "risk_level": effective_risk,
            "mandatory_category": mandatory_cat,
        })
        return approval

    def approve(
        self, approval_id: str, reviewer: str = "user", reason: str | None = None
    ) -> ApprovalRequest | None:
        approval = self.requests.get(approval_id)
        if approval is None:
            return None
        approval.status = "approved"
        approval.reviewer = reviewer
        approval.reason = reason
        self._log_audit("approve", approval_id, {"reviewer": reviewer, "reason": reason})
        return approval

    def reject(
        self, approval_id: str, reviewer: str = "user", reason: str | None = None
    ) -> ApprovalRequest | None:
        approval = self.requests.get(approval_id)
        if approval is None:
            return None
        approval.status = "rejected"
        approval.reviewer = reviewer
        approval.reason = reason
        self._log_audit("reject", approval_id, {"reviewer": reviewer, "reason": reason})
        return approval

    def bulk_approve(
        self, approval_ids: list[str], reviewer: str = "user", reason: str | None = None
    ) -> list[ApprovalRequest | None]:
        results: list[ApprovalRequest | None] = []
        for aid in approval_ids:
            results.append(self.approve(aid, reviewer, reason))
        return results

    def bulk_reject(
        self, approval_ids: list[str], reviewer: str = "user", reason: str | None = None
    ) -> list[ApprovalRequest | None]:
        results: list[ApprovalRequest | None] = []
        for aid in approval_ids:
            results.append(self.reject(aid, reviewer, reason))
        return results

    def expire_stale(self, max_age_seconds: int = 3600) -> list[ApprovalRequest]:
        now = time.time()
        expired: list[ApprovalRequest] = []
        for req in list(self.requests.values()):
            if req.status != "pending":
                continue
            try:
                created = time.mktime(
                    time.strptime(req.created_at[:19], "%Y-%m-%dT%H:%M:%S")
                )
            except (ValueError, OverflowError):
                continue
            if (now - created) > max_age_seconds:
                req.status = "expired"
                expired.append(req)
                self._log_audit("expire", req.id, {"age_seconds": now - created})
        return expired

    def get_pending(self) -> list[ApprovalRequest]:
        return [r for r in self.requests.values() if r.status == "pending"]

    def get_resolved(self) -> list[ApprovalRequest]:
        return [r for r in self.requests.values() if r.status != "pending"]

    def get(self, approval_id: str) -> ApprovalRequest | None:
        return self.requests.get(approval_id)

    def requires_approval(self, action_type: str) -> bool:
        policy = self.policies.get(action_type)
        if policy is None:
            return True
        return policy.get("require_approval", True)

    def requires_mandatory_approval(self, description: str) -> str | None:
        return self._detect_mandatory_category(description)

    def get_mandatory_categories(self) -> dict[str, dict[str, Any]]:
        return dict(_MANDATORY_CATEGORIES)

    def get_audit_log(self, limit: int = 100) -> list[dict]:
        return self._audit_log[-limit:]

    def set_policy(
        self,
        action_type: str,
        require_approval: bool,
        timeout_seconds: int = 300,
        risk_level: str = "low",
    ) -> dict:
        policy = {
            "require_approval": require_approval,
            "timeout_seconds": timeout_seconds,
            "risk_level": risk_level,
        }
        self.policies[action_type] = policy
        return policy

    def _detect_mandatory_category(self, description: str) -> str | None:
        text_lower = description.lower()
        best_cat: str | None = None
        best_score = 0
        for cat, info in _MANDATORY_CATEGORIES.items():
            score = sum(1 for kw in info["keywords"] if kw in text_lower)
            if score > best_score:
                best_score = score
                best_cat = cat
        return best_cat if best_score >= 1 else None

    def _log_audit(self, action: str, approval_id: str, details: dict | None = None) -> None:
        self._audit_log.append({
            "action": action,
            "approval_id": approval_id,
            "details": details or {},
            "timestamp": time.time(),
        })

    def to_dict(self) -> dict:
        return {
            "requests": {k: v.__dict__ for k, v in self.requests.items()},
            "policies": dict(self.policies),
            "mandatory_categories": list(_MANDATORY_CATEGORIES.keys()),
            "audit_log_size": len(self._audit_log),
        }
