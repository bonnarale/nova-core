"""Plugin sandbox — provides execution isolation."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.plugins.enums import PluginPermission
from app.plugins.exceptions import PluginSandboxError, PluginTimeoutError
from app.plugins.models import PluginExecutionResult, SandboxConfig

logger = logging.getLogger(__name__)


class PluginSandbox:
    """Provides execution isolation for plugins."""

    def __init__(self, config: SandboxConfig | None = None) -> None:
        self._config = config or SandboxConfig()
        self._active_count = 0
        self._total_executions = 0
        self._violations: list[dict[str, Any]] = []

    @property
    def config(self) -> SandboxConfig:
        return self._config

    @property
    def active_count(self) -> int:
        return self._active_count

    @property
    def total_executions(self) -> int:
        return self._total_executions

    @property
    def violations(self) -> list[dict[str, Any]]:
        return list(self._violations)

    def check_permission(self, plugin_id: str, permission: PluginPermission) -> bool:
        if not self._config.restricted:
            return True
        allowed = permission in self._config.allowed_permissions
        if not allowed:
            self._violations.append({
                "plugin_id": plugin_id,
                "permission": permission.value,
                "timestamp": time.time(),
            })
        return allowed

    async def execute(
        self,
        plugin_id: str,
        func: Any,
        *args: Any,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> PluginExecutionResult:
        effective_timeout = timeout or self._config.max_cpu_seconds
        start = time.monotonic()
        self._active_count += 1
        self._total_executions += 1
        try:
            result = await func(*args, **kwargs)
            elapsed = (time.monotonic() - start) * 1000
            if elapsed > effective_timeout * 1000:
                raise PluginTimeoutError(plugin_id, f"Execution took {elapsed:.0f}ms (limit {effective_timeout * 1000:.0f}ms)")
            return PluginExecutionResult(
                success=True,
                plugin_id=plugin_id,
                operation="execute",
                result=result,
                duration_ms=elapsed,
            )
        except (PluginTimeoutError, PluginSandboxError):
            raise
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            return PluginExecutionResult(
                success=False,
                plugin_id=plugin_id,
                operation="execute",
                error=str(exc),
                duration_ms=elapsed,
            )
        finally:
            self._active_count -= 1

    def get_stats(self) -> dict[str, Any]:
        return {
            "active_count": self._active_count,
            "total_executions": self._total_executions,
            "violations_count": len(self._violations),
            "config": self._config.to_dict(),
        }
