"""Pydantic schemas for the Observability API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    lifecycle_state: str = ""
    uptime_seconds: float = 0.0
    checks: list[dict[str, Any]] = Field(default_factory=list)


class ReadinessResponse(BaseModel):
    status: str = "ok"
    ready: bool = True
    dependencies: dict[str, str] = Field(default_factory=dict)


class LivenessResponse(BaseModel):
    status: str = "ok"
    alive: bool = True
    uptime_seconds: float = 0.0


class MetricsResponse(BaseModel):
    metrics: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class TracesResponse(BaseModel):
    traces: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class LogsResponse(BaseModel):
    logs: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class DiagnosticsResponse(BaseModel):
    dependencies: dict[str, Any] = Field(default_factory=dict)
    configuration: dict[str, Any] = Field(default_factory=dict)
    runtime: dict[str, Any] = Field(default_factory=dict)


class AlertsResponse(BaseModel):
    alerts: list[dict[str, Any]] = Field(default_factory=list)
    rules: list[dict[str, Any]] = Field(default_factory=list)
    total_alerts: int = 0


class StatisticsResponse(BaseModel):
    total_metrics: int = 0
    total_spans: int = 0
    total_logs: int = 0
    total_alerts: int = 0
    total_rules: int = 0
    uptime_seconds: float = 0.0
    lifecycle_state: str = ""


class PrometheusResponse(BaseModel):
    content: str = ""
    content_type: str = "text/plain"


class JSONExportResponse(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class CSVExportResponse(BaseModel):
    content: str = ""
    content_type: str = "text/csv"


class AlertRuleCreate(BaseModel):
    name: str
    metric_name: str
    condition: str = "gt"
    threshold: float = 0.0
    severity: str = "warning"
    cooldown_seconds: float = 60.0
    labels: dict[str, str] = Field(default_factory=dict)
