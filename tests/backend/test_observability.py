"""Tests for Observability subsystem — models, base ABCs, lifecycle, metrics,
tracing, logging, health, diagnostics, alerts, profiler, monitor, events,
collectors, exporters, repository, persistence, manager, engine, factory, and API routes.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.observability.alerts import AlertManager
from app.observability.base import (
    AlertProvider,
    DiagnosticsProvider,
    ExporterProvider,
    HealthProvider,
    LoggingProvider,
    MetricsProvider,
    ObservabilityProvider,
    TracingProvider,
)
from app.observability.collectors import (
    AICollector,
    ApplicationCollector,
    BaseCollector,
    CollectorRegistry,
    CollectorType,
    ExecutionCollector,
    MemoryCollector,
    SystemCollector,
)
from app.observability.diagnostics import DiagnosticsEngine
from app.observability.engine import ObservabilityEngine
from app.observability.events import ObservabilityEvent, ObservabilityEventBus
from app.observability.exporters import (
    CSVExporter,
    ExportManager,
    JSONExporter,
    OpenTelemetryExporter,
    PrometheusExporter,
)
from app.observability.factory import ObservabilityFactory
from app.observability.health import HealthChecker
from app.observability.lifecycle import ObservabilityLifecycle, ObservabilityLifecycleState
from app.observability.logging import ObservabilityLogger
from app.observability.manager import ObservabilityManager
from app.observability.metrics import ObservabilityMetrics, get_observability_metrics
from app.observability.models import (
    Alert,
    AlertRule,
    AlertSeverity,
    AlertState,
    CollectorType as CollectorTypeEnum,
    DiagnosticReport,
    ExportFormat,
    HealthCheck,
    HealthStatus,
    LogEntry,
    LogSeverity,
    MetricPoint,
    MetricType,
    TraceSpan,
)
from app.observability.monitor import ApplicationMonitor, SystemMonitor
from app.observability.persistence import InMemoryObservabilityPersistence
from app.observability.profiler import Profiler, ProfileSpan
from app.observability.repository import InMemoryObservabilityRepository
from app.observability.schemas import (
    AlertsResponse,
    CSVExportResponse,
    DiagnosticsResponse,
    HealthResponse,
    JSONExportResponse,
    LivenessResponse,
    LogsResponse,
    MetricsResponse,
    PrometheusResponse,
    ReadinessResponse,
    StatisticsResponse,
    TracesResponse,
)
from app.observability.tracing import ObservabilityTracer


# ======================================================================
# Domain model tests
# ======================================================================

class TestEnums:
    def test_health_status_values(self):
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"

    def test_alert_severity_values(self):
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"

    def test_alert_state_values(self):
        assert AlertState.PENDING.value == "pending"
        assert AlertState.FIRING.value == "firing"
        assert AlertState.RESOLVED.value == "resolved"

    def test_log_severity_values(self):
        assert LogSeverity.DEBUG.value == "debug"
        assert LogSeverity.INFO.value == "info"
        assert LogSeverity.WARNING.value == "warning"
        assert LogSeverity.ERROR.value == "error"
        assert LogSeverity.CRITICAL.value == "critical"

    def test_metric_type_values(self):
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"
        assert MetricType.SUMMARY.value == "summary"

    def test_export_format_values(self):
        assert ExportFormat.PROMETHEUS.value == "prometheus"
        assert ExportFormat.OPENTELEMETRY.value == "opentelemetry"
        assert ExportFormat.JSON.value == "json"
        assert ExportFormat.CSV.value == "csv"

    def test_collector_type_values(self):
        assert CollectorType.SYSTEM.value == "system"
        assert CollectorType.APPLICATION.value == "application"
        assert CollectorType.AI.value == "ai"
        assert CollectorType.MEMORY.value == "memory"
        assert CollectorType.EXECUTION.value == "execution"


class TestMetricPoint:
    def test_default_construction(self):
        m = MetricPoint()
        assert m.name == ""
        assert m.metric_type == MetricType.COUNTER
        assert m.value == 0.0
        assert m.labels == {}
        assert m.timestamp == 0.0

    def test_to_dict(self):
        m = MetricPoint(
            name="requests",
            metric_type=MetricType.COUNTER,
            value=42.0,
            labels={"env": "prod"},
            timestamp=1234567890.0,
        )
        d = m.to_dict()
        assert d["name"] == "requests"
        assert d["type"] == "counter"
        assert d["value"] == 42.0
        assert d["labels"] == {"env": "prod"}
        assert d["timestamp"] == 1234567890.0


class TestTraceSpan:
    def test_default_construction(self):
        s = TraceSpan()
        assert s.span_id == ""
        assert s.name == ""
        assert s.parent_id is None
        assert s.status == "ok"

    def test_to_dict(self):
        s = TraceSpan(
            span_id="sp1",
            name="test",
            parent_id="p1",
            trace_id="t1",
            start_time=1.0,
            end_time=2.0,
            duration_ms=1000.0,
            status="ok",
            error=None,
            attributes={"key": "val"},
        )
        d = s.to_dict()
        assert d["span_id"] == "sp1"
        assert d["name"] == "test"
        assert d["duration_ms"] == 1000.0
        assert d["attributes"] == {"key": "val"}


class TestLogEntry:
    def test_default_construction(self):
        e = LogEntry()
        assert e.entry_id == ""
        assert e.severity == LogSeverity.INFO
        assert e.message == ""

    def test_to_dict(self):
        e = LogEntry(
            entry_id="e1",
            severity=LogSeverity.ERROR,
            message="boom",
            source="test",
            timestamp=100.0,
        )
        d = e.to_dict()
        assert d["entry_id"] == "e1"
        assert d["severity"] == "error"
        assert d["message"] == "boom"


class TestAlertRule:
    def test_default_construction(self):
        r = AlertRule()
        assert r.rule_id == ""
        assert r.condition == "gt"
        assert r.enabled is True

    def test_to_dict(self):
        r = AlertRule(
            rule_id="r1",
            name="high_cpu",
            metric_name="cpu",
            condition="gt",
            threshold=90.0,
            severity=AlertSeverity.CRITICAL,
        )
        d = r.to_dict()
        assert d["rule_id"] == "r1"
        assert d["severity"] == "critical"
        assert d["threshold"] == 90.0


class TestAlert:
    def test_default_construction(self):
        a = Alert()
        assert a.alert_id == ""
        assert a.state == AlertState.PENDING

    def test_to_dict(self):
        a = Alert(
            alert_id="a1",
            rule_id="r1",
            name="high_cpu",
            severity=AlertSeverity.WARNING,
            state=AlertState.FIRING,
            message="CPU high",
            value=95.0,
        )
        d = a.to_dict()
        assert d["alert_id"] == "a1"
        assert d["state"] == "firing"
        assert d["value"] == 95.0


class TestHealthCheck:
    def test_default_construction(self):
        h = HealthCheck()
        assert h.name == ""
        assert h.status == HealthStatus.HEALTHY

    def test_to_dict(self):
        h = HealthCheck(name="db", status=HealthStatus.HEALTHY, message="ok", latency_ms=1.5)
        d = h.to_dict()
        assert d["name"] == "db"
        assert d["status"] == "healthy"
        assert d["latency_ms"] == 1.5


class TestDiagnosticReport:
    def test_default_construction(self):
        r = DiagnosticReport()
        assert r.report_id == ""

    def test_to_dict(self):
        r = DiagnosticReport(report_id="dr1", report_type="runtime", data={"threads": 10})
        d = r.to_dict()
        assert d["report_id"] == "dr1"
        assert d["data"]["threads"] == 10


# ======================================================================
# Base ABC tests
# ======================================================================

class TestBaseABCs:
    def test_cannot_instantiate_observability_provider(self):
        with pytest.raises(TypeError):
            ObservabilityProvider()

    def test_cannot_instantiate_metrics_provider(self):
        with pytest.raises(TypeError):
            MetricsProvider()

    def test_cannot_instantiate_tracing_provider(self):
        with pytest.raises(TypeError):
            TracingProvider()

    def test_cannot_instantiate_logging_provider(self):
        with pytest.raises(TypeError):
            LoggingProvider()

    def test_cannot_instantiate_health_provider(self):
        with pytest.raises(TypeError):
            HealthProvider()

    def test_cannot_instantiate_diagnostics_provider(self):
        with pytest.raises(TypeError):
            DiagnosticsProvider()

    def test_cannot_instantiate_alert_provider(self):
        with pytest.raises(TypeError):
            AlertProvider()

    def test_cannot_instantiate_exporter_provider(self):
        with pytest.raises(TypeError):
            ExporterProvider()


# ======================================================================
# Lifecycle tests
# ======================================================================

class TestObservabilityLifecycle:
    def test_initial_state(self):
        lc = ObservabilityLifecycle()
        assert lc.state == ObservabilityLifecycleState.REGISTERED

    def test_valid_transitions(self):
        lc = ObservabilityLifecycle()
        assert lc.transition(ObservabilityLifecycleState.INITIALIZED) is True
        assert lc.state == ObservabilityLifecycleState.INITIALIZED
        assert lc.transition(ObservabilityLifecycleState.READY) is True
        assert lc.state == ObservabilityLifecycleState.READY
        assert lc.transition(ObservabilityLifecycleState.RUNNING) is True
        assert lc.state == ObservabilityLifecycleState.RUNNING

    def test_invalid_transition(self):
        lc = ObservabilityLifecycle()
        assert lc.transition(ObservabilityLifecycleState.RUNNING) is False
        assert lc.state == ObservabilityLifecycleState.REGISTERED

    def test_uptime_seconds(self):
        lc = ObservabilityLifecycle()
        lc.transition(ObservabilityLifecycleState.INITIALIZED)
        lc.transition(ObservabilityLifecycleState.READY)
        lc.transition(ObservabilityLifecycleState.RUNNING)
        assert lc.uptime_seconds >= 0.0

    def test_can_transition(self):
        lc = ObservabilityLifecycle()
        assert lc.can_transition(ObservabilityLifecycleState.INITIALIZED) is True
        assert lc.can_transition(ObservabilityLifecycleState.RUNNING) is False

    def test_transition_history(self):
        lc = ObservabilityLifecycle()
        lc.transition(ObservabilityLifecycleState.INITIALIZED)
        lc.transition(ObservabilityLifecycleState.READY)
        assert len(lc.transition_history) == 2

    def test_shutdown_transition(self):
        lc = ObservabilityLifecycle()
        lc.transition(ObservabilityLifecycleState.INITIALIZED)
        lc.transition(ObservabilityLifecycleState.READY)
        lc.transition(ObservabilityLifecycleState.RUNNING)
        lc.transition(ObservabilityLifecycleState.SHUTDOWN)
        assert lc.state == ObservabilityLifecycleState.SHUTDOWN
        assert lc.stopped_at is not None

    def test_reset(self):
        lc = ObservabilityLifecycle()
        lc.transition(ObservabilityLifecycleState.INITIALIZED)
        lc.reset()
        assert lc.state == ObservabilityLifecycleState.REGISTERED
        assert lc.started_at is None
        assert lc.stopped_at is None
        assert len(lc.transition_history) == 0

    def test_same_state_transition_returns_true(self):
        lc = ObservabilityLifecycle()
        assert lc.transition(ObservabilityLifecycleState.REGISTERED) is True


# ======================================================================
# Metrics tests
# ======================================================================

class TestObservabilityMetrics:
    def setup_method(self):
        ObservabilityMetrics.reset_singleton()

    def teardown_method(self):
        ObservabilityMetrics.reset_singleton()

    def test_singleton(self):
        m1 = ObservabilityMetrics()
        m2 = ObservabilityMetrics()
        assert m1 is m2

    def test_record_counter(self):
        m = ObservabilityMetrics()
        m.record_counter("requests", 1.0)
        m.record_counter("requests", 2.0)
        assert m.get_counter("requests") == 3.0

    def test_record_gauge(self):
        m = ObservabilityMetrics()
        m.record_gauge("temperature", 25.5)
        assert m.get_gauge("temperature") == 25.5

    def test_record_histogram(self):
        m = ObservabilityMetrics()
        m.record_histogram("latency", 10.0)
        m.record_histogram("latency", 20.0)
        assert m.get_histogram("latency") == [10.0, 20.0]

    def test_histogram_stats(self):
        m = ObservabilityMetrics()
        m.record_histogram("latency", 10.0)
        m.record_histogram("latency", 20.0)
        m.record_histogram("latency", 30.0)
        stats = m.get_histogram_stats("latency")
        assert stats["count"] == 3
        assert stats["min"] == 10.0
        assert stats["max"] == 30.0
        assert stats["mean"] == 20.0
        assert stats["sum"] == 60.0

    def test_histogram_stats_empty(self):
        m = ObservabilityMetrics()
        stats = m.get_histogram_stats("nonexistent")
        assert stats["count"] == 0

    def test_get_metric(self):
        m = ObservabilityMetrics()
        m.record_counter("req", 1.0)
        found = m.get_metric("req")
        assert found is not None
        assert found.name == "req"

    def test_get_metric_not_found(self):
        m = ObservabilityMetrics()
        assert m.get_metric("nonexistent") is None

    def test_get_all_metrics(self):
        m = ObservabilityMetrics()
        m.record_counter("a", 1.0)
        m.record_gauge("b", 2.0)
        all_m = m.get_all_metrics()
        assert len(all_m) >= 2

    def test_to_dict(self):
        m = ObservabilityMetrics()
        m.record_counter("c", 5.0)
        d = m.to_dict()
        assert "counters" in d
        assert "gauges" in d
        assert "histograms" in d
        assert "total_metric_points" in d

    def test_uptime_seconds(self):
        m = ObservabilityMetrics()
        assert m.uptime_seconds >= 0.0

    def test_metric_count(self):
        m = ObservabilityMetrics()
        assert m.metric_count == 0
        m.record_counter("x", 1.0)
        assert m.metric_count == 1

    def test_reset(self):
        m = ObservabilityMetrics()
        m.record_counter("x", 1.0)
        m.reset()
        assert m.metric_count == 0
        assert m.get_counter("x") == 0.0

    def test_get_observability_metrics_factory(self):
        m = get_observability_metrics()
        assert isinstance(m, ObservabilityMetrics)


# ======================================================================
# Tracing tests
# ======================================================================

class TestObservabilityTracer:
    def test_start_and_end_span(self):
        t = ObservabilityTracer()
        span = t.start_span("test")
        assert span.name == "test"
        assert span.span_id != ""
        t.end_span(span)
        assert span.duration_ms >= 0.0
        assert t.span_count == 1

    def test_parent_span(self):
        t = ObservabilityTracer()
        parent = t.start_span("parent")
        child = t.start_span("child", parent_id=parent.span_id)
        t.end_span(parent)
        t.end_span(child)
        assert child.parent_id == parent.span_id

    def test_get_traces(self):
        t = ObservabilityTracer()
        s1 = t.start_span("a")
        t.end_span(s1)
        s2 = t.start_span("b")
        t.end_span(s2)
        traces = t.get_traces()
        assert len(traces) == 2

    def test_get_traces_by_name(self):
        t = ObservabilityTracer()
        s1 = t.start_span("a")
        t.end_span(s1)
        s2 = t.start_span("b")
        t.end_span(s2)
        traces = t.get_traces(name="a")
        assert len(traces) == 1
        assert traces[0]["name"] == "a"

    def test_get_traces_with_limit(self):
        t = ObservabilityTracer()
        for i in range(5):
            s = t.start_span(f"s{i}")
            t.end_span(s)
        traces = t.get_traces(limit=2)
        assert len(traces) == 2

    def test_get_span(self):
        t = ObservabilityTracer()
        s = t.start_span("test")
        found = t.get_span(s.span_id)
        assert found is not None
        t.end_span(s)

    def test_get_span_not_found(self):
        t = ObservabilityTracer()
        assert t.get_span("nonexistent") is None

    def test_get_traces_by_trace_id(self):
        t = ObservabilityTracer()
        s1 = t.start_span("a", trace_id="tr1")
        t.end_span(s1)
        s2 = t.start_span("b", trace_id="tr1")
        t.end_span(s2)
        traces = t.get_traces_by_trace_id("tr1")
        assert len(traces) == 2

    def test_clear(self):
        t = ObservabilityTracer()
        s = t.start_span("a")
        t.end_span(s)
        count = t.clear()
        assert count == 1
        assert t.span_count == 0

    def test_to_dict(self):
        t = ObservabilityTracer()
        s = t.start_span("a")
        t.end_span(s)
        d = t.to_dict()
        assert "traces" in d
        assert "total" in d

    def test_max_spans_eviction(self):
        t = ObservabilityTracer(max_spans=2)
        for i in range(5):
            s = t.start_span(f"s{i}")
            t.end_span(s)
        assert t.span_count == 2

    def test_get_active_span(self):
        t = ObservabilityTracer()
        s = t.start_span("active")
        found = t.get_span(s.span_id)
        assert found is not None
        t.end_span(s)


# ======================================================================
# Logging tests
# ======================================================================

class TestObservabilityLogger:
    def test_log_entry(self):
        l = ObservabilityLogger()
        entry = l.log("info", "hello world")
        assert entry.message == "hello world"
        assert entry.severity == LogSeverity.INFO
        assert l.entry_count == 1

    def test_convenience_methods(self):
        l = ObservabilityLogger()
        l.debug("d")
        l.info("i")
        l.warning("w")
        l.error("e")
        l.critical("c")
        assert l.entry_count == 5

    def test_get_logs(self):
        l = ObservabilityLogger()
        l.info("msg1")
        l.error("msg2")
        l.info("msg3")
        logs = l.get_logs()
        assert len(logs) == 3

    def test_get_logs_by_severity(self):
        l = ObservabilityLogger()
        l.info("i")
        l.error("e")
        l.info("i2")
        logs = l.get_logs(severity="error")
        assert len(logs) == 1

    def test_get_log(self):
        l = ObservabilityLogger()
        entry = l.info("test")
        found = l.get_log(entry.entry_id)
        assert found is not None

    def test_get_log_not_found(self):
        l = ObservabilityLogger()
        assert l.get_log("nonexistent") is None

    def test_clear(self):
        l = ObservabilityLogger()
        l.info("test")
        count = l.clear()
        assert count == 1
        assert l.entry_count == 0

    def test_to_dict(self):
        l = ObservabilityLogger()
        l.info("test")
        d = l.to_dict()
        assert "logs" in d
        assert "total" in d

    def test_max_entries_eviction(self):
        l = ObservabilityLogger(max_entries=2)
        l.info("a")
        l.info("b")
        l.info("c")
        assert l.entry_count == 2

    def test_log_with_context(self):
        l = ObservabilityLogger()
        entry = l.info("test", user_id="u1", agent_id="a1")
        assert entry.user_id == "u1"
        assert entry.agent_id == "a1"


# ======================================================================
# Health tests
# ======================================================================

class TestHealthChecker:
    @pytest.mark.asyncio
    async def test_check_readiness(self):
        lc = ObservabilityLifecycle()
        lc.transition(ObservabilityLifecycleState.INITIALIZED)
        lc.transition(ObservabilityLifecycleState.READY)
        hc = HealthChecker(lifecycle=lc)
        result = await hc.check_readiness()
        assert result["ready"] is True

    @pytest.mark.asyncio
    async def test_check_liveness(self):
        lc = ObservabilityLifecycle()
        lc.transition(ObservabilityLifecycleState.INITIALIZED)
        lc.transition(ObservabilityLifecycleState.READY)
        lc.transition(ObservabilityLifecycleState.RUNNING)
        hc = HealthChecker(lifecycle=lc)
        result = await hc.check_liveness()
        assert result["alive"] is True

    @pytest.mark.asyncio
    async def test_check_startup(self):
        lc = ObservabilityLifecycle()
        lc.transition(ObservabilityLifecycleState.INITIALIZED)
        lc.transition(ObservabilityLifecycleState.READY)
        lc.transition(ObservabilityLifecycleState.RUNNING)
        hc = HealthChecker(lifecycle=lc)
        result = await hc.check_startup()
        assert result["started"] is True

    @pytest.mark.asyncio
    async def test_liveness_after_shutdown(self):
        lc = ObservabilityLifecycle()
        lc.transition(ObservabilityLifecycleState.INITIALIZED)
        lc.transition(ObservabilityLifecycleState.READY)
        lc.transition(ObservabilityLifecycleState.RUNNING)
        lc.transition(ObservabilityLifecycleState.SHUTDOWN)
        hc = HealthChecker(lifecycle=lc)
        result = await hc.check_liveness()
        assert result["alive"] is False

    def test_register_check(self):
        hc = HealthChecker()
        check = HealthCheck(name="db", status=HealthStatus.HEALTHY)
        hc.register_check("db", check)
        assert "db" in hc.get_all_checks()

    def test_unregister_check(self):
        hc = HealthChecker()
        check = HealthCheck(name="db", status=HealthStatus.HEALTHY)
        hc.register_check("db", check)
        assert hc.unregister_check("db") is True
        assert hc.unregister_check("db") is False

    @pytest.mark.asyncio
    async def test_register_dependency(self):
        hc = HealthChecker()
        dep = HealthCheck(name="redis", status=HealthStatus.HEALTHY)
        hc.register_dependency("redis", dep)
        result = await hc.get_dependency_health()
        assert "redis" in result

    def test_unregister_dependency(self):
        hc = HealthChecker()
        dep = HealthCheck(name="redis", status=HealthStatus.HEALTHY)
        hc.register_dependency("redis", dep)
        assert hc.unregister_dependency("redis") is True
        assert hc.unregister_dependency("redis") is False

    def test_clear_checks(self):
        hc = HealthChecker()
        hc.register_check("a", HealthCheck(name="a"))
        count = hc.clear_checks()
        assert count == 1

    def test_clear_dependencies(self):
        hc = HealthChecker()
        hc.register_dependency("a", HealthCheck(name="a"))
        count = hc.clear_dependencies()
        assert count == 1

    def test_to_dict(self):
        hc = HealthChecker()
        hc.register_check("a", HealthCheck(name="a"))
        hc.register_dependency("b", HealthCheck(name="b"))
        d = hc.to_dict()
        assert "checks" in d
        assert "dependencies" in d


# ======================================================================
# Diagnostics tests
# ======================================================================

class TestDiagnosticsEngine:
    @pytest.mark.asyncio
    async def test_inspect_dependencies(self):
        d = DiagnosticsEngine()
        result = await d.inspect_dependencies()
        assert "python" in result
        assert "platform" in result

    @pytest.mark.asyncio
    async def test_inspect_configuration(self):
        d = DiagnosticsEngine()
        result = await d.inspect_configuration()
        assert "pid" in result
        assert "thread_count" in result

    @pytest.mark.asyncio
    async def test_inspect_runtime(self):
        d = DiagnosticsEngine()
        result = await d.inspect_runtime()
        assert "uptime_seconds" in result
        assert "modules_loaded" in result

    @pytest.mark.asyncio
    async def test_inspect_threads(self):
        d = DiagnosticsEngine()
        result = await d.inspect_threads()
        assert "active_count" in result

    @pytest.mark.asyncio
    async def test_get_performance_report(self):
        d = DiagnosticsEngine()
        result = await d.get_performance_report()
        assert "uptime_seconds" in result

    @pytest.mark.asyncio
    async def test_get_execution_report(self):
        d = DiagnosticsEngine()
        result = await d.get_execution_report()
        assert "pid" in result

    def test_register_check(self):
        d = DiagnosticsEngine()
        d.register_check("test", lambda: "ok")
        assert "test" in d._custom_checks

    def test_unregister_check(self):
        d = DiagnosticsEngine()
        d.register_check("test", lambda: "ok")
        assert d.unregister_check("test") is True
        assert d.unregister_check("test") is False

    def test_to_dict(self):
        d = DiagnosticsEngine()
        result = d.to_dict()
        assert "uptime_seconds" in result
        assert "custom_checks" in result


# ======================================================================
# Alerts tests
# ======================================================================

class TestAlertManager:
    def test_create_rule(self):
        am = AlertManager()
        rule = am.create_rule(name="high_cpu", metric_name="cpu", condition="gt", threshold=90.0)
        assert rule.name == "high_cpu"
        assert am.rule_count == 1

    def test_delete_rule(self):
        am = AlertManager()
        rule = am.create_rule(name="test", metric_name="m")
        assert am.delete_rule(rule.rule_id) is True
        assert am.delete_rule("nonexistent") is False

    def test_get_rule(self):
        am = AlertManager()
        rule = am.create_rule(name="test", metric_name="m")
        found = am.get_rule(rule.rule_id)
        assert found is not None

    def test_list_rules(self):
        am = AlertManager()
        am.create_rule(name="r1", metric_name="m1")
        am.create_rule(name="r2", metric_name="m2")
        assert len(am.list_rules()) == 2

    def test_evaluate_triggers_alert(self):
        am = AlertManager()
        am.create_rule(name="high", metric_name="cpu", condition="gt", threshold=80.0, cooldown_seconds=0.0)
        alert = am.evaluate("cpu", 95.0)
        assert alert is not None
        assert alert.severity == AlertSeverity.WARNING
        assert am.alert_count == 1

    def test_evaluate_no_trigger(self):
        am = AlertManager()
        am.create_rule(name="high", metric_name="cpu", condition="gt", threshold=80.0)
        alert = am.evaluate("cpu", 50.0)
        assert alert is None

    def test_resolve_alert(self):
        am = AlertManager()
        am.create_rule(name="high", metric_name="cpu", condition="gt", threshold=80.0, cooldown_seconds=0.0)
        alert = am.evaluate("cpu", 95.0)
        assert am.resolve_alert(alert.alert_id) is True
        assert am.resolve_alert("nonexistent") is False

    def test_get_alerts(self):
        am = AlertManager()
        am.create_rule(name="high", metric_name="cpu", condition="gt", threshold=80.0, cooldown_seconds=0.0)
        am.evaluate("cpu", 95.0)
        alerts = am.get_alerts()
        assert len(alerts) == 1

    def test_get_alerts_by_state(self):
        am = AlertManager()
        am.create_rule(name="high", metric_name="cpu", condition="gt", threshold=80.0, cooldown_seconds=0.0)
        alert = am.evaluate("cpu", 95.0)
        am.resolve_alert(alert.alert_id)
        firing = am.get_alerts("firing")
        resolved = am.get_alerts("resolved")
        assert len(firing) == 0
        assert len(resolved) == 1

    def test_get_firing_alerts(self):
        am = AlertManager()
        am.create_rule(name="high", metric_name="cpu", condition="gt", threshold=80.0, cooldown_seconds=0.0)
        am.evaluate("cpu", 95.0)
        assert len(am.get_firing_alerts()) == 1

    def test_clear(self):
        am = AlertManager()
        am.create_rule(name="high", metric_name="cpu", condition="gt", threshold=80.0, cooldown_seconds=0.0)
        am.evaluate("cpu", 95.0)
        count = am.clear()
        assert count == 1
        assert am.alert_count == 0

    def test_to_dict(self):
        am = AlertManager()
        am.create_rule(name="r1", metric_name="m1")
        d = am.to_dict()
        assert "rules" in d
        assert "alerts" in d
        assert "rule_count" in d
        assert "alert_count" in d

    def test_cooldown_prevents_duplicate(self):
        am = AlertManager()
        am.create_rule(name="high", metric_name="cpu", condition="gt", threshold=80.0, cooldown_seconds=9999.0)
        alert1 = am.evaluate("cpu", 95.0)
        alert2 = am.evaluate("cpu", 95.0)
        assert alert1 is not None
        assert alert2 is None

    def test_disabled_rule(self):
        am = AlertManager()
        am.create_rule(name="disabled", metric_name="cpu", condition="gt", threshold=80.0, enabled=False)
        alert = am.evaluate("cpu", 95.0)
        assert alert is None

    def test_various_conditions(self):
        am = AlertManager()
        am.create_rule(name="lt", metric_name="mem", condition="lt", threshold=10.0, cooldown_seconds=0.0)
        alert = am.evaluate("mem", 5.0)
        assert alert is not None


# ======================================================================
# Profiler tests
# ======================================================================

class TestProfiler:
    def test_start_and_stop(self):
        p = Profiler()
        span = p.start("test", category="cpu")
        assert span.name == "test"
        p.stop(span)
        assert span.duration_ms >= 0.0
        assert p.span_count == 1

    def test_get_spans(self):
        p = Profiler()
        s1 = p.start("a", category="io")
        p.stop(s1)
        s2 = p.start("b", category="cpu")
        p.stop(s2)
        assert len(p.get_spans()) == 2

    def test_get_spans_by_category(self):
        p = Profiler()
        s1 = p.start("a", category="io")
        p.stop(s1)
        s2 = p.start("b", category="cpu")
        p.stop(s2)
        io_spans = p.get_spans(category="io")
        assert len(io_spans) == 1

    def test_get_slowest(self):
        p = Profiler()
        s1 = p.start("fast")
        time.sleep(0.001)
        p.stop(s1)
        s2 = p.start("slow")
        time.sleep(0.01)
        p.stop(s2)
        slowest = p.get_slowest(limit=1)
        assert len(slowest) == 1

    def test_get_by_category(self):
        p = Profiler()
        s1 = p.start("a", category="io")
        p.stop(s1)
        s2 = p.start("b", category="cpu")
        p.stop(s2)
        by_cat = p.get_by_category()
        assert "io" in by_cat
        assert "cpu" in by_cat

    def test_clear(self):
        p = Profiler()
        s = p.start("test")
        p.stop(s)
        count = p.clear()
        assert count == 1
        assert p.span_count == 0

    def test_to_dict(self):
        p = Profiler()
        s = p.start("test")
        p.stop(s)
        d = p.to_dict()
        assert "spans" in d
        assert "total" in d

    def test_profile_span_to_dict(self):
        s = ProfileSpan(name="test", category="cpu")
        d = s.to_dict()
        assert d["name"] == "test"
        assert d["category"] == "cpu"


# ======================================================================
# Monitor tests
# ======================================================================

class TestSystemMonitor:
    def test_get_system_info(self):
        m = SystemMonitor()
        info = m.get_system_info()
        assert "platform" in info
        assert "python_version" in info
        assert "pid" in info

    def test_get_process_info(self):
        m = SystemMonitor()
        info = m.get_process_info()
        assert "pid" in info
        assert "uptime_seconds" in info

    def test_get_memory_info(self):
        m = SystemMonitor()
        info = m.get_memory_info()
        assert "max_rss_kb" in info

    def test_get_thread_info(self):
        m = SystemMonitor()
        info = m.get_thread_info()
        assert "active_count" in info

    def test_to_dict(self):
        m = SystemMonitor()
        d = m.to_dict()
        assert "system" in d
        assert "process" in d


class TestApplicationMonitor:
    def test_record_request(self):
        m = ApplicationMonitor()
        m.record_request()
        m.record_request()
        assert m.request_count == 2

    def test_record_response(self):
        m = ApplicationMonitor()
        m.record_response(10.0)
        m.record_response(20.0)
        assert m.response_count == 2
        assert m.average_latency_ms == 15.0

    def test_record_error(self):
        m = ApplicationMonitor()
        m.record_error()
        assert m.error_count == 1

    def test_average_latency_empty(self):
        m = ApplicationMonitor()
        assert m.average_latency_ms == 0.0

    def test_to_dict(self):
        m = ApplicationMonitor()
        m.record_request()
        m.record_response(5.0)
        d = m.to_dict()
        assert d["request_count"] == 1

    def test_reset(self):
        m = ApplicationMonitor()
        m.record_request()
        m.record_response(5.0)
        m.record_error()
        m.reset()
        assert m.request_count == 0
        assert m.response_count == 0
        assert m.error_count == 0


# ======================================================================
# Events tests
# ======================================================================

class TestObservabilityEvent:
    def test_creation(self):
        e = ObservabilityEvent(event_type="lifecycle", source="test", data={"key": "val"})
        assert e.event_type == "lifecycle"
        assert e.source == "test"
        assert e.data == {"key": "val"}

    def test_to_dict(self):
        e = ObservabilityEvent(event_type="lifecycle", source="test", data={"k": "v"})
        d = e.to_dict()
        assert d["event_type"] == "lifecycle"
        assert d["data"]["k"] == "v"


class TestObservabilityEventBus:
    def test_publish(self):
        bus = ObservabilityEventBus()
        event = bus.publish("lifecycle", "test", {"state": "running"})
        assert event.event_type == "lifecycle"
        assert bus.event_count == 1

    def test_subscribe_and_publish(self):
        bus = ObservabilityEventBus()
        received = []
        bus.subscribe("lifecycle", lambda e: received.append(e))
        bus.publish("lifecycle", "test")
        assert len(received) == 1

    def test_unsubscribe(self):
        bus = ObservabilityEventBus()
        handler = lambda e: None
        bus.subscribe("lifecycle", handler)
        assert bus.unsubscribe("lifecycle", handler) is True
        assert bus.unsubscribe("lifecycle", handler) is False

    def test_get_events(self):
        bus = ObservabilityEventBus()
        bus.publish("a", "test")
        bus.publish("b", "test")
        events = bus.get_events()
        assert len(events) == 2

    def test_get_events_by_type(self):
        bus = ObservabilityEventBus()
        bus.publish("a", "test")
        bus.publish("b", "test")
        bus.publish("a", "test")
        events = bus.get_events(event_type="a")
        assert len(events) == 2

    def test_clear(self):
        bus = ObservabilityEventBus()
        bus.publish("a", "test")
        count = bus.clear()
        assert count == 1
        assert bus.event_count == 0

    def test_to_dict(self):
        bus = ObservabilityEventBus()
        bus.publish("a", "test")
        d = bus.to_dict()
        assert "events" in d
        assert "total" in d

    def test_max_events_eviction(self):
        bus = ObservabilityEventBus(max_events=2)
        bus.publish("a", "test")
        bus.publish("b", "test")
        bus.publish("c", "test")
        assert bus.event_count == 2

    def test_handler_exception_does_not_propagate(self):
        bus = ObservabilityEventBus()
        def bad_handler(e):
            raise ValueError("oops")
        bus.subscribe("test", bad_handler)
        event = bus.publish("test", "src")
        assert event is not None


# ======================================================================
# Collectors tests
# ======================================================================

class TestBaseCollector:
    def test_collect(self):
        c = BaseCollector(CollectorType.SYSTEM, "test")
        result = c.collect()
        assert result["collector"] == "test"
        assert result["type"] == "system"


class TestSystemCollector:
    def test_collect(self):
        c = SystemCollector()
        result = c.collect()
        assert "pid" in result
        assert "thread_count" in result
        assert "platform" in result


class TestApplicationCollector:
    def test_collect(self):
        c = ApplicationCollector()
        c.record_request()
        c.record_response(10.0)
        c.record_error()
        result = c.collect()
        assert result["request_count"] == 1
        assert result["response_count"] == 1
        assert result["error_count"] == 1


class TestAICollector:
    def test_collect(self):
        c = AICollector()
        c.record_prompt(tokens=100, latency_ms=5.0)
        c.record_completion(tokens=200, latency_ms=10.0)
        result = c.collect()
        assert result["prompt_count"] == 1
        assert result["completion_count"] == 1
        assert result["total_tokens"] == 300


class TestMemoryCollector:
    def test_collect(self):
        c = MemoryCollector()
        c.record_cache_hit()
        c.record_cache_miss()
        c.record_conversation()
        c.record_vector()
        result = c.collect()
        assert result["cache_hits"] == 1
        assert result["cache_misses"] == 1


class TestExecutionCollector:
    def test_collect(self):
        c = ExecutionCollector()
        c.record("goals")
        c.record("goals")
        c.record("tasks")
        result = c.collect()
        assert result["goals"] == 2
        assert result["tasks"] == 1


class TestCollectorRegistry:
    def test_register_and_list(self):
        reg = CollectorRegistry()
        reg.register(SystemCollector())
        assert "system" in reg.list_collectors()

    def test_unregister(self):
        reg = CollectorRegistry()
        reg.register(SystemCollector())
        assert reg.unregister("system") is True
        assert reg.unregister("system") is False

    def test_get(self):
        reg = CollectorRegistry()
        reg.register(AICollector())
        ai = reg.get("ai")
        assert ai is not None
        assert reg.get("nonexistent") is None

    def test_collect_all(self):
        reg = CollectorRegistry()
        reg.register(SystemCollector())
        reg.register(AICollector())
        results = reg.collect_all()
        assert len(results) == 2

    def test_clear(self):
        reg = CollectorRegistry()
        reg.register(SystemCollector())
        count = reg.clear()
        assert count == 1

    def test_to_dict(self):
        reg = CollectorRegistry()
        reg.register(SystemCollector())
        d = reg.to_dict()
        assert "system" in d["collectors"]


# ======================================================================
# Exporters tests
# ======================================================================

class TestPrometheusExporter:
    def test_export(self):
        e = PrometheusExporter()
        metrics = [{"name": "req", "value": 10.0, "type": "counter", "labels": {"env": "prod"}}]
        result = e.export(metrics)
        assert "req" in result
        assert "10.0" in result
        assert "# HELP" in result

    def test_export_empty(self):
        e = PrometheusExporter()
        result = e.export([])
        assert result == ""


class TestJSONExporter:
    def test_export_metrics(self):
        e = JSONExporter()
        result = e.export_metrics([{"name": "req", "value": 10.0}])
        assert "req" in result

    def test_export_traces(self):
        e = JSONExporter()
        result = e.export_traces([{"name": "span1"}])
        assert "span1" in result


class TestCSVExporter:
    def test_export(self):
        e = CSVExporter()
        result = e.export([{"name": "req", "type": "counter", "value": 10.0, "timestamp": 1.0}])
        assert "req" in result
        assert "counter" in result

    def test_export_empty(self):
        e = CSVExporter()
        result = e.export([])
        assert result == ""


class TestOpenTelemetryExporter:
    def test_export(self):
        e = OpenTelemetryExporter()
        traces = [{"trace_id": "t1", "span_id": "s1", "name": "test", "start_time": 1.0, "end_time": 2.0, "status": "ok"}]
        result = e.export(traces)
        assert "resourceSpans" in result


class TestExportManager:
    def test_export_metrics_json(self):
        m = ExportManager()
        result = m.export_metrics([{"name": "x", "value": 1.0}], "json")
        assert "x" in result

    def test_export_metrics_prometheus(self):
        m = ExportManager()
        result = m.export_metrics([{"name": "x", "value": 1.0, "type": "counter"}], "prometheus")
        assert "# HELP" in result

    def test_export_metrics_csv(self):
        m = ExportManager()
        result = m.export_metrics([{"name": "x", "value": 1.0, "type": "counter", "timestamp": 0.0}], "csv")
        assert "x" in result

    def test_export_traces_json(self):
        m = ExportManager()
        result = m.export_traces([{"name": "s"}], "json")
        assert "s" in result

    def test_export_traces_opentelemetry(self):
        m = ExportManager()
        result = m.export_traces(
            [{"trace_id": "t1", "span_id": "s1", "name": "test", "start_time": 1.0, "end_time": 2.0, "status": "ok"}],
            "opentelemetry",
        )
        assert "resourceSpans" in result


# ======================================================================
# Repository tests
# ======================================================================

class TestInMemoryObservabilityRepository:
    @pytest.mark.asyncio
    async def test_store_and_get_alert(self):
        repo = InMemoryObservabilityRepository()
        alert = Alert(alert_id="a1", name="test")
        await repo.store_alert(alert)
        found = await repo.get_alert("a1")
        assert found is not None

    @pytest.mark.asyncio
    async def test_list_alerts(self):
        repo = InMemoryObservabilityRepository()
        await repo.store_alert(Alert(alert_id="a1", name="a"))
        await repo.store_alert(Alert(alert_id="a2", name="b"))
        alerts = await repo.list_alerts()
        assert len(alerts) == 2

    @pytest.mark.asyncio
    async def test_delete_alert(self):
        repo = InMemoryObservabilityRepository()
        await repo.store_alert(Alert(alert_id="a1"))
        assert await repo.delete_alert("a1") is True
        assert await repo.delete_alert("a1") is False

    @pytest.mark.asyncio
    async def test_store_and_get_rule(self):
        repo = InMemoryObservabilityRepository()
        rule = AlertRule(rule_id="r1", name="test")
        await repo.store_rule(rule)
        found = await repo.get_rule("r1")
        assert found is not None

    @pytest.mark.asyncio
    async def test_list_rules(self):
        repo = InMemoryObservabilityRepository()
        await repo.store_rule(AlertRule(rule_id="r1"))
        await repo.store_rule(AlertRule(rule_id="r2"))
        rules = await repo.list_rules()
        assert len(rules) == 2

    @pytest.mark.asyncio
    async def test_delete_rule(self):
        repo = InMemoryObservabilityRepository()
        await repo.store_rule(AlertRule(rule_id="r1"))
        assert await repo.delete_rule("r1") is True

    @pytest.mark.asyncio
    async def test_store_and_get_log(self):
        repo = InMemoryObservabilityRepository()
        log = LogEntry(entry_id="l1", message="test")
        await repo.store_log(log)
        found = await repo.get_log("l1")
        assert found is not None

    @pytest.mark.asyncio
    async def test_list_logs(self):
        repo = InMemoryObservabilityRepository()
        await repo.store_log(LogEntry(entry_id="l1"))
        await repo.store_log(LogEntry(entry_id="l2"))
        logs = await repo.list_logs()
        assert len(logs) == 2

    @pytest.mark.asyncio
    async def test_count_logs(self):
        repo = InMemoryObservabilityRepository()
        await repo.store_log(LogEntry(entry_id="l1"))
        assert await repo.count_logs() == 1

    @pytest.mark.asyncio
    async def test_store_and_get_span(self):
        repo = InMemoryObservabilityRepository()
        span = TraceSpan(span_id="s1", name="test")
        await repo.store_span(span)
        found = await repo.get_span("s1")
        assert found is not None

    @pytest.mark.asyncio
    async def test_list_spans(self):
        repo = InMemoryObservabilityRepository()
        await repo.store_span(TraceSpan(span_id="s1"))
        spans = await repo.list_spans()
        assert len(spans) == 1

    @pytest.mark.asyncio
    async def test_count_spans(self):
        repo = InMemoryObservabilityRepository()
        await repo.store_span(TraceSpan(span_id="s1"))
        assert await repo.count_spans() == 1

    @pytest.mark.asyncio
    async def test_clear(self):
        repo = InMemoryObservabilityRepository()
        await repo.store_alert(Alert(alert_id="a1"))
        await repo.store_rule(AlertRule(rule_id="r1"))
        count = await repo.clear()
        assert count == 2

    @pytest.mark.asyncio
    async def test_count_alerts(self):
        repo = InMemoryObservabilityRepository()
        await repo.store_alert(Alert(alert_id="a1"))
        assert await repo.count_alerts() == 1

    @pytest.mark.asyncio
    async def test_count_rules(self):
        repo = InMemoryObservabilityRepository()
        await repo.store_rule(AlertRule(rule_id="r1"))
        assert await repo.count_rules() == 1


# ======================================================================
# Persistence tests
# ======================================================================

class TestInMemoryObservabilityPersistence:
    @pytest.mark.asyncio
    async def test_store_and_get_counter(self):
        p = InMemoryObservabilityPersistence()
        await p.store_counter("req", 5.0)
        assert await p.get_counter("req") == 5.0

    @pytest.mark.asyncio
    async def test_store_counter_accumulates(self):
        p = InMemoryObservabilityPersistence()
        await p.store_counter("req", 3.0)
        await p.store_counter("req", 2.0)
        assert await p.get_counter("req") == 5.0

    @pytest.mark.asyncio
    async def test_set_and_get_gauge(self):
        p = InMemoryObservabilityPersistence()
        await p.set_gauge("temp", 25.5)
        assert await p.get_gauge("temp") == 25.5

    @pytest.mark.asyncio
    async def test_store_and_get_config(self):
        p = InMemoryObservabilityPersistence()
        await p.store_config("key1", "value1")
        assert await p.get_config("key1") == "value1"

    @pytest.mark.asyncio
    async def test_delete_config(self):
        p = InMemoryObservabilityPersistence()
        await p.store_config("key1", "value1")
        assert await p.delete_config("key1") is True
        assert await p.delete_config("key1") is False

    @pytest.mark.asyncio
    async def test_store_and_get_state(self):
        p = InMemoryObservabilityPersistence()
        await p.store_state("s1", {"data": 1})
        assert await p.get_state("s1") == {"data": 1}

    @pytest.mark.asyncio
    async def test_list_counters(self):
        p = InMemoryObservabilityPersistence()
        await p.store_counter("a", 1.0)
        counters = await p.list_counters()
        assert counters["a"] == 1.0

    @pytest.mark.asyncio
    async def test_list_gauges(self):
        p = InMemoryObservabilityPersistence()
        await p.set_gauge("g", 2.0)
        gauges = await p.list_gauges()
        assert gauges["g"] == 2.0

    @pytest.mark.asyncio
    async def test_clear(self):
        p = InMemoryObservabilityPersistence()
        await p.store_counter("a", 1.0)
        await p.set_gauge("b", 2.0)
        count = await p.clear()
        assert count == 2


# ======================================================================
# Manager tests
# ======================================================================

class TestObservabilityManager:
    def test_default_construction(self):
        m = ObservabilityManager()
        assert m.metrics is not None
        assert m.tracer is not None
        assert m.logger is not None
        assert m.health is not None
        assert m.diagnostics is not None
        assert m.alerts is not None
        assert m.profiler is not None
        assert m.event_bus is not None
        assert m.export_manager is not None
        assert m.collector_registry is not None
        assert m.system_monitor is not None
        assert m.app_monitor is not None

    def test_record_counter(self):
        m = ObservabilityManager()
        m.record_counter("test_counter", 1.0)
        assert m.metrics.get_counter("test_counter") == 1.0

    def test_record_gauge(self):
        m = ObservabilityManager()
        m.record_gauge("test_gauge", 42.0)
        assert m.metrics.get_gauge("test_gauge") == 42.0

    def test_record_histogram(self):
        m = ObservabilityManager()
        m.record_histogram("test_hist", 10.0)
        assert m.metrics.get_histogram("test_hist") == [10.0]

    def test_log(self):
        m = ObservabilityManager()
        m.log("info", "test message")
        assert m.logger.entry_count == 1

    @pytest.mark.asyncio
    async def test_get_readiness(self):
        m = ObservabilityManager()
        result = await m.get_readiness()
        assert "ready" in result

    @pytest.mark.asyncio
    async def test_get_liveness(self):
        m = ObservabilityManager()
        result = await m.get_liveness()
        assert "alive" in result

    @pytest.mark.asyncio
    async def test_get_startup(self):
        m = ObservabilityManager()
        result = await m.get_startup()
        assert "started" in result

    @pytest.mark.asyncio
    async def test_get_diagnostics(self):
        m = ObservabilityManager()
        result = await m.get_diagnostics()
        assert "dependencies" in result
        assert "configuration" in result
        assert "runtime" in result

    @pytest.mark.asyncio
    async def test_get_performance_report(self):
        m = ObservabilityManager()
        result = await m.get_performance_report()
        assert "uptime_seconds" in result

    def test_get_metrics_dict(self):
        m = ObservabilityManager()
        m.record_counter("x", 1.0)
        d = m.get_metrics_dict()
        assert "counters" in d

    def test_get_traces_dict(self):
        m = ObservabilityManager()
        s = m.tracer.start_span("test")
        m.tracer.end_span(s)
        d = m.get_traces_dict()
        assert "traces" in d

    def test_get_logs_dict(self):
        m = ObservabilityManager()
        m.log("info", "test")
        d = m.get_logs_dict()
        assert "logs" in d

    def test_get_alerts_dict(self):
        m = ObservabilityManager()
        d = m.get_alerts_dict()
        assert "rules" in d
        assert "alerts" in d

    def test_get_statistics(self):
        m = ObservabilityManager()
        stats = m.get_statistics()
        assert "total_metrics" in stats
        assert "total_spans" in stats
        assert "total_logs" in stats
        assert "total_alerts" in stats
        assert "total_rules" in stats
        assert "uptime_seconds" in stats

    def test_export_metrics_json(self):
        m = ObservabilityManager()
        m.record_counter("x", 1.0)
        result = m.export_metrics("json")
        assert isinstance(result, str)

    def test_export_traces_json(self):
        m = ObservabilityManager()
        result = m.export_traces("json")
        assert isinstance(result, str)


# ======================================================================
# Engine tests
# ======================================================================

class TestObservabilityEngine:
    def test_default_construction(self):
        e = ObservabilityEngine()
        assert e.lifecycle is not None
        assert e.manager is not None
        assert e.repository is not None
        assert e.lifecycle.state == ObservabilityLifecycleState.INITIALIZED

    @pytest.mark.asyncio
    async def test_start_and_shutdown(self):
        e = ObservabilityEngine()
        await e.start()
        assert e.lifecycle.state == ObservabilityLifecycleState.RUNNING
        await e.shutdown()
        assert e.lifecycle.state == ObservabilityLifecycleState.SHUTDOWN

    def test_record_counter(self):
        e = ObservabilityEngine()
        e.record_counter("req", 1.0)
        assert e.manager.metrics.get_counter("req") == 1.0

    def test_record_gauge(self):
        e = ObservabilityEngine()
        e.record_gauge("temp", 25.0)
        assert e.manager.metrics.get_gauge("temp") == 25.0

    def test_record_histogram(self):
        e = ObservabilityEngine()
        e.record_histogram("lat", 10.0)
        assert e.manager.metrics.get_histogram("lat") == [10.0]

    def test_start_and_end_span(self):
        e = ObservabilityEngine()
        span = e.start_span("test")
        assert span is not None
        e.end_span(span)
        assert span.duration_ms >= 0.0

    def test_log(self):
        e = ObservabilityEngine()
        e.log("info", "test message")
        assert e.manager.logger.entry_count == 1

    @pytest.mark.asyncio
    async def test_check_health(self):
        e = ObservabilityEngine()
        await e.start()
        result = await e.check_health()
        assert "status" in result
        assert "uptime_seconds" in result

    @pytest.mark.asyncio
    async def test_check_readiness(self):
        e = ObservabilityEngine()
        await e.start()
        result = await e.check_readiness()
        assert "ready" in result

    @pytest.mark.asyncio
    async def test_check_liveness(self):
        e = ObservabilityEngine()
        await e.start()
        result = await e.check_liveness()
        assert "alive" in result

    @pytest.mark.asyncio
    async def test_get_diagnostics(self):
        e = ObservabilityEngine()
        result = await e.get_diagnostics()
        assert "dependencies" in result

    @pytest.mark.asyncio
    async def test_get_performance_report(self):
        e = ObservabilityEngine()
        result = await e.get_performance_report()
        assert "uptime_seconds" in result

    def test_create_alert_rule(self):
        e = ObservabilityEngine()
        rule = e.create_alert_rule(
            name="high_cpu", metric_name="cpu", condition="gt",
            threshold=90.0, severity="warning",
        )
        assert rule.name == "high_cpu"

    def test_evaluate_alerts(self):
        e = ObservabilityEngine()
        e.create_alert_rule(name="high", metric_name="cpu", condition="gt", threshold=80.0, severity="critical")
        alert = e.evaluate_alerts("cpu", 95.0)
        assert alert is not None

    def test_get_alerts(self):
        e = ObservabilityEngine()
        alerts = e.get_alerts()
        assert isinstance(alerts, list)

    def test_get_alert_rules(self):
        e = ObservabilityEngine()
        e.create_alert_rule(name="r1", metric_name="m1")
        rules = e.get_alert_rules()
        assert len(rules) == 1

    def test_export_metrics(self):
        e = ObservabilityEngine()
        e.record_counter("x", 1.0)
        result = e.export_metrics("json")
        assert isinstance(result, str)

    def test_export_traces(self):
        e = ObservabilityEngine()
        result = e.export_traces("json")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_metrics(self):
        e = ObservabilityEngine()
        e.record_counter("x", 1.0)
        result = await e.get_metrics()
        assert "counters" in result

    @pytest.mark.asyncio
    async def test_get_traces(self):
        e = ObservabilityEngine()
        s = e.start_span("test")
        e.end_span(s)
        result = await e.get_traces()
        assert "traces" in result

    @pytest.mark.asyncio
    async def test_get_logs(self):
        e = ObservabilityEngine()
        e.log("info", "test")
        result = await e.get_logs()
        assert "logs" in result

    @pytest.mark.asyncio
    async def test_get_statistics(self):
        e = ObservabilityEngine()
        result = await e.get_statistics()
        assert "total_metrics" in result
        assert "lifecycle_state" in result

    def test_get_metrics_dict(self):
        e = ObservabilityEngine()
        d = e.get_metrics_dict()
        assert "counters" in d

    def test_get_traces_dict(self):
        e = ObservabilityEngine()
        d = e.get_traces_dict()
        assert "traces" in d

    def test_get_logs_dict(self):
        e = ObservabilityEngine()
        d = e.get_logs_dict()
        assert "logs" in d

    def test_get_statistics_dict(self):
        e = ObservabilityEngine()
        d = e.get_statistics_dict()
        assert "total_metrics" in d


# ======================================================================
# Factory tests
# ======================================================================

class TestObservabilityFactory:
    def test_create_engine(self):
        engine = ObservabilityFactory.create_engine()
        assert isinstance(engine, ObservabilityEngine)

    def test_create_engine_with_components(self):
        components = ObservabilityFactory.create_engine_with_components()
        assert "engine" in components
        assert "manager" in components
        assert "lifecycle" in components
        assert "repository" in components
        assert "metrics" in components
        assert "tracer" in components
        assert "logger" in components
        assert "health" in components
        assert "diagnostics" in components
        assert "alerts" in components
        assert "profiler" in components
        assert "event_bus" in components


# ======================================================================
# Pydantic schema tests
# ======================================================================

class TestSchemas:
    def test_health_response(self):
        r = HealthResponse(status="ok", lifecycle_state="running", uptime_seconds=10.0)
        assert r.status == "ok"

    def test_readiness_response(self):
        r = ReadinessResponse(status="ok", ready=True)
        assert r.ready is True

    def test_liveness_response(self):
        r = LivenessResponse(status="ok", alive=True, uptime_seconds=5.0)
        assert r.alive is True

    def test_metrics_response(self):
        r = MetricsResponse(metrics=[], total=0)
        assert r.total == 0

    def test_traces_response(self):
        r = TracesResponse(traces=[], total=0)
        assert r.total == 0

    def test_logs_response(self):
        r = LogsResponse(logs=[], total=0)
        assert r.total == 0

    def test_diagnostics_response(self):
        r = DiagnosticsResponse(dependencies={}, configuration={}, runtime={})
        assert r.dependencies == {}

    def test_alerts_response(self):
        r = AlertsResponse(alerts=[], rules=[], total_alerts=0)
        assert r.total_alerts == 0

    def test_statistics_response(self):
        r = StatisticsResponse(total_metrics=0, total_spans=0, total_logs=0)
        assert r.total_metrics == 0

    def test_prometheus_response(self):
        r = PrometheusResponse(content="# HELP x x")
        assert "x" in r.content

    def test_json_export_response(self):
        r = JSONExportResponse(data={"metrics": []})
        assert "metrics" in r.data

    def test_csv_export_response(self):
        r = CSVExportResponse(content="name,value\nx,1")
        assert "name" in r.content
