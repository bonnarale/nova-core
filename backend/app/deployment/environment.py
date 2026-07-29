"""Environment manager for the Deployment subsystem."""

from __future__ import annotations

import logging
import os
from typing import Any

from app.deployment.base import EnvironmentProvider
from app.deployment.models import EnvironmentVariable

logger = logging.getLogger(__name__)


class EnvironmentManager(EnvironmentProvider):
    """Manages environment variables with validation and filtering."""

    def __init__(self, env: dict[str, str] | None = None) -> None:
        self._env: dict[str, str] = dict(env) if env is not None else dict(os.environ)
        self._overrides: dict[str, str] = {}

    async def get(self, key: str, default: str = "") -> str:
        if key in self._overrides:
            return self._overrides[key]
        return self._env.get(key, default)

    async def get_all(self) -> dict[str, str]:
        merged = dict(self._env)
        merged.update(self._overrides)
        return merged

    async def set(self, key: str, value: str) -> None:
        self._overrides[key] = value
        logger.debug("Environment variable overridden: %s", key)

    async def validate(self, required: list[str]) -> dict[str, Any]:
        source = await self.get_all()
        missing = [var for var in required if not source.get(var)]
        return {
            "valid": len(missing) == 0,
            "missing": missing,
            "checked": len(required),
        }

    async def get_filtered(self, prefix: str) -> dict[str, str]:
        all_vars = await self.get_all()
        return {k: v for k, v in all_vars.items() if k.startswith(prefix)}

    async def get_variable(self, key: str) -> EnvironmentVariable:
        value = await self.get(key)
        return EnvironmentVariable(
            key=key,
            value=value,
            required=key in self._env,
            source="environment",
            validated=bool(value),
        )

    async def get_effective_config(self, defaults: dict[str, str] | None = None) -> dict[str, str]:
        all_vars = await self.get_all()
        config = dict(defaults or {})
        config.update(all_vars)
        return config
