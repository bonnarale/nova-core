"""Factory for creating Deployment components."""

from __future__ import annotations

import logging
from typing import Any

from app.deployment.config import DeploymentConfiguration
from app.deployment.diagnostics import DeploymentDiagnostics
from app.deployment.enums import DeployEnvironment, SecretSource
from app.deployment.environment import EnvironmentManager
from app.deployment.health import LivenessProbe, ReadinessProbe, StartupProbe
from app.deployment.lifecycle import DeploymentLifecycle
from app.deployment.manager import DeploymentManager
from app.deployment.metrics import DeploymentMetricsCollector
from app.deployment.readiness import ReadinessChecker
from app.deployment.secrets import SecretManager
from app.deployment.shutdown import GracefulShutdown
from app.deployment.tracing import DeploymentTracer
from app.deployment.validation import EnvironmentValidator

logger = logging.getLogger(__name__)


class DeploymentFactory:
    """Creates all Deployment subsystem components."""

    @staticmethod
    def create_all(environment: str = "development") -> dict[str, Any]:
        manager = DeploymentManager(environment=environment)
        lifecycle = manager.lifecycle
        config = manager.configuration
        env_manager = EnvironmentManager()
        env_validator = EnvironmentValidator()
        secret_manager = SecretManager()
        readiness = ReadinessChecker()
        startup_probe = StartupProbe()
        readiness_probe = ReadinessProbe()
        liveness_probe = LivenessProbe()
        shutdown = GracefulShutdown()
        diagnostics = DeploymentDiagnostics()
        metrics = DeploymentMetricsCollector()
        tracer = DeploymentTracer()

        return {
            "manager": manager,
            "lifecycle": lifecycle,
            "config": config,
            "env_manager": env_manager,
            "env_validator": env_validator,
            "secret_manager": secret_manager,
            "readiness": readiness,
            "startup_probe": startup_probe,
            "readiness_probe": readiness_probe,
            "liveness_probe": liveness_probe,
            "shutdown": shutdown,
            "diagnostics": diagnostics,
            "metrics": metrics,
            "tracer": tracer,
        }

    @staticmethod
    def create_manager(environment: str = "development") -> DeploymentManager:
        return DeploymentManager(environment=environment)

    @staticmethod
    def create_lifecycle() -> DeploymentLifecycle:
        return DeploymentLifecycle()

    @staticmethod
    def create_configuration(environment: str = "development") -> DeploymentConfiguration:
        return DeploymentConfiguration(environment)

    @staticmethod
    def create_environment_manager(env: dict[str, str] | None = None) -> EnvironmentManager:
        return EnvironmentManager(env=env)

    @staticmethod
    def create_environment_validator(
        required: list[str] | None = None,
        optional: dict[str, str] | None = None,
    ) -> EnvironmentValidator:
        return EnvironmentValidator(required=required, optional=optional)

    @staticmethod
    def create_secret_manager(
        source: SecretSource = SecretSource.ENVIRONMENT,
        secrets_dir: str = "/run/secrets",
    ) -> SecretManager:
        return SecretManager(source=source, secrets_dir=secrets_dir)

    @staticmethod
    def create_readiness_checker() -> ReadinessChecker:
        return ReadinessChecker()

    @staticmethod
    def create_startup_probe(timeout: float = 60.0) -> StartupProbe:
        return StartupProbe(timeout=timeout)

    @staticmethod
    def create_readiness_probe() -> ReadinessProbe:
        return ReadinessProbe()

    @staticmethod
    def create_liveness_probe() -> LivenessProbe:
        return LivenessProbe()

    @staticmethod
    def create_shutdown(timeout: float = 30.0) -> GracefulShutdown:
        return GracefulShutdown(timeout=timeout)

    @staticmethod
    def create_diagnostics() -> DeploymentDiagnostics:
        return DeploymentDiagnostics()

    @staticmethod
    def create_metrics() -> DeploymentMetricsCollector:
        return DeploymentMetricsCollector()

    @staticmethod
    def create_tracer() -> DeploymentTracer:
        return DeploymentTracer()
