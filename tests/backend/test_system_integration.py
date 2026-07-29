"""Tests for Chapter 32 — System Integration."""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.v1.router import router as api_router
from app.integration.base import (
    CompatibilityProvider,
    DependencyGraphProvider,
    DiagnosticsProvider,
    IntegrationCoordinator,
    IntegrationProvider,
)
from app.integration.compatibility import CompatibilityChecker, CompatibilityReport
from app.integration.coordinator import IntegrationCoordinator, SystemCoordinator
from app.integration.dependency_graph import DependencyGraph, DependencyInfo, DependencyNode
from app.integration.diagnostics import SystemDiagnostics
from app.integration.engine import IntegrationEngine
from app.integration.enums import (
    CompatibilityLevel,
    ComponentState,
    DependencyType,
    HealthStatus,
    IntegrationState,
    ValidationSeverity,
)
from app.integration.factory import IntegrationFactory
from app.integration.health import HealthAggregator, SystemHealth, SystemHealthStatus
from app.integration.lifecycle import IntegrationLifecycle
from app.integration.metrics import IntegrationMetrics, IntegrationMetricsCollector
from app.integration.orchestrator import SystemOrchestrator
from app.integration.registry import ComponentInfo, ComponentState as RegComponentState, IntegrationRegistry
from app.integration.schemas import (
    CompatibilityResponse,
    ComponentRegistrationRequest,
    DependencyGraphResponse,
    DiagnosticsResponse,
    HealthCheckResponse,
    IntegrationMetricsResponse,
    IntegrationStatusResponse,
    ReinitializeRequest,
    TracesResponse,
    ValidationRequest,
    ValidationResponse,
)
from app.integration.tracing import IntegrationTracer
from app.integration.validation import IntegrationValidator, ValidationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class StubComponent:
    def __init__(self, name: str = "stub", fail_start: bool = False, fail_shutdown: bool = False) -> None:
        self.name = name
        self.fail_start = fail_start
        self.fail_shutdown = fail_shutdown
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        if self.fail_start:
            raise RuntimeError(f"{self.name} start failed")
        self.started = True

    async def shutdown(self) -> None:
        if self.fail_shutdown:
            raise RuntimeError(f"{self.name} shutdown failed")
        self.stopped = True

    def health(self) -> dict[str, Any]:
        return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestEnums:
    def test_integration_state_values(self) -> None:
        assert IntegrationState.REGISTERED.value == "registered"
        assert IntegrationState.RUNNING.value == "running"
        assert IntegrationState.SHUTDOWN.value == "shutdown"

    def test_component_state_values(self) -> None:
        assert ComponentState.REGISTERED.value == "registered"
        assert ComponentState.READY.value == "ready"
        assert ComponentState.FAILED.value == "failed"

    def test_health_status_values(self) -> None:
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"

    def test_dependency_type_values(self) -> None:
        assert DependencyType.REQUIRED.value == "required"
        assert DependencyType.OPTIONAL.value == "optional"
        assert DependencyType.SOFT.value == "soft"

    def test_validation_severity_values(self) -> None:
        assert ValidationSeverity.INFO.value == "info"
        assert ValidationSeverity.CRITICAL.value == "critical"

    def test_compatibility_level_values(self) -> None:
        assert CompatibilityLevel.COMPATIBLE.value == "compatible"
        assert CompatibilityLevel.INCOMPATIBLE.value == "incompatible"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestIntegrationRegistry:
    def test_register_component(self) -> None:
        reg = IntegrationRegistry()
        info = reg.register("comp_a", object(), component_type="engine", version="1.0.0")
        assert info.name == "comp_a"
        assert info.component_type == "engine"
        assert info.version == "1.0.0"

    def test_unregister_component(self) -> None:
        reg = IntegrationRegistry()
        reg.register("comp_a", object())
        assert reg.unregister("comp_a") is True
        assert reg.get("comp_a") is None

    def test_unregister_nonexistent(self) -> None:
        reg = IntegrationRegistry()
        assert reg.unregister("nope") is False

    def test_get_component(self) -> None:
        reg = IntegrationRegistry()
        obj = object()
        reg.register("comp_a", obj)
        assert reg.get_component("comp_a") is obj

    def test_get_nonexistent(self) -> None:
        reg = IntegrationRegistry()
        assert reg.get("nope") is None
        assert reg.get_component("nope") is None

    def test_list_all(self) -> None:
        reg = IntegrationRegistry()
        reg.register("a", object())
        reg.register("b", object())
        assert len(reg.list_all()) == 2

    def test_list_by_type(self) -> None:
        reg = IntegrationRegistry()
        reg.register("a", object(), component_type="engine")
        reg.register("b", object(), component_type="provider")
        engines = reg.list_by_type("engine")
        assert len(engines) == 1
        assert engines[0].name == "a"

    def test_list_by_state(self) -> None:
        reg = IntegrationRegistry()
        info = reg.register("a", object())
        info.state = ComponentState.RUNNING
        running = reg.list_by_state(ComponentState.RUNNING)
        assert len(running) == 1

    def test_update_state(self) -> None:
        reg = IntegrationRegistry()
        reg.register("a", object())
        assert reg.update_state("a", ComponentState.RUNNING) is True
        assert reg.get("a").state == ComponentState.RUNNING

    def test_update_state_with_error(self) -> None:
        reg = IntegrationRegistry()
        reg.register("a", object())
        reg.update_state("a", ComponentState.FAILED, "boom")
        assert reg.get("a").error == "boom"

    def test_update_nonexistent(self) -> None:
        reg = IntegrationRegistry()
        assert reg.update_state("nope", ComponentState.READY) is False

    def test_count(self) -> None:
        reg = IntegrationRegistry()
        assert reg.count() == 0
        reg.register("a", object())
        assert reg.count() == 1

    def test_clear(self) -> None:
        reg = IntegrationRegistry()
        reg.register("a", object())
        reg.clear()
        assert reg.count() == 0

    def test_to_dict(self) -> None:
        reg = IntegrationRegistry()
        info = reg.register("a", object(), component_type="engine")
        d = info.to_dict()
        assert d["name"] == "a"
        assert d["component_type"] == "engine"
        assert "state" in d

    def test_concurrent_register(self) -> None:
        reg = IntegrationRegistry()
        errors: list[Exception] = []

        def register_many(prefix: str) -> None:
            try:
                for i in range(50):
                    reg.register(f"{prefix}_{i}", object())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=register_many, args=(f"t{t}",)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert reg.count() == 200


# ---------------------------------------------------------------------------
# Dependency Graph
# ---------------------------------------------------------------------------


class TestDependencyGraph:
    def test_add_node(self) -> None:
        g = DependencyGraph()
        g.add_node("a")
        assert g.node_count() == 1

    def test_add_duplicate_node(self) -> None:
        g = DependencyGraph()
        g.add_node("a")
        g.add_node("a")
        assert g.node_count() == 1

    def test_remove_node(self) -> None:
        g = DependencyGraph()
        g.add_node("a")
        g.add_node("b")
        g.add_dependency("a", "b")
        g.remove_node("a")
        assert g.node_count() == 1
        assert g.edge_count() == 0

    def test_add_dependency(self) -> None:
        g = DependencyGraph()
        g.add_dependency("a", "b")
        assert g.edge_count() == 1
        deps = g.get_dependencies("a")
        assert "b" in deps["required"]

    def test_add_duplicate_dependency(self) -> None:
        g = DependencyGraph()
        g.add_dependency("a", "b")
        g.add_dependency("a", "b")
        assert g.edge_count() == 1

    def test_remove_dependency(self) -> None:
        g = DependencyGraph()
        g.add_dependency("a", "b")
        g.remove_dependency("a", "b")
        assert g.edge_count() == 0

    def test_get_direct_dependencies(self) -> None:
        g = DependencyGraph()
        g.add_dependency("a", "b")
        g.add_dependency("a", "c")
        deps = g.get_direct_dependencies("a")
        assert "b" in deps
        assert "c" in deps

    def test_get_direct_dependents(self) -> None:
        g = DependencyGraph()
        g.add_dependency("a", "b")
        g.add_dependency("c", "b")
        deps = g.get_direct_dependents("b")
        assert "a" in deps
        assert "c" in deps

    def test_detect_cycles_none(self) -> None:
        g = DependencyGraph()
        g.add_dependency("a", "b")
        g.add_dependency("b", "c")
        cycles = g.detect_cycles()
        assert len(cycles) == 0

    def test_detect_cycles_found(self) -> None:
        g = DependencyGraph()
        g.add_dependency("a", "b")
        g.add_dependency("b", "c")
        g.add_dependency("c", "a")
        cycles = g.detect_cycles()
        assert len(cycles) > 0

    def test_topological_sort(self) -> None:
        g = DependencyGraph()
        g.add_dependency("a", "b")
        g.add_dependency("b", "c")
        order = g.topological_sort()
        assert order.index("c") < order.index("b")
        assert order.index("b") < order.index("a")

    def test_topological_sort_with_cycle(self) -> None:
        g = DependencyGraph()
        g.add_dependency("a", "b")
        g.add_dependency("b", "a")
        order = g.topological_sort()
        # Nodes in a cycle cannot be topologically sorted — they are omitted
        assert len(order) <= 2

    def test_get_all_nodes(self) -> None:
        g = DependencyGraph()
        g.add_node("a")
        g.add_node("b")
        nodes = g.get_all_nodes()
        assert len(nodes) == 2

    def test_get_all_edges(self) -> None:
        g = DependencyGraph()
        g.add_dependency("a", "b")
        g.add_dependency("c", "d")
        edges = g.get_all_edges()
        assert len(edges) == 2

    def test_to_dict(self) -> None:
        g = DependencyGraph()
        g.add_dependency("a", "b")
        d = g.to_dict()
        assert "nodes" in d
        assert "edges" in d
        assert d["node_count"] == 2
        assert d["edge_count"] == 1

    def test_node_metadata(self) -> None:
        node = DependencyNode("test", "engine", {"key": "value"})
        d = node.to_dict()
        assert d["name"] == "test"
        assert d["component_type"] == "engine"

    def test_dependency_info(self) -> None:
        info = DependencyInfo("a", "b", DependencyType.OPTIONAL)
        d = info.to_dict()
        assert d["source"] == "a"
        assert d["type"] == "optional"

    def test_optional_dependency(self) -> None:
        g = DependencyGraph()
        g.add_dependency("a", "b", "optional")
        deps = g.get_dependencies("a")
        assert "b" in deps["optional"]

    def test_soft_dependency(self) -> None:
        g = DependencyGraph()
        g.add_dependency("a", "b", "soft")
        deps = g.get_dependencies("a")
        assert "b" in deps["soft"]


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestIntegrationLifecycle:
    def test_initial_state(self) -> None:
        lc = IntegrationLifecycle()
        assert lc.state == IntegrationState.REGISTERED

    def test_valid_transitions(self) -> None:
        lc = IntegrationLifecycle()
        assert lc.transition(IntegrationState.DISCOVERING, "start") is True
        assert lc.transition(IntegrationState.VALIDATED, "validated") is True
        assert lc.transition(IntegrationState.INITIALIZING, "init") is True
        assert lc.transition(IntegrationState.READY, "ready") is True
        assert lc.transition(IntegrationState.RUNNING, "run") is True
        assert lc.state == IntegrationState.RUNNING

    def test_invalid_transition(self) -> None:
        lc = IntegrationLifecycle()
        assert lc.transition(IntegrationState.RUNNING, "skip") is False

    def test_history(self) -> None:
        lc = IntegrationLifecycle()
        lc.transition(IntegrationState.DISCOVERING, "start")
        lc.transition(IntegrationState.VALIDATED, "validated")
        history = lc.get_history()
        assert len(history) == 2

    def test_status(self) -> None:
        lc = IntegrationLifecycle()
        status = lc.get_status()
        assert status["state"] == "registered"
        assert "uptime_seconds" in status

    def test_is_running(self) -> None:
        lc = IntegrationLifecycle()
        assert lc.is_running() is False

    def test_reset(self) -> None:
        lc = IntegrationLifecycle()
        lc.transition(IntegrationState.DISCOVERING, "start")
        lc.reset()
        assert lc.state == IntegrationState.REGISTERED

    def test_shutdown_path(self) -> None:
        lc = IntegrationLifecycle()
        lc.transition(IntegrationState.DISCOVERING, "d")
        lc.transition(IntegrationState.VALIDATED, "v")
        lc.transition(IntegrationState.INITIALIZING, "i")
        lc.transition(IntegrationState.READY, "r")
        lc.transition(IntegrationState.RUNNING, "run")
        lc.transition(IntegrationState.SHUTTING_DOWN, "shutting")
        lc.transition(IntegrationState.SHUTDOWN, "off")
        assert lc.state == IntegrationState.SHUTDOWN


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestIntegrationValidator:
    def _make_validator(self, components: dict[str, list[str]] | None = None) -> tuple[IntegrationValidator, IntegrationRegistry, DependencyGraph]:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        comps = components or {"a": [], "b": ["a"], "c": ["a", "b"]}
        for name, deps in comps.items():
            comp = StubComponent(name)
            reg.register(name, comp, component_type="service", dependencies=deps)
            graph.add_node(name)
            for dep in deps:
                graph.add_dependency(name, dep)
        return IntegrationValidator(reg, graph), reg, graph

    def test_validate_dependencies_valid(self) -> None:
        validator, _, _ = self._make_validator()
        results = validator.validate_dependencies()
        errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0

    def test_validate_dependencies_missing(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        reg.register("a", StubComponent(), dependencies=["nonexistent"])
        graph.add_node("a")
        graph.add_dependency("a", "nonexistent")
        validator = IntegrationValidator(reg, graph)
        results = validator.validate_dependencies()
        errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
        assert len(errors) > 0

    def test_validate_circular_none(self) -> None:
        validator, _, _ = self._make_validator()
        results = validator.validate_circular_dependencies()
        info_results = [r for r in results if r.severity == ValidationSeverity.INFO]
        assert len(info_results) > 0

    def test_validate_circular_found(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        reg.register("a", StubComponent())
        reg.register("b", StubComponent())
        graph.add_dependency("a", "b")
        graph.add_dependency("b", "a")
        validator = IntegrationValidator(reg, graph)
        results = validator.validate_circular_dependencies()
        critical = [r for r in results if r.severity == ValidationSeverity.CRITICAL]
        assert len(critical) > 0

    def test_validate_missing_registrations(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        graph.add_node("graph_only")
        reg.register("reg_only", StubComponent())
        validator = IntegrationValidator(reg, graph)
        results = validator.validate_missing_registrations()
        warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
        assert len(warnings) == 2

    def test_validate_lifecycle_compatibility(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        info = reg.register("a", StubComponent())
        info.state = ComponentState.FAILED
        validator = IntegrationValidator(reg, graph)
        results = validator.validate_lifecycle_compatibility()
        errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
        assert len(errors) > 0

    def test_validate_provider_availability(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        reg.register("a", None)
        validator = IntegrationValidator(reg, graph)
        results = validator.validate_provider_availability()
        errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
        assert len(errors) > 0

    def test_validate_all(self) -> None:
        validator, _, _ = self._make_validator()
        results = validator.validate_all()
        assert len(results) > 0

    def test_is_valid(self) -> None:
        validator, _, _ = self._make_validator()
        assert validator.is_valid() is True

    def test_is_invalid_with_errors(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        reg.register("a", StubComponent(), dependencies=["missing"])
        graph.add_node("a")
        graph.add_dependency("a", "missing")
        validator = IntegrationValidator(reg, graph)
        assert validator.is_valid() is False

    def test_validation_result_to_dict(self) -> None:
        r = ValidationResult("check", ValidationSeverity.WARNING, "msg", {"k": "v"})
        d = r.to_dict()
        assert d["check"] == "check"
        assert d["severity"] == "warning"
        assert d["message"] == "msg"

    def test_validate_interface_compatibility(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        stub = StubComponent()
        reg.register("a", stub)
        validator = IntegrationValidator(reg, graph)
        results = validator.validate_interface_compatibility()
        warn = [r for r in results if r.check == "interface_compatibility"]
        assert len(warn) == 0


# ---------------------------------------------------------------------------
# Compatibility
# ---------------------------------------------------------------------------


class TestCompatibilityChecker:
    def _make_checker(self) -> CompatibilityChecker:
        reg = IntegrationRegistry()
        reg.register("a", StubComponent(), component_type="engine")
        reg.register("b", StubComponent(), component_type="provider")
        return CompatibilityChecker(reg)

    def test_check_pair_compatible(self) -> None:
        checker = self._make_checker()
        report = checker.check_pair("a", "b")
        assert report.level == CompatibilityLevel.COMPATIBLE

    def test_check_pair_unknown(self) -> None:
        checker = self._make_checker()
        report = checker.check_pair("a", "nonexistent")
        assert report.level == CompatibilityLevel.UNKNOWN

    def test_check_pair_incompatible(self) -> None:
        reg = IntegrationRegistry()
        info = reg.register("a", StubComponent())
        info.state = ComponentState.FAILED
        reg.register("b", StubComponent())
        checker = CompatibilityChecker(reg)
        report = checker.check_pair("a", "b")
        assert report.level == CompatibilityLevel.INCOMPATIBLE

    def test_check_all(self) -> None:
        checker = self._make_checker()
        reports = checker.check_all()
        assert len(reports) == 1

    def test_check_api_compatibility(self) -> None:
        checker = self._make_checker()
        reports = checker.check_api_compatibility()
        assert len(reports) > 0

    def test_check_provider_compatibility(self) -> None:
        checker = self._make_checker()
        reports = checker.check_provider_compatibility()
        assert len(reports) > 0

    def test_get_issues_none(self) -> None:
        checker = self._make_checker()
        issues = checker.get_issues()
        assert len(issues) == 0

    def test_get_issues_found(self) -> None:
        reg = IntegrationRegistry()
        info = reg.register("a", StubComponent())
        info.state = ComponentState.FAILED
        reg.register("b", StubComponent())
        checker = CompatibilityChecker(reg)
        issues = checker.get_issues()
        assert len(issues) > 0

    def test_report_to_dict(self) -> None:
        report = CompatibilityReport("a", "b", CompatibilityLevel.COMPATIBLE, "ok")
        d = report.to_dict()
        assert d["component_a"] == "a"
        assert d["level"] == "compatible"


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealthAggregator:
    def _make_aggregator(self) -> HealthAggregator:
        reg = IntegrationRegistry()
        reg.register("healthy", StubComponent())
        reg.register("failed", StubComponent())
        reg.update_state("healthy", ComponentState.RUNNING)
        reg.update_state("failed", ComponentState.FAILED)
        return HealthAggregator(reg)

    def test_check_component_healthy(self) -> None:
        agg = self._make_aggregator()
        h = agg.check_component("healthy")
        assert h.status == HealthStatus.HEALTHY

    def test_check_component_unhealthy(self) -> None:
        agg = self._make_aggregator()
        h = agg.check_component("failed")
        assert h.status == HealthStatus.UNHEALTHY

    def test_check_component_unknown(self) -> None:
        agg = self._make_aggregator()
        h = agg.check_component("nonexistent")
        assert h.status == HealthStatus.UNKNOWN

    def test_check_all(self) -> None:
        agg = self._make_aggregator()
        results = agg.check_all()
        assert len(results) == 2

    def test_aggregate_unhealthy(self) -> None:
        agg = self._make_aggregator()
        status = agg.aggregate()
        assert status.status == HealthStatus.UNHEALTHY
        assert status.unhealthy_count == 1

    def test_aggregate_healthy(self) -> None:
        reg = IntegrationRegistry()
        reg.register("a", StubComponent())
        reg.update_state("a", ComponentState.RUNNING)
        agg = HealthAggregator(reg)
        status = agg.aggregate()
        assert status.status == HealthStatus.HEALTHY

    def test_aggregate_degraded(self) -> None:
        reg = IntegrationRegistry()
        reg.register("a", StubComponent())
        reg.register("b", StubComponent())
        reg.update_state("a", ComponentState.RUNNING)
        reg.update_state("b", ComponentState.DEGRADED)
        agg = HealthAggregator(reg)
        status = agg.aggregate()
        assert status.status == HealthStatus.DEGRADED

    def test_custom_health_check(self) -> None:
        agg = self._make_aggregator()
        agg.set_health_check("healthy", lambda c: True)
        h = agg.check_component("healthy")
        assert h.status == HealthStatus.HEALTHY

    def test_custom_health_check_failure(self) -> None:
        agg = self._make_aggregator()
        agg.set_health_check("healthy", lambda c: (_ for _ in ()).throw(RuntimeError("bad")))
        h = agg.check_component("healthy")
        assert h.status == HealthStatus.UNHEALTHY

    def test_system_health_status_to_dict(self) -> None:
        status = SystemHealthStatus(HealthStatus.HEALTHY, 10, 8, 1, 1, 0)
        d = status.to_dict()
        assert d["component_count"] == 10
        assert d["healthy_count"] == 8

    def test_system_health_to_dict(self) -> None:
        h = SystemHealth("a", HealthStatus.HEALTHY, "ok")
        d = h.to_dict()
        assert d["name"] == "a"
        assert d["status"] == "healthy"


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class TestIntegrationMetrics:
    def test_metrics_snapshot(self) -> None:
        mc = IntegrationMetricsCollector()
        mc.start()
        mc.record_startup(0.5)
        mc.record_dependency_resolution(0.1)
        mc.record_initialization_failure()
        snap = mc.snapshot(10)
        assert snap.registered_components == 10
        assert snap.startup_time == 0.5
        assert snap.initialization_failures == 1
        assert snap.dependency_resolution_time == 0.1

    def test_metrics_to_dict(self) -> None:
        snap = IntegrationMetrics(10, 0.5, 1, 0, 0.1, 60.0)
        d = snap.to_dict()
        assert d["registered_components"] == 10
        assert d["uptime_seconds"] == 60.0

    def test_concurrent_metrics(self) -> None:
        mc = IntegrationMetricsCollector()
        mc.start()
        errors: list[Exception] = []

        def record_many() -> None:
            try:
                for _ in range(100):
                    mc.record_initialization_failure()
                    mc.record_integration_failure()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=record_many) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        snap = mc.snapshot()
        assert snap.initialization_failures == 400


# ---------------------------------------------------------------------------
# Tracing
# ---------------------------------------------------------------------------


class TestIntegrationTracer:
    def test_start_and_finish(self) -> None:
        tracer = IntegrationTracer()
        tid = tracer.start_trace("op1")
        assert tracer.count() == 1
        tracer.finish_trace(tid)
        trace = tracer.get_trace(tid)
        assert trace is not None
        assert trace["status"] == "completed"
        assert trace["duration_ms"] is not None

    def test_finish_with_error(self) -> None:
        tracer = IntegrationTracer()
        tid = tracer.start_trace("op1")
        tracer.finish_trace(tid, status="error", error="boom")
        trace = tracer.get_trace(tid)
        assert trace["status"] == "error"
        assert trace["error"] == "boom"

    def test_get_traces_limit(self) -> None:
        tracer = IntegrationTracer()
        for i in range(10):
            tracer.start_trace(f"op_{i}")
        traces = tracer.get_traces(5)
        assert len(traces) == 5

    def test_get_trace_not_found(self) -> None:
        tracer = IntegrationTracer()
        assert tracer.get_trace("nonexistent") is None

    def test_clear(self) -> None:
        tracer = IntegrationTracer()
        tracer.start_trace("op1")
        tracer.clear()
        assert tracer.count() == 0

    def test_trim(self) -> None:
        tracer = IntegrationTracer(max_traces=5)
        for i in range(10):
            tracer.start_trace(f"op_{i}")
        tracer._trim()
        assert tracer.count() == 5


# ---------------------------------------------------------------------------
# Coordinator
# ---------------------------------------------------------------------------


class TestIntegrationCoordinator:
    @pytest.mark.asyncio
    async def test_register_and_list(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        coord = SystemCoordinator(reg, graph)
        await coord.register_component("a", StubComponent(), component_type="engine")
        components = await coord.list_components()
        assert len(components) == 1

    @pytest.mark.asyncio
    async def test_unregister(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        coord = SystemCoordinator(reg, graph)
        await coord.register_component("a", StubComponent())
        result = await coord.unregister_component("a")
        assert result is True
        assert await coord.get_component("a") is None

    @pytest.mark.asyncio
    async def test_discover_components(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        coord = SystemCoordinator(reg, graph)
        await coord.register_component("a", StubComponent())
        await coord.register_component("b", StubComponent())
        discovered = await coord.discover_components()
        assert len(discovered) == 2

    @pytest.mark.asyncio
    async def test_initialize_component(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        coord = SystemCoordinator(reg, graph)
        comp = StubComponent()
        await coord.register_component("a", comp)
        result = await coord.initialize_component("a")
        assert result is True
        assert comp.started is True

    @pytest.mark.asyncio
    async def test_initialize_component_failure(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        coord = SystemCoordinator(reg, graph)
        comp = StubComponent(fail_start=True)
        await coord.register_component("a", comp)
        result = await coord.initialize_component("a")
        assert result is False

    @pytest.mark.asyncio
    async def test_shutdown_component(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        coord = SystemCoordinator(reg, graph)
        comp = StubComponent()
        await coord.register_component("a", comp)
        await coord.initialize_component("a")
        result = await coord.shutdown_component("a")
        assert result is True
        assert comp.stopped is True

    @pytest.mark.asyncio
    async def test_shutdown_component_failure(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        coord = SystemCoordinator(reg, graph)
        comp = StubComponent(fail_shutdown=True)
        await coord.register_component("a", comp)
        result = await coord.shutdown_component("a")
        assert result is False

    @pytest.mark.asyncio
    async def test_shutdown_nonexistent(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        coord = SystemCoordinator(reg, graph)
        result = await coord.shutdown_component("nope")
        assert result is False

    def test_event_log(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        coord = IntegrationCoordinator(reg, graph)
        coord._log_event("test", "target", {})
        log = coord.get_event_log()
        assert len(log) == 1


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class TestSystemOrchestrator:
    @pytest.mark.asyncio
    async def test_discover_and_register(self) -> None:
        orch = SystemOrchestrator()
        names = await orch.discover_and_register()
        assert len(names) == len(SystemOrchestrator.SUBSYSTEM_DEPENDENCIES)

    @pytest.mark.asyncio
    async def test_validate_dependencies(self) -> None:
        orch = SystemOrchestrator()
        await orch.discover_and_register()
        order = await orch.validate_dependencies()
        assert len(order) > 0

    @pytest.mark.asyncio
    async def test_validate_returns_topological_order(self) -> None:
        orch = SystemOrchestrator()
        await orch.discover_and_register()
        order = await orch.validate_dependencies()
        graph = orch.graph
        for name in order:
            deps = graph.get_direct_dependencies(name)
            for dep in deps:
                if dep in order:
                    assert order.index(dep) < order.index(name)

    @pytest.mark.asyncio
    async def test_initialize_components(self) -> None:
        orch = SystemOrchestrator()
        await orch.discover_and_register()
        await orch.validate_dependencies()
        comp = StubComponent("cognitive_engine")
        orch.register_component("cognitive_engine", comp)
        results = await orch.initialize_components()
        assert "cognitive_engine" in results

    @pytest.mark.asyncio
    async def test_shutdown_components(self) -> None:
        orch = SystemOrchestrator()
        await orch.discover_and_register()
        await orch.validate_dependencies()
        comp = StubComponent("event_system")
        orch.register_component("event_system", comp)
        await orch.initialize_components()
        results = await orch.shutdown_components()
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_reinitialize(self) -> None:
        orch = SystemOrchestrator()
        await orch.discover_and_register()
        await orch.validate_dependencies()
        comp = StubComponent("security")
        orch.register_component("security", comp)
        await orch.initialize_components()
        results = await orch.reinitialize(["security"])
        assert results["security"] is True

    def test_register_component(self) -> None:
        orch = SystemOrchestrator()
        orch.register_component("a", StubComponent(), dependencies=["b"])
        assert orch.registry.get("a") is not None

    def test_unregister_component(self) -> None:
        orch = SystemOrchestrator()
        orch.register_component("a", StubComponent())
        assert orch.unregister_component("a") is True

    def test_init_order(self) -> None:
        orch = SystemOrchestrator()
        orch._init_order = ["a", "b", "c"]
        assert orch.init_order == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_discover_idempotent(self) -> None:
        orch = SystemOrchestrator()
        await orch.discover_and_register()
        count1 = orch.registry.count()
        await orch.discover_and_register()
        count2 = orch.registry.count()
        assert count1 == count2


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


class TestSystemDiagnostics:
    def test_collect(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        reg.register("eng", StubComponent(), component_type="engine")
        reg.register("prov", StubComponent(), component_type="provider")
        graph.add_node("eng")
        graph.add_node("prov")
        diag = SystemDiagnostics(reg, graph, ["eng", "prov"])
        data = diag.collect()
        assert "eng" in data["engines"]
        assert "prov" in data["providers"]
        assert data["initialization_order"] == ["eng", "prov"]

    def test_get_component_info(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        reg.register("a", StubComponent())
        graph.add_node("a")
        diag = SystemDiagnostics(reg, graph)
        info = diag.get_component_info("a")
        assert info is not None
        assert info["name"] == "a"

    def test_get_component_info_not_found(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        diag = SystemDiagnostics(reg, graph)
        assert diag.get_component_info("nope") is None

    def test_record_failure(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        diag = SystemDiagnostics(reg, graph)
        diag.record_failure("a", "boom", "init")
        data = diag.collect()
        assert len(data["integration_failures"]) == 1

    def test_record_compatibility_issue(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        diag = SystemDiagnostics(reg, graph)
        diag.record_compatibility_issue("a", "b", "mismatch")
        data = diag.collect()
        assert len(data["compatibility_issues"]) == 1

    def test_summary(self) -> None:
        reg = IntegrationRegistry()
        graph = DependencyGraph()
        reg.register("a", StubComponent())
        reg.update_state("a", ComponentState.RUNNING)
        diag = SystemDiagnostics(reg, graph)
        s = diag.summary()
        assert s["total"] == 1
        assert s["running"] == 1


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class TestIntegrationEngine:
    @pytest.mark.asyncio
    async def test_start_and_stop(self) -> None:
        engine = IntegrationEngine()
        await engine.start()
        assert engine.is_running()
        await engine.shutdown()
        assert not engine.is_running()

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        engine = IntegrationEngine()
        engine.register_component("test_comp", StubComponent())
        await engine.start()
        status = await engine.perform_health_check()
        assert status.component_count > 0
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_validate_integrations(self) -> None:
        engine = IntegrationEngine()
        await engine.start()
        results = await engine.validate_integrations()
        assert len(results) > 0
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_dependency_graph(self) -> None:
        engine = IntegrationEngine()
        await engine.start()
        graph = engine.generate_dependency_graph()
        assert "nodes" in graph
        assert "edges" in graph
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_diagnostics(self) -> None:
        engine = IntegrationEngine()
        await engine.start()
        diag = engine.generate_diagnostics()
        assert "engines" in diag or "services" in diag
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_compatibility(self) -> None:
        engine = IntegrationEngine()
        await engine.start()
        report = engine.get_compatibility_report()
        assert "compatible" in report
        assert "checks" in report
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_status(self) -> None:
        engine = IntegrationEngine()
        await engine.start()
        status = engine.get_status()
        assert "state" in status
        assert "registered_components" in status
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_metrics(self) -> None:
        engine = IntegrationEngine()
        engine.register_component("test_comp", StubComponent())
        await engine.start()
        metrics = engine.get_metrics()
        assert metrics.registered_components > 0
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_traces(self) -> None:
        engine = IntegrationEngine()
        await engine.start()
        traces = engine.get_traces()
        assert len(traces) > 0
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_reinitialize(self) -> None:
        engine = IntegrationEngine()
        await engine.start()
        results = await engine.reinitialize()
        assert isinstance(results, dict)
        await engine.shutdown()

    def test_register_component(self) -> None:
        engine = IntegrationEngine()
        engine.register_component("a", StubComponent())
        assert engine.registry.get("a") is not None

    def test_unregister_component(self) -> None:
        engine = IntegrationEngine()
        engine.register_component("a", StubComponent())
        assert engine.unregister_component("a") is True

    @pytest.mark.asyncio
    async def test_discover_components(self) -> None:
        engine = IntegrationEngine()
        discovered = await engine.discover_components()
        assert len(discovered) > 0

    def test_properties(self) -> None:
        engine = IntegrationEngine()
        assert engine.registry is not None
        assert engine.graph is not None
        assert engine.coordinator is not None
        assert engine.orchestrator is not None
        assert engine.lifecycle is not None
        assert engine.health is not None
        assert engine.validator is not None
        assert engine.compatibility is not None
        assert engine.diagnostics is not None
        assert engine.metrics is not None
        assert engine.tracer is not None


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class TestIntegrationFactory:
    def test_create(self) -> None:
        engine = IntegrationFactory.create()
        assert engine is not None
        assert isinstance(engine, IntegrationEngine)

    def test_create_default(self) -> None:
        engine = IntegrationFactory.create_default()
        assert engine is not None

    def test_get_or_create(self) -> None:
        IntegrationFactory.reset()
        engine = IntegrationFactory.get_or_create()
        assert engine is not None
        engine2 = IntegrationFactory.get_or_create()
        assert engine is engine2

    def test_reset(self) -> None:
        IntegrationFactory.reset()
        assert IntegrationFactory._instance is None


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(api_router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestAPIEndpoints:
    @pytest.mark.asyncio
    async def test_health(self, client: AsyncClient) -> None:
        resp = await client.get("/integration/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_status(self, client: AsyncClient) -> None:
        resp = await client.get("/integration/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_components(self, client: AsyncClient) -> None:
        resp = await client.get("/integration/components")
        assert resp.status_code == 200
        data = resp.json()
        assert "components" in data["data"]

    @pytest.mark.asyncio
    async def test_dependencies(self, client: AsyncClient) -> None:
        resp = await client.get("/integration/dependencies")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data["data"]

    @pytest.mark.asyncio
    async def test_diagnostics(self, client: AsyncClient) -> None:
        resp = await client.get("/integration/diagnostics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_compatibility(self, client: AsyncClient) -> None:
        resp = await client.get("/integration/compatibility")
        assert resp.status_code == 200
        data = resp.json()
        assert "compatible" in data["data"]

    @pytest.mark.asyncio
    async def test_metrics(self, client: AsyncClient) -> None:
        resp = await client.get("/integration/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_traces(self, client: AsyncClient) -> None:
        resp = await client.get("/integration/traces")
        assert resp.status_code == 200
        data = resp.json()
        assert "traces" in data["data"]

    @pytest.mark.asyncio
    async def test_validate(self, client: AsyncClient) -> None:
        resp = await client.post("/integration/validate")
        assert resp.status_code == 200
        data = resp.json()
        assert "valid" in data["data"]

    @pytest.mark.asyncio
    async def test_reinitialize(self, client: AsyncClient) -> None:
        resp = await client.post("/integration/reinitialize")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True


# ---------------------------------------------------------------------------
# Integration — full workflow
# ---------------------------------------------------------------------------


class TestIntegrationWorkflow:
    @pytest.mark.asyncio
    async def test_full_lifecycle(self) -> None:
        engine = IntegrationEngine()
        engine.register_component("cognitive_engine", StubComponent(), component_type="engine", dependencies=["events"])
        engine.register_component("events", StubComponent(), component_type="service")
        await engine.start()
        status = await engine.perform_health_check()
        assert status.component_count >= 2
        graph = engine.generate_dependency_graph()
        assert graph["node_count"] >= 2
        await engine.shutdown()
        assert not engine.is_running()

    @pytest.mark.asyncio
    async def test_multiple_registrations(self) -> None:
        engine = IntegrationEngine()
        for i in range(10):
            engine.register_component(f"comp_{i}", StubComponent())
        await engine.start()
        assert engine.registry.count() >= 10
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_unregister_during_runtime(self) -> None:
        engine = IntegrationEngine()
        engine.register_component("a", StubComponent())
        engine.register_component("b", StubComponent())
        await engine.start()
        engine.unregister_component("a")
        assert engine.registry.get("a") is None
        await engine.shutdown()


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


class TestConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_registration(self) -> None:
        engine = IntegrationEngine()
        errors: list[Exception] = []

        async def register_batch(prefix: str) -> None:
            try:
                for i in range(20):
                    engine.register_component(f"{prefix}_{i}", StubComponent())
            except Exception as exc:
                errors.append(exc)

        await asyncio.gather(*[register_batch(f"batch_{i}") for i in range(5)])
        assert not errors
        assert engine.registry.count() >= 100

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self) -> None:
        engine = IntegrationEngine()
        await engine.start()
        errors: list[Exception] = []

        async def health_check() -> None:
            try:
                await engine.perform_health_check()
            except Exception as exc:
                errors.append(exc)

        await asyncio.gather(*[health_check() for _ in range(10)])
        assert not errors
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_concurrent_validate(self) -> None:
        engine = IntegrationEngine()
        await engine.start()
        errors: list[Exception] = []

        async def validate() -> None:
            try:
                await engine.validate_integrations()
            except Exception as exc:
                errors.append(exc)

        await asyncio.gather(*[validate() for _ in range(5)])
        assert not errors
        await engine.shutdown()


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_engine_no_components(self) -> None:
        engine = IntegrationEngine()
        await engine.start()
        status = await engine.perform_health_check()
        assert status.component_count == 0
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_double_start(self) -> None:
        engine = IntegrationEngine()
        await engine.start()
        await engine.start()
        assert engine.is_running()
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_without_start(self) -> None:
        engine = IntegrationEngine()
        await engine.shutdown()
        assert not engine.is_running()

    def test_empty_graph_cycles(self) -> None:
        g = DependencyGraph()
        assert g.detect_cycles() == []

    def test_empty_graph_topological_sort(self) -> None:
        g = DependencyGraph()
        assert g.topological_sort() == []

    def test_single_node_graph(self) -> None:
        g = DependencyGraph()
        g.add_node("a")
        order = g.topological_sort()
        assert order == ["a"]

    def test_registry_thread_safety(self) -> None:
        reg = IntegrationRegistry()
        errors: list[Exception] = []

        def access_registry() -> None:
            try:
                for i in range(100):
                    reg.register(f"t_{threading.current_thread().ident}_{i}", object())
                    reg.list_all()
                    reg.count()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=access_registry) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors

    def test_lifecycle_terminal_state(self) -> None:
        lc = IntegrationLifecycle()
        lc.transition(IntegrationState.DISCOVERING, "d")
        lc.transition(IntegrationState.VALIDATED, "v")
        lc.transition(IntegrationState.INITIALIZING, "i")
        lc.transition(IntegrationState.READY, "r")
        lc.transition(IntegrationState.RUNNING, "run")
        lc.transition(IntegrationState.SHUTTING_DOWN, "s")
        lc.transition(IntegrationState.SHUTDOWN, "off")
        assert lc.transition(IntegrationState.RUNNING, "cant") is False
