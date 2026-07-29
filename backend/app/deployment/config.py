"""Configuration management for the Deployment subsystem."""

from __future__ import annotations

import logging
import os
from typing import Any

from app.deployment.base import ConfigurationProvider
from app.deployment.enums import DeployEnvironment
from app.deployment.models import ConfigurationItem

logger = logging.getLogger(__name__)

_ENV_CONFIGS: dict[str, dict[str, Any]] = {
    "development": {
        "debug": True,
        "log_level": "debug",
        "workers": 1,
        "reload": True,
        "database_echo": False,
        "cache_ttl": 60,
        "rate_limit": 1000,
        "cors_origins": ["http://localhost:3000", "http://localhost:8080"],
    },
    "testing": {
        "debug": True,
        "log_level": "debug",
        "workers": 1,
        "reload": False,
        "database_echo": False,
        "cache_ttl": 0,
        "rate_limit": 10000,
        "cors_origins": ["http://localhost:3000"],
    },
    "staging": {
        "debug": False,
        "log_level": "info",
        "workers": 2,
        "reload": False,
        "database_echo": False,
        "cache_ttl": 300,
        "rate_limit": 500,
        "cors_origins": ["https://staging.nova-core.ai"],
    },
    "production": {
        "debug": False,
        "log_level": "warning",
        "workers": 4,
        "reload": False,
        "database_echo": False,
        "cache_ttl": 3600,
        "rate_limit": 100,
        "cors_origins": ["https://nova-core.ai"],
    },
}


class DeploymentConfiguration(ConfigurationProvider):
    """Environment-aware configuration with section support."""

    def __init__(
        self,
        environment: str | DeployEnvironment = DeployEnvironment.DEVELOPMENT,
    ) -> None:
        if isinstance(environment, DeployEnvironment):
            self._environment = environment
        else:
            self._environment = DeployEnvironment(environment)
        self._config: dict[str, Any] = {}
        self._items: dict[str, ConfigurationItem] = {}
        self._load_defaults()

    @property
    def environment(self) -> DeployEnvironment:
        return self._environment

    def _load_defaults(self) -> None:
        env_config = _ENV_CONFIGS.get(self._environment.value, {})
        for key, value in env_config.items():
            self._config[key] = value
            self._items[key] = ConfigurationItem(
                key=key,
                value=value,
                section="default",
                source="environment_default",
            )

    async def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    async def get_all(self) -> dict[str, Any]:
        return dict(self._config)

    async def set(self, key: str, value: Any) -> None:
        self._config[key] = value
        self._items[key] = ConfigurationItem(
            key=key,
            value=value,
            section="runtime",
            source="manual",
        )

    async def get_section(self, section: str) -> dict[str, Any]:
        return {
            item.key: item.value
            for item in self._items.values()
            if item.section == section
        }

    async def validate(self) -> dict[str, Any]:
        required_keys = ["debug", "log_level", "workers"]
        missing = [k for k in required_keys if k not in self._config]
        return {
            "valid": len(missing) == 0,
            "missing": missing,
            "environment": self._environment.value,
            "config_keys": sorted(self._config.keys()),
        }

    async def get_item(self, key: str) -> ConfigurationItem | None:
        return self._items.get(key)

    async def get_statistics(self) -> dict[str, Any]:
        sections: dict[str, int] = {}
        for item in self._items.values():
            sections[item.section] = sections.get(item.section, 0) + 1
        return {
            "environment": self._environment.value,
            "total_items": len(self._items),
            "sections": sections,
        }
