"""Pydantic schemas for the Future subsystem API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FeatureFlagResponse(BaseModel):
    name: str
    enabled: bool
    scope: str
    description: str = ""
    percentage: float = 100.0
    created_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class FeatureFlagsListResponse(BaseModel):
    total: int
    enabled: int
    disabled: int
    flags: list[FeatureFlagResponse] = Field(default_factory=list)


class ExperimentResponse(BaseModel):
    id: str
    name: str
    experiment_type: str
    state: str
    variants: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = ""
    started_at: str | None = None
    ended_at: str | None = None


class ExperimentsListResponse(BaseModel):
    total: int
    by_state: dict[str, int] = Field(default_factory=dict)
    experiments: list[ExperimentResponse] = Field(default_factory=list)


class CapabilityResponse(BaseModel):
    name: str
    version: str
    state: str
    description: str = ""
    provider: str = ""
    dependencies: list[str] = Field(default_factory=list)


class CapabilitiesListResponse(BaseModel):
    total: int
    by_state: dict[str, int] = Field(default_factory=dict)
    capabilities: list[CapabilityResponse] = Field(default_factory=list)


class CompatibilityCheckResponse(BaseModel):
    component: str
    from_version: str
    to_version: str
    level: str
    description: str = ""


class CompatibilityReportResponse(BaseModel):
    components: dict[str, str] = Field(default_factory=dict)
    checks: int = 0
    full: int = 0
    partial: int = 0
    incompatible: int = 0


class DeprecationResponse(BaseModel):
    feature: str
    severity: str
    message: str = ""
    deprecated_in: str = ""
    remove_in: str = ""
    migration_guide: str = ""


class DeprecationsListResponse(BaseModel):
    total: int
    by_severity: dict[str, int] = Field(default_factory=dict)
    deprecations: list[DeprecationResponse] = Field(default_factory=list)


class RoadmapItemResponse(BaseModel):
    id: str
    name: str
    description: str
    state: str
    version: str = "0.1.0"
    priority: int = 0
    tags: list[str] = Field(default_factory=list)


class RoadmapResponse(BaseModel):
    total: int
    by_state: dict[str, int] = Field(default_factory=dict)
    items: list[RoadmapItemResponse] = Field(default_factory=list)


class FutureMetricsResponse(BaseModel):
    metric_names: list[str] = Field(default_factory=list)
    total_points: int = 0
    by_name: dict[str, int] = Field(default_factory=dict)


class FutureStatisticsResponse(BaseModel):
    feature_flags: dict[str, Any] = Field(default_factory=dict)
    experiments: dict[str, Any] = Field(default_factory=dict)
    capabilities: dict[str, Any] = Field(default_factory=dict)
    compatibility: dict[str, Any] = Field(default_factory=dict)
    deprecation: dict[str, Any] = Field(default_factory=dict)
    roadmap: dict[str, Any] = Field(default_factory=dict)
    versioning: dict[str, Any] = Field(default_factory=dict)
    lifecycle: dict[str, Any] = Field(default_factory=dict)
    extensions: dict[str, Any] = Field(default_factory=dict)
