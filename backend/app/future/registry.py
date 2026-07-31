"""Central registry for the Future subsystem."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.future.capabilities import CapabilityRegistry
from app.future.compatibility import CompatibilityManager
from app.future.deprecation import DeprecationManager
from app.future.experiments import ExperimentManager
from app.future.extension_points import ExtensionPointRegistry
from app.future.feature_flags import FeatureFlagManager
from app.future.lifecycle import LifecycleManager
from app.future.metrics import FutureMetrics
from app.future.roadmap import Roadmap
from app.future.tracing import FutureTracer
from app.future.versioning import VersionManager


class FutureRegistry:
    """Central registry that wires all Future subsystem components together."""

    _instance: FutureRegistry | None = None
    _lock = threading.Lock()

    def __new__(cls) -> FutureRegistry:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self.feature_flags = FeatureFlagManager()
        self.experiments = ExperimentManager()
        self.capabilities = CapabilityRegistry()
        self.compatibility = CompatibilityManager()
        self.deprecation = DeprecationManager()
        self.extension_points = ExtensionPointRegistry()
        self.roadmap = Roadmap()
        self.lifecycle = LifecycleManager()
        self.versioning = VersionManager()
        self.metrics = FutureMetrics()
        self.tracing = FutureTracer()

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._instance = None

    def summary(self) -> dict[str, Any]:
        return {
            "feature_flags": self.feature_flags.summary(),
            "experiments": self.experiments.summary(),
            "capabilities": self.capabilities.summary(),
            "compatibility": self.compatibility.get_compatibility_report(),
            "deprecation": self.deprecation.summary(),
            "extensions": self.extension_points.summary(),
            "roadmap": self.roadmap.summary(),
            "lifecycle": self.lifecycle.summary(),
            "versioning": self.versioning.summary(),
            "metrics": self.metrics.summary(),
            "tracing": self.tracing.summary(),
        }
