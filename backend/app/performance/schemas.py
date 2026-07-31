"""Performance API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProfileRequest(BaseModel):
    """Request to start profiling."""

    profile_type: str = Field(default="comprehensive", description="Profile type")
    target: str | None = Field(default=None, description="Specific component to profile")
    duration_seconds: float = Field(default=30.0, description="Max profiling duration")


class BenchmarkRunRequest(BaseModel):
    """Request to run a benchmark."""

    category: str = Field(..., description="Benchmark category")
    iterations: int = Field(default=100, description="Number of iterations")
    warmup: int = Field(default=10, description="Warmup iterations")


class OptimizationRecommendation(BaseModel):
    """A single optimization recommendation."""

    area: str = Field(..., description="Optimization area")
    severity: str = Field(..., description="Severity level")
    title: str = Field(..., description="Recommendation title")
    description: str = Field(..., description="Detailed description")
    expected_improvement: str = Field(default="", description="Expected performance improvement")


class HealthResponse(BaseModel):
    """Performance health response."""

    status: str = Field(..., description="Health status")
    profiler_active: bool = Field(..., description="Whether profiler is active")
    active_sessions: int = Field(..., description="Number of active profiling sessions")
    total_benchmarks: int = Field(..., description="Total benchmarks run")


class ProfileResponse(BaseModel):
    """Profiling response."""

    session_id: str = Field(..., description="Profiling session ID")
    state: str = Field(..., description="Session state")
    results: dict[str, Any] = Field(default_factory=dict, description="Profile results")


class BenchmarkResponse(BaseModel):
    """Benchmark response."""

    category: str = Field(..., description="Benchmark category")
    results: list[dict[str, Any]] = Field(..., description="Benchmark results")
    summary: dict[str, Any] = Field(..., description="Summary statistics")


class DiagnosticsResponse(BaseModel):
    """Diagnostics response."""

    hotspots: list[dict[str, Any]] = Field(..., description="Performance hotspots")
    bottlenecks: list[dict[str, Any]] = Field(..., description="Identified bottlenecks")
    slow_queries: list[dict[str, Any]] = Field(..., description="Slow database queries")
    allocations: list[dict[str, Any]] = Field(..., description="Excessive allocations")
    blocking_calls: list[dict[str, Any]] = Field(..., description="Blocking calls detected")


class RecommendationsResponse(BaseModel):
    """Optimization recommendations response."""

    recommendations: list[dict[str, Any]] = Field(..., description="Recommendations")
    total: int = Field(..., description="Total recommendations")
    summary: dict[str, Any] = Field(..., description="Summary by severity")


class MetricsResponse(BaseModel):
    """Performance metrics response."""

    latency: dict[str, float] = Field(default_factory=dict, description="Latency metrics")
    throughput: dict[str, float] = Field(default_factory=dict, description="Throughput metrics")
    cache: dict[str, float] = Field(default_factory=dict, description="Cache metrics")
    resources: dict[str, float] = Field(default_factory=dict, description="Resource metrics")


class TracesResponse(BaseModel):
    """Performance traces response."""

    traces: list[dict[str, Any]] = Field(..., description="Recent traces")
    total: int = Field(..., description="Total traces recorded")
