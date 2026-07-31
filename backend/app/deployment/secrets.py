"""Secret management for the Deployment subsystem."""

from __future__ import annotations

import logging
import os
from typing import Any

from app.deployment.base import SecretProvider
from app.deployment.enums import SecretSource
from app.deployment.models import SecretInfo

logger = logging.getLogger(__name__)


class SecretManager(SecretProvider):
    """Pluggable secret manager supporting env vars, Docker, and Kubernetes secrets."""

    def __init__(
        self,
        source: SecretSource = SecretSource.ENVIRONMENT,
        secrets_dir: str = "/run/secrets",
    ) -> None:
        self._source = source
        self._secrets_dir = secrets_dir
        self._cache: dict[str, str] = {}
        self._metadata: dict[str, SecretInfo] = {}

    @property
    def source(self) -> SecretSource:
        return self._source

    async def get_secret(self, key: str) -> str | None:
        if key in self._cache:
            return self._cache[key]

        value = await self._resolve_secret(key)
        if value is not None:
            self._cache[key] = value
        return value

    async def set_secret(self, key: str, value: str) -> None:
        self._cache[key] = value
        self._metadata[key] = SecretInfo(
            key=key,
            source=self._source.value,
        )
        logger.debug("Secret set: %s (source=%s)", key, self._source.value)

    async def list_secrets(self) -> list[str]:
        return sorted(set(list(self._cache.keys()) + list(self._metadata.keys())))

    async def delete_secret(self, key: str) -> bool:
        deleted = False
        if key in self._cache:
            del self._cache[key]
            deleted = True
        if key in self._metadata:
            del self._metadata[key]
            deleted = True
        return deleted

    async def validate(self, required: list[str]) -> dict[str, Any]:
        missing: list[str] = []
        present: list[str] = []
        for key in required:
            value = await self.get_secret(key)
            if value:
                present.append(key)
            else:
                missing.append(key)
        return {
            "valid": len(missing) == 0,
            "missing": missing,
            "present": present,
            "checked": len(required),
        }

    async def get_secret_info(self, key: str) -> SecretInfo | None:
        if key in self._metadata:
            return self._metadata[key]
        value = await self.get_secret(key)
        if value is not None:
            info = SecretInfo(key=key, source=self._source.value)
            self._metadata[key] = info
            return info
        return None

    async def _resolve_secret(self, key: str) -> str | None:
        if self._source == SecretSource.ENVIRONMENT:
            return os.environ.get(key)
        if self._source == SecretSource.DOCKER:
            return self._read_from_file(key)
        if self._source == SecretSource.KUBERNETES:
            return self._read_from_file(key)
        if self._source == SecretSource.FILE:
            return self._read_from_file(key)
        return None

    def _read_from_file(self, key: str) -> str | None:
        try:
            secret_path = os.path.join(self._secrets_dir, key)
            if os.path.isfile(secret_path):
                with open(secret_path) as f:
                    return f.read().strip()
        except (OSError, IOError):
            pass
        return None
