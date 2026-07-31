"""Integration validation."""

from __future__ import annotations

import logging
from typing import Any

from app.integration.dependency_graph import DependencyGraph
from app.integration.enums import ComponentState, ValidationSeverity
from app.integration.registry import IntegrationRegistry

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of a validation check."""

    __slots__ = ("check", "severity", "message", "details")

    def __init__(
        self,
        check: str,
        severity: ValidationSeverity,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.check = check
        self.severity = severity
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
        }


class IntegrationValidator:
    """Validates integration consistency across subsystems."""

    def __init__(self, registry: IntegrationRegistry, graph: DependencyGraph) -> None:
        self._registry = registry
        self._graph = graph

    def validate_dependencies(self) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        components = self._registry.components
        for name, info in components.items():
            for dep in info.dependencies:
                if dep not in components:
                    results.append(
                        ValidationResult(
                            check="dependency_consistency",
                            severity=ValidationSeverity.ERROR,
                            message=f"Component '{name}' depends on unregistered component '{dep}'",
                            details={"component": name, "missing_dependency": dep},
                        )
                    )
        return results

    def validate_circular_dependencies(self) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        cycles = self._graph.detect_cycles()
        for cycle in cycles:
            results.append(
                ValidationResult(
                    check="circular_dependencies",
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Circular dependency detected: {' -> '.join(cycle)}",
                    details={"cycle": cycle},
                )
            )
        if not cycles:
            results.append(
                ValidationResult(
                    check="circular_dependencies",
                    severity=ValidationSeverity.INFO,
                    message="No circular dependencies detected",
                )
            )
        return results

    def validate_missing_registrations(self) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        graph_nodes = {n.name for n in self._graph.get_all_nodes()}
        registered = set(self._registry.components.keys())
        for node_name in graph_nodes - registered:
            results.append(
                ValidationResult(
                    check="missing_registrations",
                    severity=ValidationSeverity.WARNING,
                    message=f"Node '{node_name}' in dependency graph but not registered",
                    details={"component": node_name},
                )
            )
        for reg_name in registered - graph_nodes:
            results.append(
                ValidationResult(
                    check="missing_registrations",
                    severity=ValidationSeverity.WARNING,
                    message=f"Component '{reg_name}' registered but not in dependency graph",
                    details={"component": reg_name},
                )
            )
        return results

    def validate_interface_compatibility(self) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        components = self._registry.components
        for name, info in components.items():
            if info.component is not None:
                has_start = hasattr(info.component, "start") and callable(info.component.start)
                has_shutdown = hasattr(info.component, "shutdown") and callable(info.component.shutdown)
                if not has_start and not has_shutdown:
                    results.append(
                        ValidationResult(
                            check="interface_compatibility",
                            severity=ValidationSeverity.WARNING,
                            message=f"Component '{name}' lacks start/shutdown interface",
                            details={"component": name},
                        )
                    )
        return results

    def validate_lifecycle_compatibility(self) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        components = self._registry.components
        for name, info in components.items():
            if info.state == ComponentState.FAILED:
                results.append(
                    ValidationResult(
                        check="lifecycle_compatibility",
                        severity=ValidationSeverity.ERROR,
                        message=f"Component '{name}' is in FAILED state",
                        details={"component": name, "state": info.state.value},
                    )
                )
        return results

    def validate_provider_availability(self) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        components = self._registry.components
        for name, info in components.items():
            if info.component is None:
                results.append(
                    ValidationResult(
                        check="provider_availability",
                        severity=ValidationSeverity.ERROR,
                        message=f"Component '{name}' has no provider instance",
                        details={"component": name},
                    )
                )
        return results

    def validate_all(self) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        results.extend(self.validate_dependencies())
        results.extend(self.validate_circular_dependencies())
        results.extend(self.validate_missing_registrations())
        results.extend(self.validate_interface_compatibility())
        results.extend(self.validate_lifecycle_compatibility())
        results.extend(self.validate_provider_availability())
        return results

    def is_valid(self) -> bool:
        return not any(
            r.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)
            for r in self.validate_all()
        )
