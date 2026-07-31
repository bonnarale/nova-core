"""Abstract base classes for the Observability subsystem."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ObservabilityProvider(ABC):
    """Provider interface for the observability engine."""

    @abstractmethod
    async def initialize(self) -> None:
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        ...

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        ...


class MetricsProvider(ABC):
    """Provider interface for metrics collection."""

    @abstractmethod
    def record_counter(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        ...

    @abstractmethod
    def record_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        ...

    @abstractmethod
    def record_histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        ...

    @abstractmethod
    def get_metric(self, name: str) -> Any:
        ...

    @abstractmethod
    def get_all_metrics(self) -> list[Any]:
        ...


class TracingProvider(ABC):
    """Provider interface for distributed tracing."""

    @abstractmethod
    def start_span(self, name: str, parent_id: str | None = None) -> Any:
        ...

    @abstractmethod
    def end_span(self, span: Any) -> None:
        ...

    @abstractmethod
    def get_traces(self, name: str | None = None, limit: int = 100) -> list[Any]:
        ...


class LoggingProvider(ABC):
    """Provider interface for structured logging."""

    @abstractmethod
    def log(self, severity: str, message: str, **kwargs: Any) -> None:
        ...

    @abstractmethod
    def get_logs(self, severity: str | None = None, limit: int = 100) -> list[Any]:
        ...


class HealthProvider(ABC):
    """Provider interface for health checks."""

    @abstractmethod
    async def check_readiness(self) -> dict[str, Any]:
        ...

    @abstractmethod
    async def check_liveness(self) -> dict[str, Any]:
        ...

    @abstractmethod
    async def check_startup(self) -> dict[str, Any]:
        ...

    @abstractmethod
    async def get_dependency_health(self) -> dict[str, Any]:
        ...


class DiagnosticsProvider(ABC):
    """Provider interface for diagnostics."""

    @abstractmethod
    async def inspect_dependencies(self) -> dict[str, Any]:
        ...

    @abstractmethod
    async def inspect_configuration(self) -> dict[str, Any]:
        ...

    @abstractmethod
    async def inspect_runtime(self) -> dict[str, Any]:
        ...

    @abstractmethod
    async def get_performance_report(self) -> dict[str, Any]:
        ...


class AlertProvider(ABC):
    """Provider interface for alerting."""

    @abstractmethod
    def create_rule(self, rule: Any) -> Any:
        ...

    @abstractmethod
    def evaluate_rules(self) -> list[Any]:
        ...

    @abstractmethod
    def get_alerts(self, state: str | None = None) -> list[Any]:
        ...

    @abstractmethod
    def resolve_alert(self, alert_id: str) -> bool:
        ...


class ExporterProvider(ABC):
    """Provider interface for metrics/log exporters."""

    @abstractmethod
    def export_metrics(self, format: str = "json") -> str:
        ...

    @abstractmethod
    def export_traces(self, format: str = "json") -> str:
        ...
