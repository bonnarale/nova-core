"""Enums for the Future Roadmap subsystem."""

from __future__ import annotations

from enum import Enum


class FeatureState(str, Enum):
    DISABLED = "disabled"
    ENABLED = "enabled"
    EXPERIMENTAL = "experimental"
    BETA = "beta"
    STABLE = "stable"
    DEPRECATED = "deprecated"
    REMOVED = "removed"


class ExperimentType(str, Enum):
    A_B = "a_b"
    CANARY = "canary"
    SHADOW = "shadow"
    MULTIVARIATE = "multivariate"


class ExperimentState(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CapabilityState(str, Enum):
    REGISTERED = "registered"
    EXPERIMENTAL = "experimental"
    BETA = "beta"
    STABLE = "stable"
    DEPRECATED = "deprecated"
    REMOVED = "removed"


class CompatibilityLevel(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    INCOMPATIBLE = "incompatible"


class DeprecationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class VersionBumpType(str, Enum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


class FlagScope(str, Enum):
    GLOBAL = "global"
    USER = "user"
    ENVIRONMENT = "environment"
    PERCENTAGE = "percentage"
    SCHEDULED = "scheduled"
