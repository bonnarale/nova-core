"""Feature flag system for the Future subsystem."""

from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.future.enums import FlagScope, FeatureState


@dataclass
class FeatureFlag:
    name: str
    enabled: bool = False
    scope: FlagScope = FlagScope.GLOBAL
    description: str = ""
    default_value: bool = False
    percentage: float = 100.0
    start_time: datetime | None = None
    end_time: datetime | None = None
    user_overrides: dict[str, bool] = field(default_factory=dict)
    environment_values: dict[str, bool] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "enabled": self.enabled, "scope": self.scope.value,
            "description": self.description, "percentage": self.percentage,
            "created_at": self.created_at.isoformat(), "metadata": self.metadata,
        }


class FeatureFlagManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._flags: dict[str, FeatureFlag] = {}

    def set_flag(self, name: str, enabled: bool, scope: str = "global", **kwargs: Any) -> None:
        with self._lock:
            if name in self._flags:
                flag = self._flags[name]
                flag.enabled = enabled
                flag.scope = FlagScope(scope)
            else:
                self._flags[name] = FeatureFlag(
                    name=name, enabled=enabled, scope=FlagScope(scope), **kwargs
                )

    def is_enabled(self, name: str, user_id: str | None = None, context: dict[str, Any] | None = None) -> bool:
        flag = self._flags.get(name)
        if not flag:
            return False
        if not flag.enabled:
            return False
        now = datetime.now(timezone.utc)
        if flag.start_time and now < flag.start_time:
            return False
        if flag.end_time and now > flag.end_time:
            return False
        if user_id and user_id in flag.user_overrides:
            return flag.user_overrides[user_id]
        if flag.scope == FlagScope.PERCENTAGE and flag.percentage < 100.0:
            hash_val = int(hashlib.md5(f"{name}:{user_id or 'anonymous'}".encode()).hexdigest(), 16)
            bucket = hash_val % 100
            return bucket < flag.percentage
        if flag.scope == FlagScope.ENVIRONMENT and context:
            env = context.get("environment", "")
            if env in flag.environment_values:
                return flag.environment_values[env]
        return flag.enabled

    def get_flag(self, name: str) -> FeatureFlag | None:
        return self._flags.get(name)

    def get_flags(self) -> dict[str, bool]:
        return {name: flag.enabled for name, flag in self._flags.items()}

    def delete_flag(self, name: str) -> bool:
        with self._lock:
            return self._flags.pop(name, None) is not None

    def list_flags(self) -> list[FeatureFlag]:
        return list(self._flags.values())

    def set_user_override(self, name: str, user_id: str, enabled: bool) -> bool:
        flag = self._flags.get(name)
        if not flag:
            return False
        with self._lock:
            flag.user_overrides[user_id] = enabled
        return True

    def set_percentage(self, name: str, percentage: float) -> bool:
        flag = self._flags.get(name)
        if not flag:
            return False
        with self._lock:
            flag.percentage = max(0.0, min(100.0, percentage))
        return True

    def summary(self) -> dict[str, Any]:
        enabled = sum(1 for f in self._flags.values() if f.enabled)
        return {"total": len(self._flags), "enabled": enabled, "disabled": len(self._flags) - enabled}
