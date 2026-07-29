"""Configuration management for the Future subsystem."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class FutureConfig:
    feature_flags_enabled: bool = True
    experiments_enabled: bool = True
    capabilities_enabled: bool = True
    compatibility_enabled: bool = True
    deprecation_warnings: bool = True
    version_tracking: bool = True
    max_flags: int = 1000
    max_experiments: int = 100
    max_capabilities: int = 500

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_flags_enabled": self.feature_flags_enabled,
            "experiments_enabled": self.experiments_enabled,
            "capabilities_enabled": self.capabilities_enabled,
            "compatibility_enabled": self.compatibility_enabled,
            "deprecation_warnings": self.deprecation_warnings,
            "version_tracking": self.version_tracking,
            "max_flags": self.max_flags,
            "max_experiments": self.max_experiments,
            "max_capabilities": self.max_capabilities,
        }


class ConfigurationManager:
    def __init__(self, config: FutureConfig | None = None) -> None:
        self._lock = threading.Lock()
        self._config = config or FutureConfig()
        self._overrides: dict[str, Any] = {}

    @property
    def config(self) -> FutureConfig:
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        if key in self._overrides:
            return self._overrides[key]
        return getattr(self._config, key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._overrides[key] = value

    def reset(self) -> None:
        with self._lock:
            self._overrides.clear()

    def to_dict(self) -> dict[str, Any]:
        result = self._config.to_dict()
        result.update(self._overrides)
        return result

    def is_enabled(self, feature: str) -> bool:
        val = self.get(feature, False)
        return bool(val)
