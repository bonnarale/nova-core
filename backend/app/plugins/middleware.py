"""Plugin middleware — logging, timing, and error handling wrappers."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.plugins.base import PluginMiddlewareBase

logger = logging.getLogger(__name__)


class LoggingMiddleware(PluginMiddlewareBase):
    """Logs plugin execution events."""

    @property
    def name(self) -> str:
        return "logging"

    @property
    def priority(self) -> int:
        return 10

    async def before_execute(self, plugin_id: str, context: dict[str, Any]) -> dict[str, Any]:
        logger.info(f"Plugin {plugin_id} executing: {context.get('operation', 'unknown')}")
        context["_start_time"] = time.monotonic()
        return context

    async def after_execute(self, plugin_id: str, context: dict[str, Any], result: Any) -> Any:
        elapsed = (time.monotonic() - context.get("_start_time", time.monotonic())) * 1000
        logger.info(f"Plugin {plugin_id} completed in {elapsed:.1f}ms")
        return result

    async def on_error(self, plugin_id: str, context: dict[str, Any], error: Exception) -> bool:
        logger.error(f"Plugin {plugin_id} error: {error}")
        return False


class TimingMiddleware(PluginMiddlewareBase):
    """Tracks plugin execution timing."""

    @property
    def name(self) -> str:
        return "timing"

    @property
    def priority(self) -> int:
        return 5

    def __init__(self) -> None:
        self._timings: dict[str, list[float]] = {}

    async def before_execute(self, plugin_id: str, context: dict[str, Any]) -> dict[str, Any]:
        context["_timing_start"] = time.monotonic()
        return context

    async def after_execute(self, plugin_id: str, context: dict[str, Any], result: Any) -> Any:
        elapsed = (time.monotonic() - context.get("_timing_start", time.monotonic())) * 1000
        self._timings.setdefault(plugin_id, []).append(elapsed)
        return result

    async def on_error(self, plugin_id: str, context: dict[str, Any], error: Exception) -> bool:
        return False

    def get_timings(self, plugin_id: str) -> list[float]:
        return list(self._timings.get(plugin_id, []))

    def get_average(self, plugin_id: str) -> float:
        timings = self._timings.get(plugin_id, [])
        return sum(timings) / len(timings) if timings else 0.0

    def get_all_statistics(self) -> dict[str, Any]:
        stats: dict[str, Any] = {}
        for pid, timings in self._timings.items():
            stats[pid] = {
                "count": len(timings),
                "average_ms": sum(timings) / len(timings) if timings else 0.0,
                "min_ms": min(timings) if timings else 0.0,
                "max_ms": max(timings) if timings else 0.0,
            }
        return stats


class ErrorHandlingMiddleware(PluginMiddlewareBase):
    """Wraps plugin execution with error containment."""

    @property
    def name(self) -> str:
        return "error_handling"

    @property
    def priority(self) -> int:
        return 1

    async def before_execute(self, plugin_id: str, context: dict[str, Any]) -> dict[str, Any]:
        return context

    async def after_execute(self, plugin_id: str, context: dict[str, Any], result: Any) -> Any:
        return result

    async def on_error(self, plugin_id: str, context: dict[str, Any], error: Exception) -> bool:
        logger.error(f"Error handling middleware caught: {error} in plugin {plugin_id}")
        return False


class MiddlewareChain:
    """Executes a chain of middleware around plugin operations."""

    def __init__(self) -> None:
        self._middlewares: list[PluginMiddlewareBase] = []

    def add(self, middleware: PluginMiddlewareBase) -> None:
        self._middlewares.append(middleware)
        self._middlewares.sort(key=lambda m: m.priority)

    def remove(self, name: str) -> bool:
        before = len(self._middlewares)
        self._middlewares = [m for m in self._middlewares if m.name != name]
        return len(self._middlewares) < before

    async def execute_before(self, plugin_id: str, context: dict[str, Any]) -> dict[str, Any]:
        for mw in self._middlewares:
            context = await mw.before_execute(plugin_id, context)
        return context

    async def execute_after(self, plugin_id: str, context: dict[str, Any], result: Any) -> Any:
        for mw in reversed(self._middlewares):
            result = await mw.after_execute(plugin_id, context, result)
        return result

    async def execute_on_error(self, plugin_id: str, context: dict[str, Any], error: Exception) -> bool:
        handled = False
        for mw in self._middlewares:
            result = await mw.on_error(plugin_id, context, error)
            if result:
                handled = True
                break
        return handled

    def list_middlewares(self) -> list[str]:
        return [m.name for m in self._middlewares]

    def count(self) -> int:
        return len(self._middlewares)

    def clear(self) -> None:
        self._middlewares.clear()
