"""Plugin hook registry and manager."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.plugins.enums import HookPriority, HookType
from app.plugins.models import HookContext, HookRegistration

logger = logging.getLogger(__name__)


class HookRegistry:
    """Registry for all hook bindings."""

    def __init__(self) -> None:
        self._hooks: dict[str, list[HookRegistration]] = {}
        self._handlers: dict[str, dict[str, Any]] = {}

    def register(
        self,
        hook_name: str,
        plugin_id: str,
        hook_type: HookType = HookType.BEFORE,
        priority: HookPriority = HookPriority.NORMAL,
        handler: Any = None,
    ) -> HookRegistration:
        reg = HookRegistration(
            hook_name=hook_name,
            plugin_id=plugin_id,
            hook_type=hook_type,
            priority=priority,
        )
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(reg)
        if handler is not None:
            key = f"{plugin_id}:{hook_name}:{hook_type.value}"
            self._handlers[key] = handler
        self._hooks[hook_name].sort(key=lambda r: r.priority.value)
        return reg

    def unregister(self, hook_name: str, plugin_id: str) -> bool:
        if hook_name not in self._hooks:
            return False
        before = len(self._hooks[hook_name])
        self._hooks[hook_name] = [
            r for r in self._hooks[hook_name] if r.plugin_id != plugin_id
        ]
        for hook_type in HookType:
            key = f"{plugin_id}:{hook_name}:{hook_type.value}"
            self._handlers.pop(key, None)
        return len(self._hooks[hook_name]) < before

    def get_hooks(self, hook_name: str) -> list[HookRegistration]:
        return list(self._hooks.get(hook_name, []))

    def get_hooks_by_type(self, hook_name: str, hook_type: HookType) -> list[HookRegistration]:
        return [r for r in self._hooks.get(hook_name, []) if r.hook_type == hook_type]

    def get_handler(self, plugin_id: str, hook_name: str, hook_type: HookType) -> Any | None:
        key = f"{plugin_id}:{hook_name}:{hook_type.value}"
        return self._handlers.get(key)

    def list_all_hooks(self) -> list[HookRegistration]:
        result = []
        for hooks in self._hooks.values():
            result.extend(hooks)
        return result

    def list_hook_names(self) -> list[str]:
        return list(self._hooks.keys())

    def count(self) -> int:
        return sum(len(hooks) for hooks in self._hooks.values())

    def clear(self) -> None:
        self._hooks.clear()
        self._handlers.clear()


class HookManager:
    """Executes hooks and manages the hook lifecycle."""

    def __init__(self, registry: HookRegistry | None = None) -> None:
        self._registry = registry or HookRegistry()
        self._execution_count = 0
        self._execution_log: list[dict[str, Any]] = []

    @property
    def registry(self) -> HookRegistry:
        return self._registry

    @property
    def execution_count(self) -> int:
        return self._execution_count

    async def fire(self, hook_name: str, context: HookContext) -> HookContext:
        hooks = self._registry.get_hooks_by_type(hook_name, context.hook_type)
        for reg in hooks:
            if not reg.enabled:
                continue
            handler = self._registry.get_handler(reg.plugin_id, hook_name, context.hook_type)
            if handler is None:
                continue
            start = time.monotonic()
            try:
                if callable(handler):
                    context = await handler(context) if hasattr(handler, "__call__") else context
            except Exception as exc:
                logger.error(f"Hook error [{hook_name}] from {reg.plugin_id}: {exc}")
                self._execution_log.append({
                    "hook_name": hook_name,
                    "plugin_id": reg.plugin_id,
                    "success": False,
                    "error": str(exc),
                    "duration_ms": (time.monotonic() - start) * 1000,
                    "timestamp": time.time(),
                })
            else:
                elapsed = (time.monotonic() - start) * 1000
                self._execution_log.append({
                    "hook_name": hook_name,
                    "plugin_id": reg.plugin_id,
                    "success": True,
                    "duration_ms": elapsed,
                    "timestamp": time.time(),
                })
            self._execution_count += 1
        return context

    def get_execution_log(self, limit: int = 100) -> list[dict[str, Any]]:
        return list(self._execution_log[-limit:])

    def get_statistics(self) -> dict[str, Any]:
        return {
            "total_hooks": self._registry.count(),
            "total_executions": self._execution_count,
            "hook_names": self._registry.list_hook_names(),
        }
