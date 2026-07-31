"""Plugin API — external interface for the plugin system."""

from __future__ import annotations

import logging
from typing import Any

from app.plugins.engine import PluginEngine
from app.plugins.models import PluginManifest

logger = logging.getLogger(__name__)


class PluginAPI:
    """External API for interacting with the plugin system."""

    def __init__(self, engine: PluginEngine) -> None:
        self._engine = engine

    async def list_plugins(self) -> list[dict[str, Any]]:
        return self._engine.list_plugins()

    async def get_plugin(self, plugin_id: str) -> dict[str, Any]:
        return self._engine.get_plugin(plugin_id)

    async def register_plugin(self, manifest_data: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
        from app.plugins.manifest import ManifestValidator
        manifest = ManifestValidator.parse_manifest(manifest_data)
        return await self._engine.register_and_start(manifest, config)

    async def unregister_plugin(self, plugin_id: str) -> None:
        await self._engine.stop_and_unregister(plugin_id)

    async def enable_plugin(self, plugin_id: str) -> None:
        await self._engine.manager.enable_plugin(plugin_id)

    async def disable_plugin(self, plugin_id: str) -> None:
        await self._engine.manager.disable_plugin(plugin_id)

    async def execute(self, plugin_id: str, operation: str, params: dict[str, Any] | None = None) -> Any:
        return await self._engine.execute(plugin_id, operation, params)

    async def health(self) -> dict[str, Any]:
        return await self._engine.health()

    async def statistics(self) -> dict[str, Any]:
        return self._engine.get_statistics()

    async def list_by_type(self, plugin_type: str) -> list[dict[str, Any]]:
        from app.plugins.enums import PluginType
        try:
            pt = PluginType(plugin_type)
        except ValueError:
            return []
        return [p.to_dict() for p in self._engine.manager.list_by_type(pt)]

    async def list_by_capability(self, capability: str) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._engine.manager.list_by_capability(capability)]
