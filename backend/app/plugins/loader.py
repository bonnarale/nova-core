"""Plugin loader — handles instantiation of plugin classes from manifests."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.plugins.enums import PluginState
from app.plugins.exceptions import PluginLoadError
from app.plugins.models import PluginInfo, PluginManifest
from app.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


class PluginLoader:
    """Loads plugins into the registry."""

    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry
        self._plugin_classes: dict[str, type] = {}

    def register_class(self, plugin_id: str, plugin_class: type) -> None:
        self._plugin_classes[plugin_id] = plugin_class

    def register_classes(self, classes: dict[str, type]) -> None:
        self._plugin_classes.update(classes)

    async def load(self, manifest: PluginManifest, config: dict[str, Any] | None = None) -> PluginInfo:
        start = time.monotonic()
        plugin_id = manifest.plugin_id

        if self._registry.contains(plugin_id):
            existing = self._registry.get(plugin_id)
            if existing.state not in {PluginState.STOPPED, PluginState.ERROR, PluginState.REGISTERED}:
                raise PluginLoadError(plugin_id, f"Plugin already loaded and in state {existing.state.value}")

        plugin_class = self._plugin_classes.get(plugin_id)
        instance = None
        if plugin_class is not None:
            try:
                instance = plugin_class()
            except Exception as exc:
                raise PluginLoadError(plugin_id, str(exc)) from exc

        info = self._registry.register(manifest, instance=instance)
        if config:
            info.config.update(config)

        lifecycle = self._registry.get_lifecycle(plugin_id)
        if lifecycle is not None:
            lifecycle.transition(PluginState.LOADING)
            lifecycle.transition(PluginState.LOADED)

        info.state = PluginState.LOADED
        info.load_time_ms = (time.monotonic() - start) * 1000
        logger.info(f"Loaded plugin {plugin_id} in {info.load_time_ms:.1f}ms")
        return info

    async def unload(self, plugin_id: str) -> None:
        info = self._registry.get(plugin_id)
        lifecycle = self._registry.get_lifecycle(plugin_id)
        if lifecycle is not None:
            if lifecycle.is_running():
                lifecycle.transition(PluginState.STOPPING)
                lifecycle.transition(PluginState.STOPPED)
            info.state = PluginState.STOPPED
        logger.info(f"Unloaded plugin {plugin_id}")

    def has_class(self, plugin_id: str) -> bool:
        return plugin_id in self._plugin_classes

    def list_classes(self) -> list[str]:
        return list(self._plugin_classes.keys())
