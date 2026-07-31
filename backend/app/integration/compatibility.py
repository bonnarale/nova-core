"""Compatibility checking across subsystems."""

from __future__ import annotations

import logging
from typing import Any

from app.integration.enums import CompatibilityLevel
from app.integration.registry import IntegrationRegistry

logger = logging.getLogger(__name__)


class CompatibilityReport:
    """Result of a compatibility check."""

    __slots__ = ("component_a", "component_b", "level", "message", "details")

    def __init__(
        self,
        component_a: str,
        component_b: str,
        level: CompatibilityLevel,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.component_a = component_a
        self.component_b = component_b
        self.level = level
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_a": self.component_a,
            "component_b": self.component_b,
            "level": self.level.value,
            "message": self.message,
            "details": self.details,
        }


class CompatibilityChecker:
    """Checks compatibility between registered subsystems."""

    def __init__(self, registry: IntegrationRegistry) -> None:
        self._registry = registry

    def check_pair(self, name_a: str, name_b: str) -> CompatibilityReport:
        info_a = self._registry.get(name_a)
        info_b = self._registry.get(name_b)
        if not info_a or not info_b:
            return CompatibilityReport(
                name_a, name_b, CompatibilityLevel.UNKNOWN,
                f"Component not registered: {name_a if not info_a else name_b}",
            )
        if info_a.state.value == "failed" or info_b.state.value == "failed":
            return CompatibilityReport(
                name_a, name_b, CompatibilityLevel.INCOMPATIBLE,
                f"Component in failed state: {name_a if info_a.state.value == 'failed' else name_b}",
            )
        return CompatibilityReport(
            name_a, name_b, CompatibilityLevel.COMPATIBLE,
            "Components are compatible",
        )

    def check_all(self) -> list[CompatibilityReport]:
        reports: list[CompatibilityReport] = []
        components = list(self._registry.components.keys())
        for i, name_a in enumerate(components):
            for name_b in components[i + 1:]:
                reports.append(self.check_pair(name_a, name_b))
        return reports

    def check_api_compatibility(self) -> list[CompatibilityReport]:
        reports: list[CompatibilityReport] = []
        for info in self._registry.list_by_type("engine"):
            if info.component and hasattr(info.component, "start"):
                reports.append(
                    CompatibilityReport(
                        info.name, "api_platform",
                        CompatibilityLevel.COMPATIBLE,
                        f"Engine '{info.name}' exposes start() interface",
                    )
                )
        return reports

    def check_provider_compatibility(self) -> list[CompatibilityReport]:
        reports: list[CompatibilityReport] = []
        for info in self._registry.list_by_type("provider"):
            if info.component:
                has_interface = any(
                    hasattr(info.component, method)
                    for method in ("start", "shutdown", "health", "get_status")
                )
                level = CompatibilityLevel.COMPATIBLE if has_interface else CompatibilityLevel.DEPRECATED
                reports.append(
                    CompatibilityReport(
                        info.name, "system",
                        level,
                        f"Provider '{info.name}' {'has' if has_interface else 'lacks'} standard interface",
                    )
                )
        return reports

    def check_plugin_compatibility(self) -> list[CompatibilityReport]:
        reports: list[CompatibilityReport] = []
        for info in self._registry.list_by_type("plugin"):
            if info.component and hasattr(info.component, "activate"):
                reports.append(
                    CompatibilityReport(
                        info.name, "plugin_system",
                        CompatibilityLevel.COMPATIBLE,
                        f"Plugin '{info.name}' exposes activate() interface",
                    )
                )
        return reports

    def get_issues(self) -> list[str]:
        issues: list[str] = []
        for report in self.check_all():
            if report.level in (CompatibilityLevel.INCOMPATIBLE, CompatibilityLevel.DEPRECATED):
                issues.append(report.message)
        return issues
