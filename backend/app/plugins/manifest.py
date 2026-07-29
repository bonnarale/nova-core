"""Plugin manifest validation and parsing."""

from __future__ import annotations

import re
from typing import Any

from app.plugins.base import PluginValidator
from app.plugins.enums import PluginPermission, PluginType
from app.plugins.models import PluginDependency, PluginManifest


class ManifestValidator(PluginValidator):
    """Validates plugin manifests and configurations."""

    _VALID_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
    _VALID_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$")
    _VALID_TYPES = {t.value for t in PluginType}
    _VALID_PERMISSIONS = {p.value for p in PluginPermission}

    async def validate_manifest(self, manifest: PluginManifest) -> list[str]:
        errors: list[str] = []
        if not manifest.plugin_id:
            errors.append("plugin_id is required")
        elif not self._VALID_ID_RE.match(manifest.plugin_id):
            errors.append(f"Invalid plugin_id format: {manifest.plugin_id}")
        if not manifest.name:
            errors.append("name is required")
        if not manifest.version:
            errors.append("version is required")
        elif not self._VALID_VERSION_RE.match(manifest.version):
            errors.append(f"Invalid semver: {manifest.version}")
        if manifest.plugin_type.value not in self._VALID_TYPES:
            errors.append(f"Invalid plugin type: {manifest.plugin_type.value}")
        for perm in manifest.permissions:
            perm_value = perm.value if hasattr(perm, "value") else str(perm)
            if perm_value not in self._VALID_PERMISSIONS:
                errors.append(f"Invalid permission: {perm_value}")
        for dep in manifest.dependencies:
            if not dep.plugin_id:
                errors.append("Dependency missing plugin_id")
            elif not self._VALID_ID_RE.match(dep.plugin_id):
                errors.append(f"Invalid dependency plugin_id: {dep.plugin_id}")
            if dep.version_min and not self._VALID_VERSION_RE.match(dep.version_min):
                errors.append(f"Invalid dependency version_min: {dep.version_min}")
            if dep.version_max and not self._VALID_VERSION_RE.match(dep.version_max):
                errors.append(f"Invalid dependency version_max: {dep.version_max}")
        return errors

    async def validate_config(self, plugin_id: str, config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if not isinstance(config, dict):
            errors.append(f"Config for {plugin_id} must be a dict")
        return errors

    @staticmethod
    def parse_manifest(data: dict[str, Any]) -> PluginManifest:
        """Parse a dict into a PluginManifest."""
        deps = []
        for d in data.get("dependencies", []):
            if isinstance(d, dict):
                deps.append(PluginDependency(
                    plugin_id=d.get("plugin_id", ""),
                    version_min=d.get("version_min", ""),
                    version_max=d.get("version_max", ""),
                    required=d.get("required", True),
                ))
        permissions = []
        for p in data.get("permissions", []):
            try:
                permissions.append(PluginPermission(p))
            except ValueError:
                continue
        plugin_type_str = data.get("type", "extension")
        try:
            plugin_type = PluginType(plugin_type_str)
        except ValueError:
            plugin_type = PluginType.EXTENSION

        return PluginManifest(
            plugin_id=data.get("plugin_id", ""),
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            plugin_type=plugin_type,
            permissions=permissions,
            dependencies=deps,
            capabilities=list(data.get("capabilities", [])),
            tags=list(data.get("tags", [])),
            config_schema=dict(data.get("config_schema", {})),
            hooks=list(data.get("hooks", [])),
            enabled=data.get("enabled", True),
            metadata=dict(data.get("metadata", {})),
        )
