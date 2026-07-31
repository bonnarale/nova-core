"""Plugin configuration manager."""

from __future__ import annotations

from typing import Any

from app.plugins.exceptions import PluginNotFoundError


class PluginConfigManager:
    """Manages per-plugin configuration."""

    def __init__(self) -> None:
        self._configs: dict[str, dict[str, Any]] = {}
        self._defaults: dict[str, dict[str, Any]] = {}

    def set_default(self, plugin_id: str, defaults: dict[str, Any]) -> None:
        self._defaults[plugin_id] = dict(defaults)
        if plugin_id not in self._configs:
            self._configs[plugin_id] = dict(defaults)

    def set_config(self, plugin_id: str, config: dict[str, Any]) -> None:
        existing = self._configs.get(plugin_id, {})
        existing.update(config)
        self._configs[plugin_id] = existing

    def get_config(self, plugin_id: str) -> dict[str, Any]:
        config = self._configs.get(plugin_id)
        if config is None:
            defaults = self._defaults.get(plugin_id, {})
            return dict(defaults)
        return dict(config)

    def get_value(self, plugin_id: str, key: str, default: Any = None) -> Any:
        config = self.get_config(plugin_id)
        return config.get(key, default)

    def remove_config(self, plugin_id: str) -> None:
        self._configs.pop(plugin_id, None)
        self._defaults.pop(plugin_id, None)

    def reset_config(self, plugin_id: str) -> None:
        defaults = self._defaults.get(plugin_id, {})
        self._configs[plugin_id] = dict(defaults)

    def list_configs(self) -> dict[str, dict[str, Any]]:
        return {pid: dict(cfg) for pid, cfg in self._configs.items()}

    def has_config(self, plugin_id: str) -> bool:
        return plugin_id in self._configs

    def merge_config(self, plugin_id: str, overrides: dict[str, Any]) -> dict[str, Any]:
        base = self.get_config(plugin_id)
        base.update(overrides)
        self._configs[plugin_id] = base
        return dict(base)
