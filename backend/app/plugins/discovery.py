"""Plugin discovery — finds and validates plugin manifests."""

from __future__ import annotations

import logging
from typing import Any

from app.plugins.base import PluginDiscovery as PluginDiscoveryABC
from app.plugins.manifest import ManifestValidator
from app.plugins.models import PluginManifest

logger = logging.getLogger(__name__)


class PluginDiscoveryService(PluginDiscoveryABC):
    """Discovers plugins from registered sources."""

    def __init__(self) -> None:
        self._sources: list[dict[str, Any]] = []
        self._manifests: list[PluginManifest] = []
        self._validator = ManifestValidator()

    def add_source(self, source_type: str, config: dict[str, Any] | None = None) -> None:
        self._sources.append({"type": source_type, "config": config or {}})

    def add_manifest(self, manifest: PluginManifest) -> None:
        self._manifests.append(manifest)

    def add_manifests(self, manifests: list[PluginManifest]) -> None:
        self._manifests.extend(manifests)

    async def discover(self) -> list[PluginManifest]:
        return list(self._manifests)

    async def discover_by_type(self, plugin_type: str) -> list[PluginManifest]:
        return [m for m in self._manifests if m.plugin_type.value == plugin_type]

    async def discover_by_capability(self, capability: str) -> list[PluginManifest]:
        return [m for m in self._manifests if capability in m.capabilities]

    async def discover_by_tag(self, tag: str) -> list[PluginManifest]:
        return [m for m in self._manifests if tag in m.tags]

    async def discover_enabled(self) -> list[PluginManifest]:
        return [m for m in self._manifests if m.enabled]

    async def discover_with_validation(self) -> tuple[list[PluginManifest], dict[str, list[str]]]:
        valid: list[PluginManifest] = []
        errors: dict[str, list[str]] = {}
        for manifest in self._manifests:
            errs = await self._validator.validate_manifest(manifest)
            if errs:
                errors[manifest.plugin_id] = errs
            else:
                valid.append(manifest)
        return valid, errors

    def clear(self) -> None:
        self._manifests.clear()

    def count(self) -> int:
        return len(self._manifests)

    def list_sources(self) -> list[dict[str, Any]]:
        return list(self._sources)
