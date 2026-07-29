"""Environment validation for the Deployment subsystem."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class EnvironmentValidator:
    """Validates environment variables against required/optional schemas."""

    _REQUIRED: list[str] = [
        "APP_NAME",
        "APP_ENV",
    ]

    _OPTIONAL: dict[str, str] = {
        "APP_VERSION": "0.1.0",
        "LOG_LEVEL": "info",
        "DATABASE_URL": "sqlite+aiosqlite:///./nova.db",
        "REDIS_URL": "",
        "CHROMA_HOST": "localhost",
        "CHROMA_PORT": "8000",
        "OLLAMA_HOST": "localhost",
        "OLLAMA_PORT": "11434",
        "API_HOST": "0.0.0.0",
        "API_PORT": "8000",
        "SECRET_KEY": "",
        "CORS_ORIGINS": "*",
        "WORKERS": "1",
        "DEBUG": "false",
    }

    def __init__(
        self,
        required: list[str] | None = None,
        optional: dict[str, str] | None = None,
    ) -> None:
        self._required = required if required is not None else list(self._REQUIRED)
        self._optional = dict(optional or self._OPTIONAL)

    @property
    def required_variables(self) -> list[str]:
        return list(self._required)

    @property
    def optional_defaults(self) -> dict[str, str]:
        return dict(self._optional)

    def validate(self, env: dict[str, str] | None = None) -> dict[str, Any]:
        source = env if env is not None else dict(os.environ)
        missing: list[str] = []
        present: list[str] = []
        defaults_applied: dict[str, str] = {}

        for var in self._required:
            if var in source and source[var]:
                present.append(var)
            else:
                missing.append(var)

        for var, default in self._optional.items():
            if var in source and source[var]:
                present.append(var)
            else:
                defaults_applied[var] = default

        valid = len(missing) == 0

        return {
            "valid": valid,
            "missing_required": missing,
            "present": present,
            "defaults_applied": defaults_applied,
            "required_count": len(self._required),
            "present_count": len(present),
        }

    def get_effective_config(self, env: dict[str, str] | None = None) -> dict[str, str]:
        source = env if env is not None else dict(os.environ)
        config: dict[str, str] = {}

        for var, default in self._optional.items():
            config[var] = source.get(var, default)

        for var in self._required:
            if var in source:
                config[var] = source[var]

        return config

    def add_required(self, variable: str) -> None:
        if variable not in self._required:
            self._required.append(variable)

    def add_optional(self, variable: str, default: str = "") -> None:
        self._optional[variable] = default
