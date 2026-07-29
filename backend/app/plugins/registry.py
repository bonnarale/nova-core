"""Plugin registry — central registry for all plugins."""

from __future__ import annotations

from typing import Any

from app.plugins.enums import PluginState, PluginType
from app.plugins.exceptions import PluginNotFoundError
from app.plugins.lifecycle import PluginLifecycle
from app.plugins.models import PluginInfo, PluginManifest


class PluginRegistry:
    """Central registry for all loaded plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginInfo] = {}
        self._lifecycles: dict[str, PluginLifecycle] = {}
        self._index_by_type: dict[str, set[str]] = {}
        self._index_by_capability: dict[str, set[str]] = {}
        self._index_by_tag: dict[str, set[str]] = {}

    def register(self, manifest: PluginManifest, instance: Any = None) -> PluginInfo:
        info = PluginInfo(manifest=manifest, instance=instance)
        self._plugins[manifest.plugin_id] = info
        self._lifecycles[manifest.plugin_id] = PluginLifecycle(manifest.plugin_id)
        self._reindex(manifest)
        return info

    def unregister(self, plugin_id: str) -> None:
        info = self._plugins.pop(plugin_id, None)
        self._lifecycles.pop(plugin_id, None)
        if info is not None:
            self._remove_from_indices(info.manifest)

    def get(self, plugin_id: str) -> PluginInfo:
        info = self._plugins.get(plugin_id)
        if info is None:
            raise PluginNotFoundError(plugin_id)
        return info

    def get_optional(self, plugin_id: str) -> PluginInfo | None:
        return self._plugins.get(plugin_id)

    def get_lifecycle(self, plugin_id: str) -> PluginLifecycle | None:
        return self._lifecycles.get(plugin_id)

    def list_all(self) -> list[PluginInfo]:
        return list(self._plugins.values())

    def list_by_state(self, state: PluginState) -> list[PluginInfo]:
        return [p for p in self._plugins.values() if p.state == state]

    def list_by_type(self, plugin_type: PluginType) -> list[PluginInfo]:
        ids = self._index_by_type.get(plugin_type.value, set())
        return [self._plugins[pid] for pid in ids if pid in self._plugins]

    def list_by_capability(self, capability: str) -> list[PluginInfo]:
        ids = self._index_by_capability.get(capability, set())
        return [self._plugins[pid] for pid in ids if pid in self._plugins]

    def list_by_tag(self, tag: str) -> list[PluginInfo]:
        ids = self._index_by_tag.get(tag, set())
        return [self._plugins[pid] for pid in ids if pid in self._plugins]

    def list_enabled(self) -> list[PluginInfo]:
        return [p for p in self._plugins.values() if p.manifest.enabled]

    def list_disabled(self) -> list[PluginInfo]:
        return [p for p in self._plugins.values() if not p.manifest.enabled]

    def contains(self, plugin_id: str) -> bool:
        return plugin_id in self._plugins

    def count(self) -> int:
        return len(self._plugins)

    def update_state(self, plugin_id: str, state: PluginState) -> None:
        info = self._plugins.get(plugin_id)
        if info is not None:
            info.state = state

    def update_config(self, plugin_id: str, config: dict[str, Any]) -> None:
        info = self._plugins.get(plugin_id)
        if info is not None:
            info.config.update(config)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.count(),
            "plugins": {pid: info.to_dict() for pid, info in self._plugins.items()},
        }

    def _reindex(self, manifest: PluginManifest) -> None:
        type_key = manifest.plugin_type.value
        if type_key not in self._index_by_type:
            self._index_by_type[type_key] = set()
        self._index_by_type[type_key].add(manifest.plugin_id)
        for cap in manifest.capabilities:
            if cap not in self._index_by_capability:
                self._index_by_capability[cap] = set()
            self._index_by_capability[cap].add(manifest.plugin_id)
        for tag in manifest.tags:
            if tag not in self._index_by_tag:
                self._index_by_tag[tag] = set()
            self._index_by_tag[tag].add(manifest.plugin_id)

    def _remove_from_indices(self, manifest: PluginManifest) -> None:
        type_key = manifest.plugin_type.value
        if type_key in self._index_by_type:
            self._index_by_type[type_key].discard(manifest.plugin_id)
        for cap in manifest.capabilities:
            if cap in self._index_by_capability:
                self._index_by_capability[cap].discard(manifest.plugin_id)
        for tag in manifest.tags:
            if tag in self._index_by_tag:
                self._index_by_tag[tag].discard(manifest.plugin_id)
