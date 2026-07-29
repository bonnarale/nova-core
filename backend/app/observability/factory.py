"""Observability factory — creates and wires all observability components."""

from __future__ import annotations

import logging
from typing import Any

from app.observability.alerts import AlertManager
from app.observability.diagnostics import DiagnosticsEngine
from app.observability.engine import ObservabilityEngine
from app.observability.events import ObservabilityEventBus
from app.observability.health import HealthChecker
from app.observability.lifecycle import ObservabilityLifecycle
from app.observability.logging import ObservabilityLogger
from app.observability.manager import ObservabilityManager
from app.observability.metrics import get_observability_metrics
from app.observability.profiler import Profiler
from app.observability.repository import InMemoryObservabilityRepository
from app.observability.tracing import ObservabilityTracer

logger = logging.getLogger(__name__)


class ObservabilityFactory:
    """Factory that creates all observability components and wires them together."""

    @staticmethod
    def create_engine() -> ObservabilityEngine:
        """Create a fully wired ObservabilityEngine instance."""
        metrics = get_observability_metrics()
        tracer = ObservabilityTracer()
        log = ObservabilityLogger()
        lifecycle = ObservabilityLifecycle()
        health = HealthChecker(lifecycle=lifecycle)
        diagnostics = DiagnosticsEngine()
        alerts = AlertManager()
        profiler = Profiler()
        event_bus = ObservabilityEventBus()
        repository = InMemoryObservabilityRepository()

        manager = ObservabilityManager(
            metrics=metrics,
            tracer=tracer,
            logger_instance=log,
            health_checker=health,
            diagnostics=diagnostics,
            alert_manager=alerts,
            profiler=profiler,
            event_bus=event_bus,
        )

        engine = ObservabilityEngine(
            manager=manager,
            repository=repository,
            lifecycle=lifecycle,
        )
        logger.info("ObservabilityFactory created engine")
        return engine

    @staticmethod
    def create_engine_with_components() -> dict[str, Any]:
        """Create engine and return all components."""
        engine = ObservabilityFactory.create_engine()
        return {
            "engine": engine,
            "manager": engine.manager,
            "lifecycle": engine.lifecycle,
            "repository": engine.repository,
            "metrics": engine.manager.metrics,
            "tracer": engine.manager.tracer,
            "logger": engine.manager.logger,
            "health": engine.manager.health,
            "diagnostics": engine.manager.diagnostics,
            "alerts": engine.manager.alerts,
            "profiler": engine.manager.profiler,
            "event_bus": engine.manager.event_bus,
        }
