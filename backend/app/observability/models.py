"""Domain models for the Observability subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertState(str, Enum):
    PENDING = "pending"
    FIRING = "firing"
    RESOLVED = "resolved"


class LogSeverity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class ExportFormat(str, Enum):
    PROMETHEUS = "prometheus"
    OPENTELEMETRY = "opentelemetry"
    JSON = "json"
    CSV = "csv"


class CollectorType(str, Enum):
    SYSTEM = "system"
    APPLICATION = "application"
    AI = "ai"
    MEMORY = "memory"
    EXECUTION = "execution"


@dataclass
class MetricPoint:
    name: str = ""
    metric_type: MetricType = MetricType.COUNTER
    value: float = 0.0
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "value": self.value,
            "labels": self.labels,
            "timestamp": self.timestamp,
        }


@dataclass
class TraceSpan:
    span_id: str = ""
    name: str = ""
    parent_id: str | None = None
    trace_id: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    status: str = "ok"
    error: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "name": self.name,
            "parent_id": self.parent_id,
            "trace_id": self.trace_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error": self.error,
            "attributes": self.attributes,
        }


@dataclass
class LogEntry:
    entry_id: str = ""
    severity: LogSeverity = LogSeverity.INFO
    message: str = ""
    source: str = ""
    timestamp: float = 0.0
    correlation_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    request_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    agent_id: str | None = None
    workflow_id: str | None = None
    task_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "severity": self.severity.value,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "workflow_id": self.workflow_id,
            "task_id": self.task_id,
            "extra": self.extra,
        }


@dataclass
class AlertRule:
    rule_id: str = ""
    name: str = ""
    metric_name: str = ""
    condition: str = "gt"
    threshold: float = 0.0
    severity: AlertSeverity = AlertSeverity.WARNING
    cooldown_seconds: float = 60.0
    enabled: bool = True
    labels: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "metric_name": self.metric_name,
            "condition": self.condition,
            "threshold": self.threshold,
            "severity": self.severity.value,
            "cooldown_seconds": self.cooldown_seconds,
            "enabled": self.enabled,
            "labels": self.labels,
        }


@dataclass
class Alert:
    alert_id: str = ""
    rule_id: str = ""
    name: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    state: AlertState = AlertState.PENDING
    message: str = ""
    value: float = 0.0
    timestamp: float = 0.0
    resolved_at: float | None = None
    labels: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "name": self.name,
            "severity": self.severity.value,
            "state": self.state.value,
            "message": self.message,
            "value": self.value,
            "timestamp": self.timestamp,
            "resolved_at": self.resolved_at,
            "labels": self.labels,
        }


@dataclass
class HealthCheck:
    name: str = ""
    status: HealthStatus = HealthStatus.HEALTHY
    message: str = ""
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "latency_ms": self.latency_ms,
            "metadata": self.metadata,
        }


@dataclass
class DiagnosticReport:
    report_id: str = ""
    report_type: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "report_type": self.report_type,
            "data": self.data,
            "timestamp": self.timestamp,
        }
