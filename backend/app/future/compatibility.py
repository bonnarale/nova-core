"""Compatibility layer for cross-version and cross-component support."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.future.enums import CompatibilityLevel


@dataclass
class CompatibilityEntry:
    component: str
    from_version: str
    to_version: str
    level: CompatibilityLevel
    description: str = ""
    breaking_changes: list[str] = field(default_factory=list)
    migration_steps: list[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component, "from_version": self.from_version,
            "to_version": self.to_version, "level": self.level.value,
            "description": self.description, "breaking_changes": self.breaking_changes,
            "migration_steps": self.migration_steps,
        }


class CompatibilityManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: list[CompatibilityEntry] = []
        self._component_versions: dict[str, str] = {}

    def register_component(self, name: str, version: str) -> None:
        with self._lock:
            self._component_versions[name] = version

    def get_component_version(self, name: str) -> str | None:
        return self._component_versions.get(name)

    def check_api_compatibility(self, from_version: str, to_version: str) -> dict[str, Any]:
        level = self._determine_level(from_version, to_version)
        entry = CompatibilityEntry(
            component="api", from_version=from_version, to_version=to_version, level=level,
            description=f"API compatibility check: {from_version} -> {to_version}",
        )
        with self._lock:
            self._entries.append(entry)
        return entry.to_dict()

    def check_model_compatibility(self, model_name: str, version: str) -> dict[str, Any]:
        current = self._component_versions.get(model_name)
        level = CompatibilityLevel.FULL
        if current:
            level = self._determine_level(current, version)
        entry = CompatibilityEntry(
            component=model_name, from_version=current or "unknown", to_version=version,
            level=level, description=f"Model compatibility: {model_name}",
        )
        with self._lock:
            self._entries.append(entry)
        return entry.to_dict()

    def check_plugin_compatibility(self, plugin_name: str, version: str) -> dict[str, Any]:
        current = self._component_versions.get(f"plugin:{plugin_name}")
        level = self._determine_level(current or "0.0.0", version)
        entry = CompatibilityEntry(
            component=f"plugin:{plugin_name}", from_version=current or "0.0.0",
            to_version=version, level=level, description=f"Plugin compatibility: {plugin_name}",
        )
        with self._lock:
            self._entries.append(entry)
        return entry.to_dict()

    def check_workflow_compatibility(self, workflow_name: str, version: str) -> dict[str, Any]:
        current = self._component_versions.get(f"workflow:{workflow_name}")
        level = self._determine_level(current or "0.0.0", version)
        entry = CompatibilityEntry(
            component=f"workflow:{workflow_name}", from_version=current or "0.0.0",
            to_version=version, level=level, description=f"Workflow compatibility: {workflow_name}",
        )
        with self._lock:
            self._entries.append(entry)
        return entry.to_dict()

    def check_schema_compatibility(self, schema_name: str, version: str) -> dict[str, Any]:
        current = self._component_versions.get(f"schema:{schema_name}")
        level = self._determine_level(current or "0.0.0", version)
        entry = CompatibilityEntry(
            component=f"schema:{schema_name}", from_version=current or "0.0.0",
            to_version=version, level=level, description=f"Schema compatibility: {schema_name}",
        )
        with self._lock:
            self._entries.append(entry)
        return entry.to_dict()

    def get_compatibility_report(self) -> dict[str, Any]:
        return {
            "components": dict(self._component_versions),
            "checks": len(self._entries),
            "full": sum(1 for e in self._entries if e.level == CompatibilityLevel.FULL),
            "partial": sum(1 for e in self._entries if e.level == CompatibilityLevel.PARTIAL),
            "incompatible": sum(1 for e in self._entries if e.level == CompatibilityLevel.INCOMPATIBLE),
            "entries": [e.to_dict() for e in self._entries[-10:]],
        }

    def get_entries(self) -> list[CompatibilityEntry]:
        return list(self._entries)

    @staticmethod
    def _determine_level(from_version: str, to_version: str) -> CompatibilityLevel:
        from_parts = _parse_version(from_version)
        to_parts = _parse_version(to_version)
        if not from_parts or not to_parts:
            return CompatibilityLevel.PARTIAL
        if from_parts[0] != to_parts[0]:
            return CompatibilityLevel.INCOMPATIBLE
        if from_parts[1] != to_parts[1]:
            return CompatibilityLevel.PARTIAL
        return CompatibilityLevel.FULL


def _parse_version(version: str) -> tuple[int, int, int] | None:
    parts = version.split(".")
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError):
        return None
