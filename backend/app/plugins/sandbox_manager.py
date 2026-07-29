"""Plugin sandbox manager — tracks resource usage across sandboxes."""

from __future__ import annotations

import time
from typing import Any

from app.plugins.models import SandboxConfig


class SandboxManager:
    """Manages sandbox instances for plugins."""

    def __init__(self, default_config: SandboxConfig | None = None) -> None:
        self._default_config = default_config or SandboxConfig()
        self._configs: dict[str, SandboxConfig] = {}
        self._resource_usage: dict[str, dict[str, Any]] = {}

    def set_sandbox_config(self, plugin_id: str, config: SandboxConfig) -> None:
        self._configs[plugin_id] = config

    def get_sandbox_config(self, plugin_id: str) -> SandboxConfig:
        return self._configs.get(plugin_id, self._default_config)

    def track_execution(self, plugin_id: str, duration_ms: float, memory_mb: float = 0.0) -> None:
        if plugin_id not in self._resource_usage:
            self._resource_usage[plugin_id] = {
                "total_executions": 0,
                "total_duration_ms": 0.0,
                "max_memory_mb": 0.0,
                "last_execution_at": 0.0,
            }
        usage = self._resource_usage[plugin_id]
        usage["total_executions"] += 1
        usage["total_duration_ms"] += duration_ms
        usage["max_memory_mb"] = max(usage["max_memory_mb"], memory_mb)
        usage["last_execution_at"] = time.time()

    def get_resource_usage(self, plugin_id: str) -> dict[str, Any]:
        return dict(self._resource_usage.get(plugin_id, {}))

    def get_all_usage(self) -> dict[str, dict[str, Any]]:
        return {pid: dict(usage) for pid, usage in self._resource_usage.items()}

    def check_limits(self, plugin_id: str) -> dict[str, Any]:
        config = self.get_sandbox_config(plugin_id)
        usage = self._resource_usage.get(plugin_id, {})
        return {
            "plugin_id": plugin_id,
            "within_limits": True,
            "config": config.to_dict(),
            "usage": dict(usage),
        }

    def remove(self, plugin_id: str) -> None:
        self._configs.pop(plugin_id, None)
        self._resource_usage.pop(plugin_id, None)

    def count(self) -> int:
        return len(self._resource_usage)
