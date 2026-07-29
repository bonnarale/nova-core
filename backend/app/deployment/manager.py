"""Deployment manager — top-level orchestrator."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.deployment.config import DeploymentConfiguration
from app.deployment.diagnostics import DeploymentDiagnostics
from app.deployment.enums import DeployState, HealthStatus
from app.deployment.environment import EnvironmentManager
from app.deployment.health import LivenessProbe, ReadinessProbe, StartupProbe
from app.deployment.lifecycle import DeploymentLifecycle
from app.deployment.metrics import DeploymentMetricsCollector
from app.deployment.models import DeploymentHealth, DeploymentStatistics
from app.deployment.readiness import ReadinessChecker
from app.deployment.secrets import SecretManager
from app.deployment.shutdown import GracefulShutdown
from app.deployment.tracing import DeploymentTracer
from app.deployment.validation import EnvironmentValidator

logger = logging.getLogger(__name__)


class DeploymentManager:
    """Top-level orchestrator for the deployment subsystem."""

    def __init__(
        self,
        environment: str = "development",
    ) -> None:
        self._lifecycle = DeploymentLifecycle()
        self._config = DeploymentConfiguration(environment)
        self._env_manager = EnvironmentManager()
        self._env_validator = EnvironmentValidator()
        self._secret_manager = SecretManager()
        self._readiness = ReadinessChecker()
        self._startup_probe = StartupProbe()
        self._readiness_probe = ReadinessProbe()
        self._liveness_probe = LivenessProbe()
        self._shutdown = GracefulShutdown()
        self._diagnostics = DeploymentDiagnostics()
        self._metrics = DeploymentMetricsCollector()
        self._tracer = DeploymentTracer()
        self._start_time: float = 0.0

    @property
    def lifecycle(self) -> DeploymentLifecycle:
        return self._lifecycle

    @property
    def configuration(self) -> DeploymentConfiguration:
        return self._config

    async def start(self) -> None:
        trace_id = self._tracer.start_trace("deployment.start")
        start = time.time()

        self._lifecycle.transition(DeployState.INITIALIZING, "start called")
        await self._startup_probe.start()
        self._liveness_probe.mark_started()

        self._lifecycle.transition(DeployState.STARTING, "initializing components")

        env_validation = self._env_validator.validate()
        self._diagnostics.add_check(
            "environment",
            env_validation["valid"],
            env_validation,
        )

        config_validation = await self._config.validate()
        self._diagnostics.add_check(
            "configuration",
            config_validation["valid"],
            config_validation,
        )

        await self._startup_probe.complete()
        self._lifecycle.transition(DeployState.RUNNING, "startup complete")

        self._start_time = time.time()
        duration_ms = (time.time() - start) * 1000
        self._metrics.record_startup(duration_ms)
        self._tracer.finish_trace(trace_id)
        logger.info("Deployment started in %.2fms", duration_ms)

    async def shutdown(self) -> None:
        trace_id = self._tracer.start_trace("deployment.shutdown")
        start = time.time()

        self._lifecycle.transition(DeployState.SHUTTING_DOWN, "shutdown called")
        result = await self._shutdown.execute()

        self._lifecycle.transition(DeployState.STOPPED, "shutdown complete")

        duration_ms = (time.time() - start) * 1000
        self._metrics.record_shutdown(duration_ms)
        self._tracer.finish_trace(trace_id)
        logger.info("Deployment stopped in %.2fms", duration_ms)

    async def health(self) -> dict[str, Any]:
        self._metrics.record_health_check()
        startup = await self._startup_probe.check()
        readiness = await self._readiness.check_readiness()
        liveness = await self._liveness_probe.check()

        checks = await self._diagnostics.collect()
        all_ok = (
            startup.status == HealthStatus.HEALTHY.value
            and readiness.get("ready", False)
            and liveness.status == HealthStatus.HEALTHY.value
        )
        health = DeploymentHealth(
            status=HealthStatus.HEALTHY.value if all_ok else HealthStatus.DEGRADED.value,
            startup=startup.status == HealthStatus.HEALTHY.value,
            readiness=readiness.get("ready", False),
            liveness=liveness.status == HealthStatus.HEALTHY.value,
            details=checks,
        )
        return health.to_dict()

    async def readiness(self) -> dict[str, Any]:
        return await self._readiness.check_readiness()

    async def liveness(self) -> dict[str, Any]:
        check = await self._liveness_probe.check()
        return check.to_dict()

    async def environment(self) -> dict[str, Any]:
        return await self._env_manager.get_all()

    async def diagnostics(self) -> dict[str, Any]:
        return await self._diagnostics.collect()

    async def statistics(self) -> DeploymentStatistics:
        stats = DeploymentStatistics(
            state=self._lifecycle.state.value,
            environment=self._config.environment.value,
            uptime_seconds=self._lifecycle.uptime(),
            health_checks=self._metrics.get_statistics()["total_health_checks"],
            restarts=self._metrics.get_statistics()["total_restarts"],
        )
        return stats

    def register_shutdown_handler(self, name: str, handler: Any) -> None:
        self._shutdown.register_handler(name, handler)

    def register_readiness_check(self, name: str, healthy: bool) -> None:
        self._readiness.register_check(name, healthy)

    @property
    def is_running(self) -> bool:
        return self._lifecycle.is_running()
