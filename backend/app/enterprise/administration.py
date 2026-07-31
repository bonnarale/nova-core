"""Administration — centralized administration services for enterprise deployments."""

from __future__ import annotations

import threading
import time
from typing import Any

from app.enterprise.enums import AuditEventType


class AdminAction:
    """Represents an administrative action."""

    __slots__ = ("action_type", "target", "actor", "result", "timestamp", "metadata")

    def __init__(
        self,
        action_type: str,
        target: str,
        actor: str,
        result: str = "success",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.action_type = action_type
        self.target = target
        self.actor = actor
        self.result = result
        self.timestamp = time.time()
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "target": self.target,
            "actor": self.actor,
            "result": self.result,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class AdministrationManager:
    """Centralized administration for enterprise deployments."""

    def __init__(self) -> None:
        self._actions: list[AdminAction] = []
        self._settings: dict[str, Any] = {
            "enforce_sso": False,
            "enforce_mfa": False,
            "session_timeout": 86400,
            "max_login_attempts": 5,
            "password_min_length": 8,
            "audit_enabled": True,
            "default_role": "viewer",
        }
        self._lock = threading.RLock()

    def get_setting(self, key: str) -> Any:
        with self._lock:
            return self._settings.get(key)

    def set_setting(self, key: str, value: Any, actor: str = "system") -> None:
        with self._lock:
            self._settings[key] = value
        self._record_action("setting_change", key, actor, metadata={"value": value})

    def get_all_settings(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._settings)

    def _record_action(
        self,
        action_type: str,
        target: str,
        actor: str,
        result: str = "success",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        action = AdminAction(action_type=action_type, target=target, actor=actor, result=result, metadata=metadata)
        with self._lock:
            self._actions.append(action)

    def get_actions(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            return [a.to_dict() for a in self._actions[-limit:]]

    def count_actions(self) -> int:
        with self._lock:
            return len(self._actions)

    def get_audit_event_type(self) -> AuditEventType:
        return AuditEventType.ADMINISTRATIVE
