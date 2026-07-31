"""Observability engine — top-level orchestrator for the Observability subsystem."""

from __future__ import annotations

import logging
from typing import Any

from app.observability.alerts import AlertManager
from app.observability.collectors import CollectorRegistry
from app.observability.diagnostics import DiagnosticsEngine
from app.observability.events import ObservabilityEventBus
from app.observability.exporters import ExportManager
from app.observability.health import HealthChecker
from app.observability.lifecycle import ObservabilityLifecycle, ObservabilityLifecycleState
from app.observability.logging import ObservabilityLogger
from app.observability.manager import ObservabilityManager
from app.observability.metrics import ObservabilityMetrics, get_observability_metrics
from app.observability.monitor import ApplicationMonitor, SystemMonitor
from app.observability.profiler import Profiler
from app.observability.repository import InMemoryObservabilityRepository
from app.observability.tracing import ObservabilityTracer

logger = logging.getLogger(__name__)


class ObservabilityEngine:
    """Top-level orchestrator for the Observability subsystem."""

    def __init__(
        self,
        manager: ObservabilityManager | None = None,
        repository: InMemoryObservabilityRepository | None = None,
        lifecycle: ObservabilityLifecycle | None = None,
    ) -> None:
        self._lifecycle = lifecycle or ObservabilityLifecycle()
        self._manager = manager or ObservabilityManager()
        self._repository = repository or InMemoryObservabilityRepository()
        self._lifecycle.transition(ObservabilityLifecycleState.INITIALIZED)

    @property
    def lifecycle(self) -> ObservabilityLifecycle:
        return self._lifecycle

    @property
    def manager(self) -> ObservabilityManager:
        return self._manager

    @property
    def repository(self) -> InMemoryObservabilityRepository:
        return self._repository

    async def start(self) -> None:
        self._lifecycle.transition(ObservabilityLifecycleState.READY)
        self._lifecycle.transition(ObservabilityLifecycleState.RUNNING)
        self._manager.event_bus.publish("lifecycle", "observability", {"state": "running"})
        logger.info("ObservabilityEngine started")

    async def shutdown(self) -> None:
        self._lifecycle.transition(ObservabilityLifecycleState.SHUTDOWN)
        self._manager.event_bus.publish("lifecycle", "observability", {"state": "shutdown"})
        logger.info("ObservabilityEngine shutdown")

    # --- Metrics ---

    def record_counter(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        self._manager.record_counter(name, value, labels)

    def record_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        self._manager.record_gauge(name, value, labels)

    def record_histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        self._manager.record_histogram(name, value, labels)

    # --- Tracing ---

    def start_span(self, name: str, parent_id: str | None = None) -> Any:
        return self._manager.tracer.start_span(name, parent_id)

    def end_span(self, span: Any) -> None:
        self._manager.tracer.end_span(span)

    # --- Logging ---

    def log(self, severity: str, message: str, **kwargs: Any) -> None:
        self._manager.log(severity, message, **kwargs)

    # --- Health ---

    async def check_health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self._lifecycle.state == ObservabilityLifecycleState.RUNNING else "degraded",
            "lifecycle_state": self._lifecycle.state.value,
            "uptime_seconds": self._lifecycle.uptime_seconds,
            "checks": await self._manager.health.check_readiness(),
        }

    async def check_readiness(self) -> dict[str, Any]:
        return await self._manager.get_readiness()

    async def check_liveness(self) -> dict[str, Any]:
        return await self._manager.get_liveness()

    async def check_startup(self) -> dict[str, Any]:
        return await self._manager.get_startup()

    # --- Diagnostics ---

    async def get_diagnostics(self) -> dict[str, Any]:
        return await self._manager.get_diagnostics()

    async def get_performance_report(self) -> dict[str, Any]:
        return await self._manager.get_performance_report()

    # --- Alerts ---

    def create_alert_rule(
        self,
        name: str,
        metric_name: str,
        condition: str = "gt",
        threshold: float = 0.0,
        severity: str = "warning",
    ) -> Any:
        return self._manager.alerts.create_rule(
            name=name, metric_name=metric_name, condition=condition,
            threshold=threshold, severity=severity,
        )

    def evaluate_alerts(self, metric_name: str, value: float) -> Any:
        return self._manager.alerts.evaluate(metric_name, value)

    def get_alerts(self, state: str | None = None) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self._manager.alerts.get_alerts(state)]

    def get_alert_rules(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._manager.alerts.list_rules()]

    # --- Export ---

    def export_metrics(self, format: str = "json") -> str:
        return self._manager.export_metrics(format)

    def export_traces(self, format: str = "json") -> str:
        return self._manager.export_traces(format)

    # --- Aggregation ---

    async def get_metrics(self) -> dict[str, Any]:
        return self._manager.get_metrics_dict()

    async def get_traces(self, limit: int = 100) -> dict[str, Any]:
        return self._manager.get_traces_dict(limit)

    async def get_logs(self, limit: int = 100) -> dict[str, Any]:
        return self._manager.get_logs_dict(limit)

    async def get_statistics(self) -> dict[str, Any]:
        stats = self._manager.get_statistics()
        stats["lifecycle_state"] = self._lifecycle.state.value
        return stats

    def get_metrics_dict(self) -> dict[str, Any]:
        return self._manager.get_metrics_dict()

    def get_traces_dict(self, limit: int = 100) -> dict[str, Any]:
        return self._manager.get_traces_dict(limit)

    def get_logs_dict(self, limit: int = 100) -> dict[str, Any]:
        return self._manager.get_logs_dict(limit)

    def get_statistics_dict(self) -> dict[str, Any]:
        return self._manager.get_statistics()
