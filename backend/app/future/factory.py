"""Factory for creating Future subsystem instances."""

from __future__ import annotations

from typing import Any

from app.future.capabilities import CapabilityRegistry
from app.future.compatibility import CompatibilityManager
from app.future.configuration import ConfigurationManager, FutureConfig
from app.future.deprecation import DeprecationManager
from app.future.experiments import ExperimentManager
from app.future.extension_points import ExtensionPointRegistry
from app.future.feature_flags import FeatureFlagManager
from app.future.lifecycle import LifecycleManager
from app.future.metrics import FutureMetrics
from app.future.registry import FutureRegistry
from app.future.roadmap import Roadmap
from app.future.tracing import FutureTracer
from app.future.versioning import VersionManager


class FutureFactory:
    @staticmethod
    def create_feature_flags() -> FeatureFlagManager:
        return FeatureFlagManager()

    @staticmethod
    def create_experiments() -> ExperimentManager:
        return ExperimentManager()

    @staticmethod
    def create_capabilities() -> CapabilityRegistry:
        return CapabilityRegistry()

    @staticmethod
    def create_compatibility() -> CompatibilityManager:
        return CompatibilityManager()

    @staticmethod
    def create_deprecation() -> DeprecationManager:
        return DeprecationManager()

    @staticmethod
    def create_extension_points() -> ExtensionPointRegistry:
        return ExtensionPointRegistry()

    @staticmethod
    def create_roadmap() -> Roadmap:
        return Roadmap()

    @staticmethod
    def create_lifecycle() -> LifecycleManager:
        return LifecycleManager()

    @staticmethod
    def create_versioning(current_version: str = "0.1.0") -> VersionManager:
        return VersionManager(current_version=current_version)

    @staticmethod
    def create_metrics() -> FutureMetrics:
        return FutureMetrics()

    @staticmethod
    def create_tracing() -> FutureTracer:
        return FutureTracer()

    @staticmethod
    def create_configuration(config: FutureConfig | None = None) -> ConfigurationManager:
        return ConfigurationManager(config=config)

    @staticmethod
    def create_registry() -> FutureRegistry:
        return FutureRegistry()

    @staticmethod
    def create_full(config: FutureConfig | None = None) -> dict[str, Any]:
        return {
            "feature_flags": FutureFactory.create_feature_flags(),
            "experiments": FutureFactory.create_experiments(),
            "capabilities": FutureFactory.create_capabilities(),
            "compatibility": FutureFactory.create_compatibility(),
            "deprecation": FutureFactory.create_deprecation(),
            "extension_points": FutureFactory.create_extension_points(),
            "roadmap": FutureFactory.create_roadmap(),
            "lifecycle": FutureFactory.create_lifecycle(),
            "versioning": FutureFactory.create_versioning(),
            "metrics": FutureFactory.create_metrics(),
            "tracing": FutureFactory.create_tracing(),
            "configuration": FutureFactory.create_configuration(config),
        }
