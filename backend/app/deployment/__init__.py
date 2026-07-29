"""Deployment subsystem — Chapter 27.

Standardizes deployment, packaging, runtime configuration and production operations.
"""

from app.deployment.base import (
    ConfigurationProvider,
    DeploymentProvider,
    EnvironmentProvider,
    HealthProvider,
    SecretProvider,
)
from app.deployment.config import DeploymentConfiguration
from app.deployment.diagnostics import DeploymentDiagnostics
from app.deployment.environment import EnvironmentManager
from app.deployment.factory import DeploymentFactory
from app.deployment.health import (
    LivenessProbe,
    ReadinessProbe,
    StartupProbe,
)
from app.deployment.lifecycle import DeploymentLifecycle
from app.deployment.manager import DeploymentManager
from app.deployment.metrics import DeploymentMetricsCollector
from app.deployment.models import (
    ConfigurationItem,
    DeploymentHealth,
    DeploymentMetrics,
    DeploymentStatistics,
    EnvironmentVariable,
    HealthCheck,
    SecretInfo,
)
from app.deployment.readiness import ReadinessChecker
from app.deployment.secrets import SecretManager
from app.deployment.schemas import (
    ConfigurationResponse,
    DeploymentHealthResponse,
    DeploymentMetricsResponse,
    DeploymentStatisticsResponse,
    DiagnosticsResponse,
    EnvironmentResponse,
    LivenessResponse,
    ReadinessResponse,
    StartupResponse,
)
from app.deployment.tracing import DeploymentTracer
from app.deployment.validation import EnvironmentValidator

__all__ = [
    # ABCs
    "DeploymentProvider",
    "EnvironmentProvider",
    "ConfigurationProvider",
    "HealthProvider",
    "SecretProvider",
    # Models
    "DeploymentMetrics",
    "DeploymentHealth",
    "DeploymentStatistics",
    "ConfigurationItem",
    "EnvironmentVariable",
    "HealthCheck",
    "SecretInfo",
    # Core
    "DeploymentManager",
    "DeploymentLifecycle",
    "DeploymentConfiguration",
    "EnvironmentManager",
    "EnvironmentValidator",
    "SecretManager",
    "ReadinessChecker",
    "StartupProbe",
    "ReadinessProbe",
    "LivenessProbe",
    "DeploymentDiagnostics",
    "DeploymentMetricsCollector",
    "DeploymentTracer",
    # Schemas
    "DeploymentHealthResponse",
    "DeploymentStatisticsResponse",
    "EnvironmentResponse",
    "ConfigurationResponse",
    "DiagnosticsResponse",
    "DeploymentMetricsResponse",
    "ReadinessResponse",
    "LivenessResponse",
    "StartupResponse",
    # Factory
    "DeploymentFactory",
]
