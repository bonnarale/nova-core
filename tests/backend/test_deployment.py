"""Comprehensive tests for Chapter 27 — Deployment."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

# ─── Enums ────────────────────────────────────────────────────────────────
from app.deployment.enums import (
    ConfigFormat,
    DeployEnvironment,
    DeployState,
    HealthStatus,
    SecretSource,
)


class TestEnums:
    def test_deploy_environment_values(self) -> None:
        assert DeployEnvironment.DEVELOPMENT.value == "development"
        assert DeployEnvironment.TESTING.value == "testing"
        assert DeployEnvironment.STAGING.value == "staging"
        assert DeployEnvironment.PRODUCTION.value == "production"

    def test_deploy_state_values(self) -> None:
        assert DeployState.REGISTERED.value == "registered"
        assert DeployState.RUNNING.value == "running"
        assert DeployState.STOPPED.value == "stopped"
        assert DeployState.FAILED.value == "failed"

    def test_health_status_values(self) -> None:
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_secret_source_values(self) -> None:
        assert SecretSource.ENVIRONMENT.value == "environment"
        assert SecretSource.DOCKER.value == "docker"
        assert SecretSource.KUBERNETES.value == "kubernetes"
        assert SecretSource.VAULT.value == "vault"
        assert SecretSource.FILE.value == "file"

    def test_config_format_values(self) -> None:
        assert ConfigFormat.JSON.value == "json"
        assert ConfigFormat.YAML.value == "yaml"
        assert ConfigFormat.ENV.value == "env"
        assert ConfigFormat.TOML.value == "toml"

    def test_all_deploy_states(self) -> None:
        states = list(DeployState)
        assert len(states) == 8

    def test_all_deploy_environments(self) -> None:
        envs = list(DeployEnvironment)
        assert len(envs) == 4

    def test_all_health_statuses(self) -> None:
        statuses = list(HealthStatus)
        assert len(statuses) == 4

    def test_all_secret_sources(self) -> None:
        sources = list(SecretSource)
        assert len(sources) == 5


# ─── Base ABCs ─────────────────────────────────────────────────────────────
from app.deployment.base import (
    ConfigurationProvider,
    DeploymentProvider,
    EnvironmentProvider,
    HealthProvider,
    SecretProvider,
)


class TestBaseABCs:
    def test_cannot_instantiate_deployment_provider(self) -> None:
        with pytest.raises(TypeError):
            DeploymentProvider()  # type: ignore[abstract]

    def test_cannot_instantiate_environment_provider(self) -> None:
        with pytest.raises(TypeError):
            EnvironmentProvider()  # type: ignore[abstract]

    def test_cannot_instantiate_configuration_provider(self) -> None:
        with pytest.raises(TypeError):
            ConfigurationProvider()  # type: ignore[abstract]

    def test_cannot_instantiate_health_provider(self) -> None:
        with pytest.raises(TypeError):
            HealthProvider()  # type: ignore[abstract]

    def test_cannot_instantiate_secret_provider(self) -> None:
        with pytest.raises(TypeError):
            SecretProvider()  # type: ignore[abstract]


# ─── Models ────────────────────────────────────────────────────────────────
from app.deployment.models import (
    ConfigurationItem,
    DeploymentHealth,
    DeploymentMetrics,
    DeploymentStatistics,
    EnvironmentVariable,
    HealthCheck,
    SecretInfo,
)


class TestModels:
    def test_deployment_metrics_defaults(self) -> None:
        m = DeploymentMetrics()
        assert m.total_startups == 0
        assert m.total_shutdowns == 0

    def test_deployment_metrics_to_dict(self) -> None:
        m = DeploymentMetrics(total_startups=3, uptime_seconds=100.0)
        d = m.to_dict()
        assert d["total_startups"] == 3
        assert d["uptime_seconds"] == 100.0

    def test_deployment_health_defaults(self) -> None:
        h = DeploymentHealth()
        assert h.status == HealthStatus.HEALTHY.value
        assert h.startup is False

    def test_deployment_health_to_dict(self) -> None:
        h = DeploymentHealth(status="degraded", readiness=True)
        d = h.to_dict()
        assert d["status"] == "degraded"
        assert d["readiness"] is True

    def test_deployment_statistics_defaults(self) -> None:
        s = DeploymentStatistics()
        assert s.state == DeployState.REGISTERED.value
        assert s.environment == DeployEnvironment.DEVELOPMENT.value

    def test_deployment_statistics_to_dict(self) -> None:
        s = DeploymentStatistics(state="running", uptime_seconds=3600.0)
        d = s.to_dict()
        assert d["state"] == "running"
        assert d["uptime_seconds"] == 3600.0

    def test_configuration_item(self) -> None:
        c = ConfigurationItem(key="debug", value=True, section="app")
        d = c.to_dict()
        assert d["key"] == "debug"
        assert d["value"] is True
        assert d["section"] == "app"

    def test_environment_variable(self) -> None:
        e = EnvironmentVariable(key="APP_ENV", value="production", required=True)
        d = e.to_dict()
        assert d["key"] == "APP_ENV"
        assert d["value"] == "production"
        assert d["required"] is True

    def test_health_check(self) -> None:
        hc = HealthCheck(name="database", status="healthy", latency_ms=1.5)
        d = hc.to_dict()
        assert d["name"] == "database"
        assert d["status"] == "healthy"
        assert d["latency_ms"] == 1.5

    def test_secret_info(self) -> None:
        si = SecretInfo(key="api_key", source="environment")
        d = si.to_dict()
        assert d["key"] == "api_key"
        assert d["source"] == "environment"


# ─── Lifecycle ─────────────────────────────────────────────────────────────
from app.deployment.lifecycle import DeploymentLifecycle


class TestLifecycle:
    def test_initial_state(self) -> None:
        lc = DeploymentLifecycle()
        assert lc.state == DeployState.REGISTERED

    def test_valid_transitions(self) -> None:
        lc = DeploymentLifecycle()
        assert lc.transition(DeployState.INITIALIZING) is True
        assert lc.transition(DeployState.STARTING) is True
        assert lc.transition(DeployState.RUNNING) is True
        assert lc.state == DeployState.RUNNING

    def test_invalid_transition(self) -> None:
        lc = DeploymentLifecycle()
        assert lc.transition(DeployState.RUNNING) is False

    def test_is_running(self) -> None:
        lc = DeploymentLifecycle()
        assert lc.is_running() is False
        lc.transition(DeployState.INITIALIZING)
        lc.transition(DeployState.STARTING)
        lc.transition(DeployState.RUNNING)
        assert lc.is_running() is True

    def test_is_ready(self) -> None:
        lc = DeploymentLifecycle()
        lc.transition(DeployState.INITIALIZING)
        lc.transition(DeployState.STARTING)
        lc.transition(DeployState.RUNNING)
        assert lc.is_ready() is True

    def test_can_accept_traffic(self) -> None:
        lc = DeploymentLifecycle()
        lc.transition(DeployState.INITIALIZING)
        lc.transition(DeployState.STARTING)
        lc.transition(DeployState.RUNNING)
        assert lc.can_accept_traffic() is True

    def test_uptime(self) -> None:
        lc = DeploymentLifecycle()
        assert lc.uptime() == 0.0
        lc.transition(DeployState.INITIALIZING)
        lc.transition(DeployState.STARTING)
        lc.transition(DeployState.RUNNING)
        assert lc.uptime() >= 0.0

    def test_history(self) -> None:
        lc = DeploymentLifecycle()
        lc.transition(DeployState.INITIALIZING, "start")
        lc.transition(DeployState.STARTING, "init done")
        lc.transition(DeployState.RUNNING, "ready")
        history = lc.get_history()
        assert len(history) == 3
        assert history[0]["from"] == "registered"
        assert history[0]["to"] == "initializing"

    def test_get_status(self) -> None:
        lc = DeploymentLifecycle()
        status = lc.get_status()
        assert "state" in status
        assert "is_running" in status
        assert "uptime_seconds" in status

    def test_full_lifecycle_to_stopped(self) -> None:
        lc = DeploymentLifecycle()
        lc.transition(DeployState.INITIALIZING)
        lc.transition(DeployState.STARTING)
        lc.transition(DeployState.RUNNING)
        lc.transition(DeployState.SHUTTING_DOWN)
        lc.transition(DeployState.STOPPED)
        assert lc.state == DeployState.STOPPED

    def test_failed_to_initializing(self) -> None:
        lc = DeploymentLifecycle()
        lc.transition(DeployState.INITIALIZING)
        lc.transition(DeployState.STARTING)
        lc.transition(DeployState.FAILED)
        assert lc.transition(DeployState.INITIALIZING) is True


# ─── Validation ────────────────────────────────────────────────────────────
from app.deployment.validation import EnvironmentValidator


class TestValidation:
    def test_validate_with_required_present(self) -> None:
        v = EnvironmentValidator(required=["APP_NAME", "APP_ENV"])
        result = v.validate({"APP_NAME": "nova", "APP_ENV": "dev"})
        assert result["valid"] is True
        assert len(result["missing_required"]) == 0

    def test_validate_with_required_missing(self) -> None:
        v = EnvironmentValidator(required=["APP_NAME", "APP_ENV"])
        result = v.validate({"APP_NAME": "nova"})
        assert result["valid"] is False
        assert "APP_ENV" in result["missing_required"]

    def test_validate_with_empty_value(self) -> None:
        v = EnvironmentValidator(required=["APP_NAME"])
        result = v.validate({"APP_NAME": ""})
        assert result["valid"] is False

    def test_defaults_applied(self) -> None:
        v = EnvironmentValidator(
            required=["APP_NAME"],
            optional={"LOG_LEVEL": "info"},
        )
        result = v.validate({"APP_NAME": "nova"})
        assert result["valid"] is True
        assert "LOG_LEVEL" in result["defaults_applied"]

    def test_get_effective_config(self) -> None:
        v = EnvironmentValidator(
            required=["APP_NAME"],
            optional={"LOG_LEVEL": "info", "DEBUG": "false"},
        )
        config = v.get_effective_config({"APP_NAME": "nova", "DEBUG": "true"})
        assert config["APP_NAME"] == "nova"
        assert config["DEBUG"] == "true"
        assert config["LOG_LEVEL"] == "info"

    def test_add_required(self) -> None:
        v = EnvironmentValidator(required=[])
        v.add_required("NEW_VAR")
        assert "NEW_VAR" in v.required_variables

    def test_add_optional(self) -> None:
        v = EnvironmentValidator(optional={})
        v.add_optional("NEW_OPT", default="val")
        assert v.optional_defaults["NEW_OPT"] == "val"

    def test_validate_with_all_defaults(self) -> None:
        v = EnvironmentValidator(required=[], optional={"X": "1"})
        result = v.validate({})
        assert result["valid"] is True


# ─── Environment Manager ───────────────────────────────────────────────────
from app.deployment.environment import EnvironmentManager


class TestEnvironmentManager:
    @pytest.mark.asyncio
    async def test_get_existing(self) -> None:
        em = EnvironmentManager(env={"MY_VAR": "hello"})
        assert await em.get("MY_VAR") == "hello"

    @pytest.mark.asyncio
    async def test_get_default(self) -> None:
        em = EnvironmentManager(env={})
        assert await em.get("MISSING", "fallback") == "fallback"

    @pytest.mark.asyncio
    async def test_set_override(self) -> None:
        em = EnvironmentManager(env={"A": "1"})
        await em.set("A", "2")
        assert await em.get("A") == "2"

    @pytest.mark.asyncio
    async def test_get_all(self) -> None:
        em = EnvironmentManager(env={"X": "1", "Y": "2"})
        all_vars = await em.get_all()
        assert "X" in all_vars
        assert "Y" in all_vars

    @pytest.mark.asyncio
    async def test_validate_pass(self) -> None:
        em = EnvironmentManager(env={"A": "1", "B": "2"})
        result = await em.validate(["A", "B"])
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_fail(self) -> None:
        em = EnvironmentManager(env={"A": "1"})
        result = await em.validate(["A", "B"])
        assert result["valid"] is False
        assert "B" in result["missing"]

    @pytest.mark.asyncio
    async def test_get_filtered(self) -> None:
        em = EnvironmentManager(env={"APP_DEBUG": "true", "APP_LOG": "info", "DB_HOST": "localhost"})
        filtered = await em.get_filtered("APP_")
        assert "APP_DEBUG" in filtered
        assert "DB_HOST" not in filtered

    @pytest.mark.asyncio
    async def test_get_variable(self) -> None:
        em = EnvironmentManager(env={"KEY": "val"})
        var = await em.get_variable("KEY")
        assert var.key == "KEY"
        assert var.value == "val"

    @pytest.mark.asyncio
    async def test_get_effective_config(self) -> None:
        em = EnvironmentManager(env={"A": "1"})
        config = await em.get_effective_config({"B": "2"})
        assert "A" in config
        assert "B" in config


# ─── Configuration ─────────────────────────────────────────────────────────
from app.deployment.config import DeploymentConfiguration


class TestConfiguration:
    @pytest.mark.asyncio
    async def test_default_config_development(self) -> None:
        cfg = DeploymentConfiguration("development")
        assert await cfg.get("debug") is True
        assert await cfg.get("workers") == 1

    @pytest.mark.asyncio
    async def test_default_config_production(self) -> None:
        cfg = DeploymentConfiguration("production")
        assert await cfg.get("debug") is False
        assert await cfg.get("workers") == 4

    @pytest.mark.asyncio
    async def test_set_config(self) -> None:
        cfg = DeploymentConfiguration("development")
        await cfg.set("custom_key", "custom_value")
        assert await cfg.get("custom_key") == "custom_value"

    @pytest.mark.asyncio
    async def test_get_all(self) -> None:
        cfg = DeploymentConfiguration("development")
        all_items = await cfg.get_all()
        assert "debug" in all_items

    @pytest.mark.asyncio
    async def test_validate(self) -> None:
        cfg = DeploymentConfiguration("development")
        result = await cfg.validate()
        assert result["valid"] is True
        assert result["environment"] == "development"

    @pytest.mark.asyncio
    async def test_get_section(self) -> None:
        cfg = DeploymentConfiguration("development")
        await cfg.set("runtime_key", "val")
        section = await cfg.get_section("runtime")
        assert "runtime_key" in section

    @pytest.mark.asyncio
    async def test_get_item(self) -> None:
        cfg = DeploymentConfiguration("development")
        item = await cfg.get_item("debug")
        assert item is not None
        assert item.key == "debug"

    @pytest.mark.asyncio
    async def test_get_statistics(self) -> None:
        cfg = DeploymentConfiguration("development")
        stats = await cfg.get_statistics()
        assert stats["environment"] == "development"
        assert stats["total_items"] > 0


# ─── Secrets ───────────────────────────────────────────────────────────────
from app.deployment.secrets import SecretManager


class TestSecrets:
    @pytest.mark.asyncio
    async def test_set_and_get(self) -> None:
        sm = SecretManager()
        await sm.set_secret("api_key", "secret123")
        assert await sm.get_secret("api_key") == "secret123"

    @pytest.mark.asyncio
    async def test_get_missing(self) -> None:
        sm = SecretManager()
        assert await sm.get_secret("nonexistent") is None

    @pytest.mark.asyncio
    async def test_list_secrets(self) -> None:
        sm = SecretManager()
        await sm.set_secret("a", "1")
        await sm.set_secret("b", "2")
        secrets = await sm.list_secrets()
        assert "a" in secrets
        assert "b" in secrets

    @pytest.mark.asyncio
    async def test_delete_secret(self) -> None:
        sm = SecretManager()
        await sm.set_secret("key", "val")
        assert await sm.delete_secret("key") is True
        assert await sm.get_secret("key") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self) -> None:
        sm = SecretManager()
        assert await sm.delete_secret("nope") is False

    @pytest.mark.asyncio
    async def test_validate_pass(self) -> None:
        sm = SecretManager()
        await sm.set_secret("a", "1")
        result = await sm.validate(["a"])
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_fail(self) -> None:
        sm = SecretManager()
        result = await sm.validate(["missing_key"])
        assert result["valid"] is False
        assert "missing_key" in result["missing"]

    @pytest.mark.asyncio
    async def test_get_secret_info(self) -> None:
        sm = SecretManager()
        await sm.set_secret("k", "v")
        info = await sm.get_secret_info("k")
        assert info is not None
        assert info.key == "k"

    @pytest.mark.asyncio
    async def test_cache(self) -> None:
        sm = SecretManager()
        await sm.set_secret("cached", "val")
        val = await sm.get_secret("cached")
        assert val == "val"


# ─── Health Probes ─────────────────────────────────────────────────────────
from app.deployment.health import LivenessProbe, ReadinessProbe, StartupProbe


class TestLivenessProbe:
    @pytest.mark.asyncio
    async def test_not_started(self) -> None:
        lp = LivenessProbe()
        check = await lp.check()
        assert check.status == HealthStatus.UNHEALTHY.value

    @pytest.mark.asyncio
    async def test_started(self) -> None:
        lp = LivenessProbe()
        lp.mark_started()
        check = await lp.check()
        assert check.status == HealthStatus.HEALTHY.value
        assert lp.is_alive is True


class TestStartupProbe:
    @pytest.mark.asyncio
    async def test_not_started(self) -> None:
        sp = StartupProbe()
        check = await sp.check()
        assert check.status in ("degraded", "not_started", "in_progress")

    @pytest.mark.asyncio
    async def test_start_and_complete(self) -> None:
        sp = StartupProbe()
        await sp.start()
        await sp.complete()
        check = await sp.check()
        assert check.status == HealthStatus.HEALTHY.value
        assert sp.is_complete is True

    @pytest.mark.asyncio
    async def test_timeout(self) -> None:
        sp = StartupProbe(timeout=0.0)
        await sp.start()
        check = await sp.check()
        assert check.status == HealthStatus.UNHEALTHY.value

    def test_add_check(self) -> None:
        sp = StartupProbe()
        sp.add_check("db", True, "ok")
        assert len(sp._checks) == 1


class TestReadinessProbe:
    @pytest.mark.asyncio
    async def test_ready_by_default(self) -> None:
        rp = ReadinessProbe()
        check = await rp.check()
        assert check.status == HealthStatus.HEALTHY.value

    @pytest.mark.asyncio
    async def test_not_ready(self) -> None:
        rp = ReadinessProbe()
        rp.register_check("db", False)
        check = await rp.check()
        assert check.status == HealthStatus.DEGRADED.value
        assert rp.is_ready is False

    @pytest.mark.asyncio
    async def test_ready_with_checks(self) -> None:
        rp = ReadinessProbe()
        rp.register_check("db", True)
        rp.register_check("cache", True)
        assert rp.is_ready is True

    def test_remove_check(self) -> None:
        rp = ReadinessProbe()
        rp.register_check("x", True)
        assert rp.remove_check("x") is True
        assert rp.remove_check("y") is False


# ─── Readiness Checker ─────────────────────────────────────────────────────
from app.deployment.readiness import ReadinessChecker


class TestReadinessChecker:
    @pytest.mark.asyncio
    async def test_check_readiness(self) -> None:
        rc = ReadinessChecker()
        result = await rc.check_readiness()
        assert result["ready"] is True

    @pytest.mark.asyncio
    async def test_register_check(self) -> None:
        rc = ReadinessChecker()
        rc.register_check("database", True)
        assert rc.is_ready is True

    @pytest.mark.asyncio
    async def test_not_ready(self) -> None:
        rc = ReadinessChecker()
        rc.register_check("database", False)
        assert rc.is_ready is False

    @pytest.mark.asyncio
    async def test_check_all(self) -> None:
        rc = ReadinessChecker()
        result = await rc.check_all()
        assert "startup" in result
        assert "readiness" in result
        assert "liveness" in result

    @pytest.mark.asyncio
    async def test_check_startup(self) -> None:
        rc = ReadinessChecker()
        result = await rc.check_startup()
        assert result["status"] == "ready"

    @pytest.mark.asyncio
    async def test_check_liveness(self) -> None:
        rc = ReadinessChecker()
        result = await rc.check_liveness()
        assert result["status"] == "alive"

    def test_remove_check(self) -> None:
        rc = ReadinessChecker()
        rc.register_check("db", True)
        assert rc.remove_check("db") is True
        assert rc.remove_check("missing") is False


# ─── Shutdown ──────────────────────────────────────────────────────────────
from app.deployment.shutdown import GracefulShutdown


class TestShutdown:
    @pytest.mark.asyncio
    async def test_execute_empty(self) -> None:
        gs = GracefulShutdown()
        result = await gs.execute()
        assert result["handlers_total"] == 0
        assert len(result["completed"]) == 0

    @pytest.mark.asyncio
    async def test_execute_with_handler(self) -> None:
        gs = GracefulShutdown()
        called = []

        async def handler() -> None:
            called.append(True)

        gs.register_handler("test", handler)
        result = await gs.execute()
        assert result["handlers_total"] == 1
        assert "test" in result["completed"]
        assert len(called) == 1

    @pytest.mark.asyncio
    async def test_execute_with_failing_handler(self) -> None:
        gs = GracefulShutdown()

        async def bad_handler() -> None:
            raise ValueError("boom")

        gs.register_handler("bad", bad_handler)
        result = await gs.execute()
        assert "bad" in result["failed"]

    def test_is_shutting_down(self) -> None:
        gs = GracefulShutdown()
        assert gs.is_shutting_down is False

    def test_get_status(self) -> None:
        gs = GracefulShutdown()
        status = gs.get_status()
        assert "handlers_registered" in status
        assert "timeout_seconds" in status


# ─── Diagnostics ───────────────────────────────────────────────────────────
from app.deployment.diagnostics import DeploymentDiagnostics


class TestDiagnostics:
    @pytest.mark.asyncio
    async def test_collect(self) -> None:
        diag = DeploymentDiagnostics()
        data = await diag.collect()
        assert "python" in data
        assert "platform" in data
        assert "runtime" in data

    def test_add_check(self) -> None:
        diag = DeploymentDiagnostics()
        diag.add_check("disk", True, {"usage": "50%"})
        checks = diag.get_checks()
        assert "disk" in checks
        assert checks["disk"]["passed"] is True

    def test_remove_check(self) -> None:
        diag = DeploymentDiagnostics()
        diag.add_check("x", True)
        assert diag.remove_check("x") is True
        assert diag.remove_check("y") is False

    def test_get_summary(self) -> None:
        diag = DeploymentDiagnostics()
        diag.add_check("a", True)
        diag.add_check("b", False)
        summary = diag.get_summary()
        assert summary["total_checks"] == 2
        assert summary["passed"] == 1
        assert summary["failed"] == 1


# ─── Metrics ───────────────────────────────────────────────────────────────
from app.deployment.metrics import DeploymentMetricsCollector


class TestMetrics:
    def test_record_startup(self) -> None:
        m = DeploymentMetricsCollector()
        m.record_startup(100.0)
        stats = m.get_statistics()
        assert stats["total_startups"] == 1
        assert stats["average_startup_time_ms"] == 100.0

    def test_record_shutdown(self) -> None:
        m = DeploymentMetricsCollector()
        m.record_shutdown(50.0)
        stats = m.get_statistics()
        assert stats["total_shutdowns"] == 1

    def test_record_health_check(self) -> None:
        m = DeploymentMetricsCollector()
        m.record_health_check()
        m.record_health_check()
        stats = m.get_statistics()
        assert stats["total_health_checks"] == 2

    def test_record_restart(self) -> None:
        m = DeploymentMetricsCollector()
        m.record_restart()
        stats = m.get_statistics()
        assert stats["total_restarts"] == 1

    def test_to_model(self) -> None:
        m = DeploymentMetricsCollector()
        m.record_startup(10.0)
        model = m.to_model()
        assert model.total_startups == 1

    def test_reset(self) -> None:
        m = DeploymentMetricsCollector()
        m.record_startup(10.0)
        m.record_health_check()
        m.reset()
        stats = m.get_statistics()
        assert stats["total_startups"] == 0
        assert stats["total_health_checks"] == 0

    def test_uptime(self) -> None:
        m = DeploymentMetricsCollector()
        stats = m.get_statistics()
        assert stats["uptime_seconds"] >= 0.0


# ─── Tracing ───────────────────────────────────────────────────────────────
from app.deployment.tracing import DeploymentTracer


class TestTracing:
    def test_start_and_finish_trace(self) -> None:
        t = DeploymentTracer()
        tid = t.start_trace("test")
        t.finish_trace(tid, "ok")
        trace = t.get_trace(tid)
        assert trace is not None
        assert trace["status"] == "ok"

    def test_add_and_end_span(self) -> None:
        t = DeploymentTracer()
        tid = t.start_trace("root")
        t.add_span(tid, "child1")
        t.end_span(tid, "child1")
        t.finish_trace(tid)
        trace = t.get_trace(tid)
        assert len(trace["spans"]) == 1
        assert trace["spans"][0]["duration_ms"] >= 0

    def test_get_trace_not_found(self) -> None:
        t = DeploymentTracer()
        assert t.get_trace("nonexistent") is None

    def test_get_recent_traces(self) -> None:
        t = DeploymentTracer()
        for i in range(5):
            tid = t.start_trace(f"trace_{i}")
            t.finish_trace(tid)
        traces = t.get_recent_traces(3)
        assert len(traces) == 3

    def test_get_statistics(self) -> None:
        t = DeploymentTracer()
        tid = t.start_trace("ok")
        t.finish_trace(tid, "ok")
        tid2 = t.start_trace("err")
        t.finish_trace(tid2, "error")
        stats = t.get_statistics()
        assert stats["total_traces"] == 2
        assert stats["failed"] == 1

    def test_clear(self) -> None:
        t = DeploymentTracer()
        t.start_trace("x")
        t.clear()
        assert len(t.get_recent_traces()) == 0

    def test_sliding_window(self) -> None:
        t = DeploymentTracer(max_spans=5)
        for i in range(10):
            t.start_trace(f"t{i}")
        assert len(t._spans) <= 5


# ─── Factory ───────────────────────────────────────────────────────────────
from app.deployment.factory import DeploymentFactory


class TestFactory:
    def test_create_all(self) -> None:
        components = DeploymentFactory.create_all("development")
        assert "manager" in components
        assert "lifecycle" in components
        assert "config" in components
        assert "metrics" in components
        assert "tracer" in components

    def test_create_manager(self) -> None:
        m = DeploymentFactory.create_manager("testing")
        assert m is not None

    def test_create_lifecycle(self) -> None:
        lc = DeploymentFactory.create_lifecycle()
        assert lc.state == DeployState.REGISTERED

    def test_create_configuration(self) -> None:
        cfg = DeploymentFactory.create_configuration("production")
        assert cfg.environment == DeployEnvironment.PRODUCTION

    def test_create_environment_manager(self) -> None:
        em = DeploymentFactory.create_environment_manager({"A": "1"})
        assert em is not None

    def test_create_environment_validator(self) -> None:
        v = DeploymentFactory.create_environment_validator(required=["X"])
        assert v is not None

    def test_create_secret_manager(self) -> None:
        sm = DeploymentFactory.create_secret_manager()
        assert sm is not None

    def test_create_readiness_checker(self) -> None:
        rc = DeploymentFactory.create_readiness_checker()
        assert rc is not None

    def test_create_startup_probe(self) -> None:
        sp = DeploymentFactory.create_startup_probe(timeout=30.0)
        assert sp is not None

    def test_create_readiness_probe(self) -> None:
        rp = DeploymentFactory.create_readiness_probe()
        assert rp is not None

    def test_create_liveness_probe(self) -> None:
        lp = DeploymentFactory.create_liveness_probe()
        assert lp is not None

    def test_create_shutdown(self) -> None:
        gs = DeploymentFactory.create_shutdown(timeout=10.0)
        assert gs is not None

    def test_create_diagnostics(self) -> None:
        d = DeploymentFactory.create_diagnostics()
        assert d is not None

    def test_create_metrics(self) -> None:
        m = DeploymentFactory.create_metrics()
        assert m is not None

    def test_create_tracer(self) -> None:
        t = DeploymentFactory.create_tracer()
        assert t is not None


# ─── Deployment Manager ────────────────────────────────────────────────────
from app.deployment.manager import DeploymentManager


class TestDeploymentManager:
    @pytest.mark.asyncio
    async def test_start_and_health(self) -> None:
        dm = DeploymentManager(environment="testing")
        await dm.start()
        health = await dm.health()
        assert health["startup"] is True

    @pytest.mark.asyncio
    async def test_start_and_shutdown(self) -> None:
        dm = DeploymentManager(environment="testing")
        await dm.start()
        await dm.shutdown()
        assert dm.is_running is False

    @pytest.mark.asyncio
    async def test_readiness(self) -> None:
        dm = DeploymentManager(environment="testing")
        await dm.start()
        result = await dm.readiness()
        assert "ready" in result

    @pytest.mark.asyncio
    async def test_liveness(self) -> None:
        dm = DeploymentManager(environment="testing")
        await dm.start()
        result = await dm.liveness()
        assert "status" in result

    @pytest.mark.asyncio
    async def test_environment(self) -> None:
        dm = DeploymentManager(environment="testing")
        env = await dm.environment()
        assert isinstance(env, dict)

    @pytest.mark.asyncio
    async def test_diagnostics(self) -> None:
        dm = DeploymentManager(environment="testing")
        diag = await dm.diagnostics()
        assert "python" in diag

    @pytest.mark.asyncio
    async def test_statistics(self) -> None:
        dm = DeploymentManager(environment="testing")
        stats = await dm.statistics()
        assert stats.state == DeployState.REGISTERED.value

    def test_register_readiness_check(self) -> None:
        dm = DeploymentManager()
        dm.register_readiness_check("db", True)
        assert dm._readiness.is_ready is True

    @pytest.mark.asyncio
    async def test_lifecycle_property(self) -> None:
        dm = DeploymentManager()
        assert dm.lifecycle.state == DeployState.REGISTERED

    @pytest.mark.asyncio
    async def test_configuration_property(self) -> None:
        dm = DeploymentManager(environment="production")
        assert dm.configuration.environment == DeployEnvironment.PRODUCTION


# ─── Schemas ───────────────────────────────────────────────────────────────
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


class TestSchemas:
    def test_health_response(self) -> None:
        r = DeploymentHealthResponse()
        assert r.status == "healthy"

    def test_statistics_response(self) -> None:
        r = DeploymentStatisticsResponse()
        assert r.state == "registered"

    def test_environment_response(self) -> None:
        r = EnvironmentResponse()
        assert r.count == 0

    def test_configuration_response(self) -> None:
        r = ConfigurationResponse()
        assert r.valid is True

    def test_diagnostics_response(self) -> None:
        r = DiagnosticsResponse()
        assert r.python == {}

    def test_metrics_response(self) -> None:
        r = DeploymentMetricsResponse()
        assert r.total_startups == 0

    def test_readiness_response(self) -> None:
        r = ReadinessResponse()
        assert r.ready is True

    def test_liveness_response(self) -> None:
        r = LivenessResponse()
        assert r.alive is True

    def test_startup_response(self) -> None:
        r = StartupResponse()
        assert r.completed is True


# ─── Integration ───────────────────────────────────────────────────────────
class TestIntegration:
    @pytest.mark.asyncio
    async def test_factory_full_lifecycle(self) -> None:
        components = DeploymentFactory.create_all("development")
        manager = components["manager"]
        await manager.start()
        health = await manager.health()
        assert health["startup"] is True
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_environment_validation_integration(self) -> None:
        v = EnvironmentValidator(required=["APP_NAME", "APP_ENV"])
        result = v.validate({"APP_NAME": "nova", "APP_ENV": "test"})
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_secrets_and_config_integration(self) -> None:
        sm = SecretManager()
        cfg = DeploymentConfiguration("development")
        await sm.set_secret("db_password", "s3cret")
        await cfg.set("db_host", "localhost")
        assert await sm.get_secret("db_password") == "s3cret"
        assert await cfg.get("db_host") == "localhost"

    @pytest.mark.asyncio
    async def test_readiness_with_checks(self) -> None:
        rc = ReadinessChecker()
        rc.register_check("database", True)
        rc.register_check("cache", True)
        result = await rc.check_readiness()
        assert result["ready"] is True

    @pytest.mark.asyncio
    async def test_metrics_after_lifecycle(self) -> None:
        m = DeploymentMetricsCollector()
        m.record_startup(100.0)
        m.record_health_check()
        m.record_shutdown(50.0)
        stats = m.get_statistics()
        assert stats["total_startups"] == 1
        assert stats["total_shutdowns"] == 1
        assert stats["total_health_checks"] == 1

    @pytest.mark.asyncio
    async def test_tracing_lifecycle(self) -> None:
        t = DeploymentTracer()
        tid = t.start_trace("lifecycle")
        t.add_span(tid, "init")
        t.end_span(tid, "init")
        t.finish_trace(tid, "ok")
        stats = t.get_statistics()
        assert stats["total_traces"] == 1
        assert stats["completed"] == 1

    @pytest.mark.asyncio
    async def test_diagnostics_integration(self) -> None:
        d = DeploymentDiagnostics()
        d.add_check("python", True, {"version": "3.13"})
        d.add_check("platform", True)
        summary = d.get_summary()
        assert summary["passed"] == 2

    @pytest.mark.asyncio
    async def test_lifecycle_shutdown_handlers(self) -> None:
        gs = GracefulShutdown(timeout=5.0)
        steps = []

        async def step1() -> None:
            steps.append("step1")

        async def step2() -> None:
            steps.append("step2")

        gs.register_handler("s1", step1)
        gs.register_handler("s2", step2)
        result = await gs.execute()
        assert steps == ["step1", "step2"]
        assert result["handlers_total"] == 2


# ─── Edge Cases ────────────────────────────────────────────────────────────
class TestEdgeCases:
    def test_lifecycle_cannot_go_backwards(self) -> None:
        lc = DeploymentLifecycle()
        lc.transition(DeployState.INITIALIZING)
        assert lc.transition(DeployState.REGISTERED) is False

    def test_config_empty_environment(self) -> None:
        cfg = DeploymentConfiguration("development")
        assert cfg.environment == DeployEnvironment.DEVELOPMENT

    def test_validator_no_requirements(self) -> None:
        v = EnvironmentValidator(required=[], optional={})
        result = v.validate({})
        assert result["valid"] is True

    def test_secret_manager_no_cache(self) -> None:
        sm = SecretManager()
        assert sm._cache == {}

    def test_metrics_sliding_window(self) -> None:
        m = DeploymentMetricsCollector()
        for _ in range(1200):
            m.record_startup(1.0)
        stats = m.get_statistics()
        assert stats["total_startups"] == 1200

    def test_tracer_empty_statistics(self) -> None:
        t = DeploymentTracer()
        stats = t.get_statistics()
        assert stats["total_traces"] == 0
        assert stats["average_duration_ms"] == 0.0

    def test_shutdown_no_handlers(self) -> None:
        gs = GracefulShutdown()
        assert gs.get_status()["handlers_registered"] == 0

    def test_readiness_empty_checks(self) -> None:
        rp = ReadinessProbe()
        assert rp.is_ready is True

    def test_diagnostics_no_checks(self) -> None:
        d = DeploymentDiagnostics()
        summary = d.get_summary()
        assert summary["total_checks"] == 0

    def test_environment_manager_empty(self) -> None:
        em = EnvironmentManager(env={})
        assert em._env == {}
