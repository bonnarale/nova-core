"""Observability manager — mid-level manager wrapping all observability components."""

from __future__ import annotations

import logging
from typing import Any

from app.observability.alerts import AlertManager
from app.observability.collectors import (
    AICollector,
    ApplicationCollector,
    CollectorRegistry,
    ExecutionCollector,
    MemoryCollector,
    SystemCollector,
)
from app.observability.diagnostics import DiagnosticsEngine
from app.observability.events import ObservabilityEventBus
from app.observability.exporters import ExportManager
from app.observability.health import HealthChecker
from app.observability.lifecycle import ObservabilityLifecycle, ObservabilityLifecycleState
from app.observability.logging import ObservabilityLogger
from app.observability.metrics import ObservabilityMetrics, get_observability_metrics
from app.observability.monitor import ApplicationMonitor, SystemMonitor
from app.observability.profiler import Profiler
from app.observability.tracing import ObservabilityTracer

logger = logging.getLogger(__name__)


class ObservabilityManager:
    """Mid-level manager coordinating all observability components."""

    def __init__(
        self,
        metrics: ObservabilityMetrics | None = None,
        tracer: ObservabilityTracer | None = None,
        logger_instance: ObservabilityLogger | None = None,
        health_checker: HealthChecker | None = None,
        diagnostics: DiagnosticsEngine | None = None,
        alert_manager: AlertManager | None = None,
        profiler: Profiler | None = None,
        event_bus: ObservabilityEventBus | None = None,
    ) -> None:
        self._metrics = metrics or get_observability_metrics()
        self._tracer = tracer or ObservabilityTracer()
        self._logger = logger_instance or ObservabilityLogger()
        self._health = health_checker or HealthChecker()
        self._diagnostics = diagnostics or DiagnosticsEngine()
        self._alerts = alert_manager or AlertManager()
        self._profiler = profiler or Profiler()
        self._event_bus = event_bus or ObservabilityEventBus()
        self._export_manager = ExportManager()
        self._collector_registry = CollectorRegistry()
        self._system_monitor = SystemMonitor()
        self._app_monitor = ApplicationMonitor()

        self._setup_default_collectors()

    def _setup_default_collectors(self) -> None:
        self._collector_registry.register(SystemCollector())
        self._collector_registry.register(ApplicationCollector())
        self._collector_registry.register(AICollector())
        self._collector_registry.register(MemoryCollector())
        self._collector_registry.register(ExecutionCollector())

    @property
    def metrics(self) -> ObservabilityMetrics:
        return self._metrics

    @property
    def tracer(self) -> ObservabilityTracer:
        return self._tracer

    @property
    def logger(self) -> ObservabilityLogger:
        return self._logger

    @property
    def health(self) -> HealthChecker:
        return self._health

    @property
    def diagnostics(self) -> DiagnosticsEngine:
        return self._diagnostics

    @property
    def alerts(self) -> AlertManager:
        return self._alerts

    @property
    def profiler(self) -> Profiler:
        return self._profiler

    @property
    def event_bus(self) -> ObservabilityEventBus:
        return self._event_bus

    @property
    def export_manager(self) -> ExportManager:
        return self._export_manager

    @property
    def collector_registry(self) -> CollectorRegistry:
        return self._collector_registry

    @property
    def system_monitor(self) -> SystemMonitor:
        return self._system_monitor

    @property
    def app_monitor(self) -> ApplicationMonitor:
        return self._app_monitor

    def record_counter(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        self._metrics.record_counter(name, value, labels)

    def record_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        self._metrics.record_gauge(name, value, labels)

    def record_histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        self._metrics.record_histogram(name, value, labels)

    def log(self, severity: str, message: str, **kwargs: Any) -> None:
        self._logger.log(severity, message, **kwargs)

    async def get_readiness(self) -> dict[str, Any]:
        return await self._health.check_readiness()

    async def get_liveness(self) -> dict[str, Any]:
        return await self._health.check_liveness()

    async def get_startup(self) -> dict[str, Any]:
        return await self._health.check_startup()

    async def get_diagnostics(self) -> dict[str, Any]:
        return {
            "dependencies": await self._diagnostics.inspect_dependencies(),
            "configuration": await self._diagnostics.inspect_configuration(),
            "runtime": await self._diagnostics.inspect_runtime(),
        }

    async def get_performance_report(self) -> dict[str, Any]:
        return await self._diagnostics.get_performance_report()

    def get_metrics_dict(self) -> dict[str, Any]:
        return self._metrics.to_dict()

    def get_traces_dict(self, limit: int = 100) -> dict[str, Any]:
        return self._tracer.to_dict(limit=limit)

    def get_logs_dict(self, limit: int = 100) -> dict[str, Any]:
        return self._logger.to_dict(limit=limit)

    def get_alerts_dict(self) -> dict[str, Any]:
        return self._alerts.to_dict()

    def get_statistics(self) -> dict[str, Any]:
        return {
            "total_metrics": self._metrics.metric_count,
            "total_spans": self._tracer.span_count,
            "total_logs": self._logger.entry_count,
            "total_alerts": self._alerts.alert_count,
            "total_rules": self._alerts.rule_count,
            "uptime_seconds": self._metrics.uptime_seconds,
        }

    def export_metrics(self, format: str = "json") -> str:
        metric_dicts = [m.to_dict() for m in self._metrics.get_all_metrics()]
        return self._export_manager.export_metrics(metric_dicts, format)

    def export_traces(self, format: str = "json") -> str:
        trace_dicts = self._tracer.get_traces(limit=1000)
        return self._export_manager.export_traces(trace_dicts, format)
