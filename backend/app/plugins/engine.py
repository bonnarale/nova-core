"""Plugin engine — top-level orchestrator for the Plugin subsystem."""

from __future__ import annotations

import logging
from typing import Any

from app.plugins.enums import PluginState
from app.plugins.exceptions import PluginNotFoundError
from app.plugins.lifecycle import PluginLifecycle
from app.plugins.manager import PluginManager
from app.plugins.models import PluginManifest, PluginStatistics

logger = logging.getLogger(__name__)


class PluginEngine:
    """Top-level orchestrator for the Plugin subsystem."""

    def __init__(self, manager: PluginManager | None = None) -> None:
        self._manager = manager or PluginManager()
        self._running = False
        self._started_at: float = 0.0

    @property
    def manager(self) -> PluginManager:
        return self._manager

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        import time
        self._started_at = time.time()
        self._running = True
        self._manager.event_bus.publish("engine.started", "system")
        logger.info("PluginEngine started")

    async def shutdown(self) -> None:
        for info in self._manager.list_plugins():
            if info.state == PluginState.RUNNING:
                try:
                    await self._manager.stop_plugin(info.manifest.plugin_id)
                except Exception as exc:
                    logger.error(f"Error stopping plugin {info.manifest.plugin_id}: {exc}")
        self._running = False
        self._manager.event_bus.publish("engine.stopped", "system")
        logger.info("PluginEngine shutdown")

    async def register_and_start(
        self,
        manifest: PluginManifest,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        info = await self._manager.register_plugin(manifest, config)
        await self._manager.start_plugin(manifest.plugin_id)
        return info.to_dict()

    async def stop_and_unregister(self, plugin_id: str) -> None:
        await self._manager.unregister_plugin(plugin_id)

    async def execute(
        self,
        plugin_id: str,
        operation: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        return await self._manager.execute_plugin(plugin_id, operation, params)

    async def health(self) -> dict[str, Any]:
        import time
        uptime = time.time() - self._started_at if self._started_at > 0 else 0.0
        plugin_health = await self._manager.health_check()
        return {
            "status": "ok" if self._running else "stopped",
            "uptime_seconds": uptime,
            "plugins": plugin_health,
        }

    def get_statistics(self) -> dict[str, Any]:
        stats = self._manager.get_statistics()
        stats["running"] = self._running
        return stats

    def list_plugins(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._manager.list_plugins()]

    def get_plugin(self, plugin_id: str) -> dict[str, Any]:
        return self._manager.get_plugin(plugin_id).to_dict()
