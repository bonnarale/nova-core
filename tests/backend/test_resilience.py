"""Tests for the Resilience subsystem (Ch34)."""

from __future__ import annotations

import asyncio
import threading
from typing import Any

import pytest

from app.resilience.enums import (
    CircuitState,
    DegradationLevel,
    FallbackStrategy,
    HealthStatus,
    RecoveryPolicy,
    ResilienceState,
    RetryStrategy,
)
from app.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerManager
from app.resilience.retry import RetryManager, RetryPolicy
from app.resilience.timeout import TimeoutManager
from app.resilience.fallback import FallbackManager
from app.resilience.bulkhead import BulkheadManager, Bulkhead
from app.resilience.backpressure import BackpressureManager
from app.resilience.rate_control import RateController
from app.resilience.health_guard import HealthGuard
from app.resilience.watchdog import Watchdog
from app.resilience.recovery import RecoveryManager
from app.resilience.failover import FailoverManager
from app.resilience.degradation import DegradationManager
from app.resilience.resilience_policy import ResiliencePolicyManager, ResiliencePolicy
from app.resilience.diagnostics import ResilienceDiagnostics
from app.resilience.lifecycle import ResilienceLifecycle
from app.resilience.metrics import ResilienceMetricsCollector
from app.resilience.tracing import ResilienceTracer
from app.resilience.engine import ResilienceEngine
from app.resilience.factory import ResilienceFactory


# ===== Enums =====

class TestEnums:
    def test_circuit_state_values(self) -> None:
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.HALF_OPEN.value == "half_open"
        assert CircuitState.OPEN.value == "open"

    def test_retry_strategy(self) -> None:
        assert RetryStrategy.EXPONENTIAL.value == "exponential"
        assert RetryStrategy.FIXED.value == "fixed"
        assert RetryStrategy.LINEAR.value == "linear"

    def test_fallback_strategy(self) -> None:
        assert FallbackStrategy.DEFAULT.value == "default"
        assert FallbackStrategy.CACHE.value == "cache"
        assert FallbackStrategy.STALE.value == "stale"
        assert FallbackStrategy.SKIP.value == "skip"
        assert FallbackStrategy.DEGRADED.value == "degraded"

    def test_recovery_policy(self) -> None:
        assert RecoveryPolicy.RESTART.value == "restart"
        assert RecoveryPolicy.RESUME.value == "resume"
        assert RecoveryPolicy.CHECKPOINT.value == "checkpoint"
        assert RecoveryPolicy.ROLLBACK.value == "rollback"
        assert RecoveryPolicy.SKIP.value == "skip"

    def test_health_status(self) -> None:
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_degradation_level(self) -> None:
        assert DegradationLevel.NONE.value == "none"
        assert DegradationLevel.PARTIAL.value == "partial"
        assert DegradationLevel.SEVERE.value == "severe"
        assert DegradationLevel.EMERGENCY.value == "emergency"

    def test_resilience_state(self) -> None:
        assert ResilienceState.REGISTERED.value == "registered"
        assert ResilienceState.INITIALIZED.value == "initialized"
        assert ResilienceState.READY.value == "ready"
        assert ResilienceState.RUNNING.value == "running"
        assert ResilienceState.DEGRADED.value == "degraded"
        assert ResilienceState.RECOVERING.value == "recovering"
        assert ResilienceState.FAILED.value == "failed"
        assert ResilienceState.SHUTDOWN.value == "shutdown"


# ===== Circuit Breaker =====

class TestCircuitBreaker:
    def test_initial_state(self) -> None:
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=10)
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0

    def test_records_failure(self) -> None:
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=10)
        cb.record_failure()
        assert cb._failure_count == 1

    def test_trips_at_threshold(self) -> None:
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=10)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_resets_count(self) -> None:
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=10)
        cb.record_failure()
        cb.record_success()
        assert cb._failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_allow_request_when_closed(self) -> None:
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=10)
        assert cb.allow_request() is True

    def test_deny_request_when_open(self) -> None:
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=100)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    def test_get_stats(self) -> None:
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=10)
        stats = cb.get_stats()
        assert stats["name"] == "test"
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 0
        assert stats["failure_threshold"] == 3

    def test_concurrent_failures(self) -> None:
        cb = CircuitBreaker("test", failure_threshold=10, recovery_timeout=10)

        def fail() -> None:
            for _ in range(5):
                cb.record_failure()

        threads = [threading.Thread(target=fail) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert cb._failure_count > 0


class TestCircuitBreakerManager:
    def test_get_or_create(self) -> None:
        mgr = CircuitBreakerManager()
        cb = mgr.get_or_create("svc1", failure_threshold=5, recovery_timeout=30)
        assert cb.name == "svc1"
        assert cb._failure_threshold == 5

    def test_same_instance(self) -> None:
        mgr = CircuitBreakerManager()
        cb1 = mgr.get_or_create("svc1", failure_threshold=5, recovery_timeout=30)
        cb2 = mgr.get_or_create("svc1", failure_threshold=5, recovery_timeout=30)
        assert cb1 is cb2

    def test_get(self) -> None:
        mgr = CircuitBreakerManager()
        mgr.get_or_create("svc1")
        assert mgr.get("svc1") is not None
        assert mgr.get("nonexistent") is None

    def test_reset(self) -> None:
        mgr = CircuitBreakerManager()
        cb = mgr.get_or_create("svc1", failure_threshold=1, recovery_timeout=100)
        cb.record_failure()
        assert cb._failure_count == 1
        mgr.reset("svc1")
        assert cb._failure_count == 0

    def test_reset_all(self) -> None:
        mgr = CircuitBreakerManager()
        cb1 = mgr.get_or_create("svc1", failure_threshold=1)
        cb2 = mgr.get_or_create("svc2", failure_threshold=1)
        cb1.record_failure()
        cb2.record_failure()
        mgr.reset_all()
        assert cb1._failure_count == 0
        assert cb2._failure_count == 0

    def test_get_summary(self) -> None:
        mgr = CircuitBreakerManager()
        mgr.get_or_create("svc1")
        mgr.get_or_create("svc2")
        summary = mgr.get_summary()
        assert summary["total"] == 2
        assert "svc1" in summary["states"]
        assert summary["states"]["svc1"] == "closed"

    def test_get_all(self) -> None:
        mgr = CircuitBreakerManager()
        mgr.get_or_create("a")
        mgr.get_or_create("b")
        assert len(mgr.get_all()) == 2


# ===== Retry =====

class TestRetryPolicy:
    def test_default_values(self) -> None:
        p = RetryPolicy()
        assert p.name == "default"
        assert p.max_retries == 3
        assert p.strategy == RetryStrategy.EXPONENTIAL

    def test_custom_values(self) -> None:
        p = RetryPolicy(name="custom", max_retries=5, strategy=RetryStrategy.FIXED)
        assert p.name == "custom"
        assert p.max_retries == 5
        assert p.strategy == RetryStrategy.FIXED

    def test_get_delay(self) -> None:
        p = RetryPolicy(base_delay=1.0, strategy=RetryStrategy.FIXED, jitter=False)
        d = p.get_delay(0)
        assert d == 1.0

    def test_to_dict(self) -> None:
        p = RetryPolicy(name="x")
        d = p.to_dict()
        assert d["name"] == "x"
        assert "strategy" in d


class TestRetryManager:
    def test_add_policy_and_get(self) -> None:
        mgr = RetryManager()
        p = RetryPolicy(name="svc1", max_retries=5)
        mgr.add_policy(p)
        assert mgr.get_policy("svc1") is p
        assert mgr.get_policy("nonexistent") is not None

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        mgr = RetryManager()

        async def ok() -> str:
            return "ok"

        result = await mgr.execute(ok)
        assert result == "ok"
        assert mgr.get_stats()["total"] == 1

    @pytest.mark.asyncio
    async def test_execute_retry_then_success(self) -> None:
        mgr = RetryManager()
        mgr.add_policy(RetryPolicy(name="svc1", max_retries=5))
        attempts = 0

        async def flaky() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ValueError("fail")
            return "ok"

        result = await mgr.execute(flaky, policy_name="svc1")
        assert result == "ok"
        assert mgr.get_stats()["by_policy"]["svc1"]["success"] >= 1

    @pytest.mark.asyncio
    async def test_execute_all_fail(self) -> None:
        mgr = RetryManager()

        async def fail() -> None:
            raise ValueError("always")

        with pytest.raises(ValueError, match="always"):
            await mgr.execute(fail, policy_name="svc1")

    def test_stats(self) -> None:
        mgr = RetryManager()
        stats = mgr.get_stats()
        assert "total" in stats
        assert "by_policy" in stats
        assert "success_rate" in stats

    def test_reset_stats(self) -> None:
        mgr = RetryManager()
        mgr.reset_stats()
        assert mgr.get_stats()["total"] == 0


# ===== Timeout =====

class TestTimeoutManager:
    @pytest.mark.asyncio
    async def test_execute_within_timeout(self) -> None:
        mgr = TimeoutManager()

        async def ok() -> str:
            return "ok"

        result = await mgr.execute(ok, operation="svc1", timeout=10)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_execute_timeout(self) -> None:
        mgr = TimeoutManager()

        async def slow() -> None:
            await asyncio.sleep(100)

        with pytest.raises(asyncio.TimeoutError):
            await mgr.execute(slow, operation="svc1", timeout=0.01)

    def test_set_and_get_timeout(self) -> None:
        mgr = TimeoutManager()
        mgr.set_timeout("svc1", 5.0)
        assert mgr.get_timeout("svc1") == 5.0

    def test_get_timeout_default(self) -> None:
        mgr = TimeoutManager()
        assert mgr.get_timeout("unknown") == 30.0

    def test_get_events(self) -> None:
        mgr = TimeoutManager()
        assert mgr.get_events() == []

    def test_get_all_timeouts(self) -> None:
        mgr = TimeoutManager()
        t = mgr.get_all_timeouts()
        assert "api_request" in t

    def test_reset(self) -> None:
        mgr = TimeoutManager()
        mgr.set_timeout("x", 999.0)
        mgr.reset()
        assert mgr.get_timeout("x") == 30.0


# ===== Fallback =====

class TestFallbackManager:
    @pytest.mark.asyncio
    async def test_execute_with_fallback(self) -> None:
        mgr = FallbackManager()

        async def fail() -> None:
            raise ValueError("boom")

        def default_fallback(*args: Any, **kwargs: Any) -> str:
            return "fallback_result"

        mgr.register_handler("svc1", default_fallback)
        result = await mgr.execute("svc1", fail)
        assert result == "fallback_result"

    @pytest.mark.asyncio
    async def test_execute_skip_strategy(self) -> None:
        mgr = FallbackManager()

        async def fail() -> None:
            raise ValueError("boom")

        mgr.set_strategy("svc_skip", FallbackStrategy.SKIP)
        result = await mgr.execute("svc_skip", fail)
        assert result is None

    @pytest.mark.asyncio
    async def test_execute_default_strategy(self) -> None:
        mgr = FallbackManager()

        async def fail() -> None:
            raise ValueError("boom")

        result = await mgr.execute("svc_def", fail)
        assert result is not None
        assert result["fallback"] is True

    def test_set_strategy_and_get(self) -> None:
        mgr = FallbackManager()
        mgr.set_strategy("svc1", FallbackStrategy.CACHE)
        assert mgr.get_strategy("svc1") == FallbackStrategy.CACHE

    def test_get_strategy_default(self) -> None:
        mgr = FallbackManager()
        assert mgr.get_strategy("nonexistent") == FallbackStrategy.DEFAULT

    def test_get_invocations(self) -> None:
        mgr = FallbackManager()
        inv = mgr.get_invocations()
        assert isinstance(inv, dict)

    def test_get_stats(self) -> None:
        mgr = FallbackManager()
        stats = mgr.get_stats()
        assert "strategies" in stats
        assert "total_invocations" in stats


# ===== Bulkhead =====

class TestBulkhead:
    def test_acquire_release(self) -> None:
        bh = Bulkhead("test", max_concurrent=3)
        assert bh.acquire() is True
        bh.release()

    def test_max_concurrent(self) -> None:
        bh = Bulkhead("test", max_concurrent=2)
        assert bh.acquire() is True
        assert bh.acquire() is True
        assert bh.acquire() is False
        bh.release()
        assert bh.acquire() is True

    def test_available(self) -> None:
        bh = Bulkhead("test", max_concurrent=5)
        assert bh.available == 5
        bh.acquire()
        assert bh.available == 4

    def test_get_stats(self) -> None:
        bh = Bulkhead("test", max_concurrent=5)
        stats = bh.get_stats()
        assert stats["name"] == "test"
        assert stats["max_concurrent"] == 5
        assert stats["current"] == 0


class TestBulkheadManager:
    def test_get_or_create(self) -> None:
        mgr = BulkheadManager()
        bh = mgr.get_or_create("svc1", max_concurrent=10)
        assert bh.max_concurrent == 10

    def test_get(self) -> None:
        mgr = BulkheadManager()
        mgr.get_or_create("svc1", max_concurrent=10)
        assert mgr.get("svc1") is not None
        assert mgr.get("nonexistent") is None

    def test_get_all(self) -> None:
        mgr = BulkheadManager()
        all_bh = mgr.get_all()
        assert len(all_bh) >= 5

    def test_get_summary(self) -> None:
        mgr = BulkheadManager()
        summary = mgr.get_summary()
        assert isinstance(summary, dict)

    def test_default_bulkheads(self) -> None:
        mgr = BulkheadManager()
        agents = mgr.get("agents")
        assert agents is not None
        assert agents.max_concurrent == 20


# ===== Backpressure =====

class TestBackpressureManager:
    def test_default_state(self) -> None:
        mgr = BackpressureManager()
        assert mgr.can_accept() is True

    def test_accept_and_release(self) -> None:
        mgr = BackpressureManager(max_queue_size=3)
        assert mgr.accept() is True
        assert mgr.accept() is True
        assert mgr.accept() is True
        assert mgr.accept() is False
        mgr.release()
        assert mgr.accept() is True

    def test_is_throttled(self) -> None:
        mgr = BackpressureManager(max_queue_size=10)
        for _ in range(9):
            mgr.accept()
        assert mgr.is_throttled() is True

    def test_get_stats(self) -> None:
        mgr = BackpressureManager()
        stats = mgr.get_stats()
        assert "current_queue" in stats
        assert "max_queue_size" in stats
        assert "total_accepted" in stats

    def test_reset(self) -> None:
        mgr = BackpressureManager(max_queue_size=3)
        mgr.accept()
        mgr.accept()
        mgr.reset()
        assert mgr._current_queue == 0

    def test_record_throttle(self) -> None:
        mgr = BackpressureManager()
        mgr.record_throttle()
        stats = mgr.get_stats()
        assert stats["total_throttled"] == 1


# ===== Rate Control =====

class TestRateController:
    def test_allow(self) -> None:
        ctrl = RateController()
        assert ctrl.allow() is True

    def test_burst_limit(self) -> None:
        ctrl = RateController(rate=1.0, burst=2)
        assert ctrl.allow() is True
        assert ctrl.allow() is True
        assert ctrl.allow() is False

    def test_get_stats(self) -> None:
        ctrl = RateController()
        stats = ctrl.get_stats()
        assert "rate" in stats
        assert "burst" in stats
        assert "total_allowed" in stats
        assert "total_denied" in stats

    def test_reset(self) -> None:
        ctrl = RateController(rate=1.0, burst=1)
        ctrl.allow()
        ctrl.reset()
        assert ctrl._tokens == 1.0


# ===== Health Guard =====

class TestHealthGuard:
    def test_register_check(self) -> None:
        hg = HealthGuard()
        hg.register_check("svc1")
        assert "svc1" in hg._checks

    def test_run_check_healthy(self) -> None:
        hg = HealthGuard()
        hg.register_check("svc1")
        status = hg.run_check("svc1", healthy=True)
        assert status == HealthStatus.HEALTHY.value

    def test_run_check_unhealthy(self) -> None:
        hg = HealthGuard()
        hg.register_check("svc1")
        status = hg.run_check("svc1", healthy=False, message="down")
        assert status == HealthStatus.UNHEALTHY.value

    def test_get_status(self) -> None:
        hg = HealthGuard()
        hg.register_check("svc1")
        hg.run_check("svc1", healthy=True)
        assert hg.get_status("svc1") == HealthStatus.HEALTHY.value

    def test_get_status_unknown(self) -> None:
        hg = HealthGuard()
        assert hg.get_status("nonexistent") == HealthStatus.UNKNOWN.value

    def test_get_all_status(self) -> None:
        hg = HealthGuard()
        hg.register_check("a")
        hg.register_check("b")
        hg.run_check("a", healthy=True)
        hg.run_check("b", healthy=False)
        all_s = hg.get_all_status()
        assert len(all_s) == 2

    def test_is_healthy(self) -> None:
        hg = HealthGuard()
        assert hg.is_healthy() is True
        hg.register_check("svc1")
        hg.run_check("svc1", healthy=True)
        assert hg.is_healthy() is True

    def test_is_healthy_with_unhealthy(self) -> None:
        hg = HealthGuard()
        hg.register_check("svc1")
        hg.run_check("svc1", healthy=False)
        assert hg.is_healthy() is False

    def test_unregister_check(self) -> None:
        hg = HealthGuard()
        hg.register_check("svc1")
        hg.unregister_check("svc1")
        assert hg.get_status("svc1") == HealthStatus.UNKNOWN.value

    def test_get_interventions(self) -> None:
        hg = HealthGuard()
        hg.register_check("svc1")
        hg.run_check("svc1", healthy=False, message="down")
        interventions = hg.get_interventions()
        assert len(interventions) == 1

    def test_get_summary(self) -> None:
        hg = HealthGuard()
        hg.register_check("a")
        hg.run_check("a", healthy=True)
        summary = hg.get_summary()
        assert summary["total_checks"] == 1
        assert summary["healthy"] == 1


# ===== Watchdog =====

class TestWatchdog:
    def test_register(self) -> None:
        wd = Watchdog()
        wd.register("svc1", category="task")
        assert "svc1" in wd.get_monitored()

    def test_heartbeat(self) -> None:
        wd = Watchdog()
        wd.register("svc1")
        wd.heartbeat("svc1")
        monitored = wd.get_monitored()
        assert "svc1" in monitored

    def test_unregister(self) -> None:
        wd = Watchdog()
        wd.register("svc1")
        wd.unregister("svc1")
        assert "svc1" not in wd.get_monitored()

    def test_check_stalled(self) -> None:
        wd = Watchdog(stall_threshold=0.01)
        wd.register("svc1")
        import time
        time.sleep(0.02)
        stalled = wd.check_stalled()
        assert "svc1" in stalled

    def test_mark_resolved(self) -> None:
        wd = Watchdog(stall_threshold=0.01)
        wd.register("svc1")
        import time
        time.sleep(0.02)
        wd.check_stalled()
        wd.mark_resolved("svc1")
        monitored = wd.get_monitored()
        assert monitored["svc1"]["status"] == "active"

    def test_get_interventions(self) -> None:
        wd = Watchdog(stall_threshold=0.01)
        wd.register("svc1")
        import time
        time.sleep(0.02)
        wd.check_stalled()
        interventions = wd.get_interventions()
        assert len(interventions) == 1

    def test_get_summary(self) -> None:
        wd = Watchdog()
        wd.register("a")
        wd.register("b")
        summary = wd.get_summary()
        assert summary["total_monitored"] == 2
        assert summary["active"] == 2


# ===== Recovery =====

class TestRecoveryManager:
    @pytest.mark.asyncio
    async def test_recover_default(self) -> None:
        mgr = RecoveryManager()
        success = await mgr.recover("svc1")
        assert success is True

    @pytest.mark.asyncio
    async def test_recover_with_policy(self) -> None:
        mgr = RecoveryManager()
        mgr.set_policy("svc1", RecoveryPolicy.RESUME)
        success = await mgr.recover("svc1")
        assert success is True

    @pytest.mark.asyncio
    async def test_recover_checkpoint(self) -> None:
        mgr = RecoveryManager()
        mgr.set_policy("svc1", RecoveryPolicy.CHECKPOINT)
        success = await mgr.recover("svc1")
        assert success is False
        mgr.save_checkpoint("svc1", {"step": 5})
        success = await mgr.recover("svc1")
        assert success is True

    def test_get_policy(self) -> None:
        mgr = RecoveryManager()
        assert mgr.get_policy("svc1") == RecoveryPolicy.RESTART
        mgr.set_policy("svc1", RecoveryPolicy.ROLLBACK)
        assert mgr.get_policy("svc1") == RecoveryPolicy.ROLLBACK

    def test_save_and_get_checkpoint(self) -> None:
        mgr = RecoveryManager()
        mgr.save_checkpoint("svc1", {"x": 1})
        cp = mgr.get_checkpoint("svc1")
        assert cp is not None
        assert cp["x"] == 1

    def test_get_checkpoint_none(self) -> None:
        mgr = RecoveryManager()
        assert mgr.get_checkpoint("nonexistent") is None

    def test_get_history(self) -> None:
        mgr = RecoveryManager()
        assert mgr.get_history() == []

    def test_get_stats(self) -> None:
        mgr = RecoveryManager()
        stats = mgr.get_stats()
        assert "total" in stats
        assert "success_rate" in stats

    def test_reset(self) -> None:
        mgr = RecoveryManager()
        mgr.save_checkpoint("svc1", {"x": 1})
        mgr.reset()
        assert mgr.get_checkpoint("svc1") is None


# ===== Failover =====

class TestFailoverManager:
    def test_register_chain(self) -> None:
        mgr = FailoverManager()
        mgr.register_chain("svc1", ["primary", "backup1", "backup2"])
        assert mgr.get_current("svc1") == "primary"

    @pytest.mark.asyncio
    async def test_failover(self) -> None:
        mgr = FailoverManager()
        mgr.register_chain("svc1", ["primary", "backup1"])
        result = await mgr.failover("svc1", reason="primary down")
        assert result == "backup1"
        assert mgr.get_current("svc1") == "backup1"

    @pytest.mark.asyncio
    async def test_failover_no_next(self) -> None:
        mgr = FailoverManager()
        mgr.register_chain("svc1", ["only_one"])
        result = await mgr.failover("svc1")
        assert result is None

    @pytest.mark.asyncio
    async def test_failover_unknown(self) -> None:
        mgr = FailoverManager()
        result = await mgr.failover("unknown")
        assert result is None

    @pytest.mark.asyncio
    async def test_reset(self) -> None:
        mgr = FailoverManager()
        mgr.register_chain("svc1", ["primary", "backup"])
        await mgr.failover("svc1")
        mgr.reset("svc1")
        assert mgr.get_current("svc1") == "primary"

    def test_reset_all(self) -> None:
        mgr = FailoverManager()
        mgr.register_chain("a", ["p", "b"])
        mgr.register_chain("b", ["p2", "b2"])
        mgr.reset_all()
        assert mgr.get_current("a") == "p"
        assert mgr.get_current("b") == "p2"

    def test_get_events(self) -> None:
        mgr = FailoverManager()
        assert mgr.get_events() == []

    def test_get_stats(self) -> None:
        mgr = FailoverManager()
        stats = mgr.get_stats()
        assert "total_chains" in stats
        assert "total_failovers" in stats


# ===== Degradation =====

class TestDegradationManager:
    def test_initial_level(self) -> None:
        mgr = DegradationManager()
        assert mgr.get_level("svc1") == DegradationLevel.NONE

    def test_set_level(self) -> None:
        mgr = DegradationManager()
        mgr.set_level("svc1", DegradationLevel.SEVERE)
        assert mgr.get_level("svc1") == DegradationLevel.SEVERE

    def test_get_degraded_subsystems(self) -> None:
        mgr = DegradationManager()
        mgr.set_level("svc1", DegradationLevel.SEVERE)
        degraded = mgr.get_degraded_subsystems()
        assert "svc1" in degraded

    def test_get_degraded_none(self) -> None:
        mgr = DegradationManager()
        assert mgr.get_degraded_subsystems() == []

    def test_disable_enable_feature(self) -> None:
        mgr = DegradationManager()
        mgr.disable_feature("svc1", "feature_a")
        assert mgr.is_feature_enabled("svc1", "feature_a") is False
        mgr.enable_feature("svc1", "feature_a")
        assert mgr.is_feature_enabled("svc1", "feature_a") is True

    def test_feature_enabled_default(self) -> None:
        mgr = DegradationManager()
        assert mgr.is_feature_enabled("svc1", "unknown_feature") is True

    def test_get_stats(self) -> None:
        mgr = DegradationManager()
        mgr.set_level("svc1", DegradationLevel.PARTIAL)
        stats = mgr.get_stats()
        assert "levels" in stats
        assert "degraded_count" in stats
        assert stats["degraded_count"] == 1


# ===== Policies =====

class TestResiliencePolicy:
    def test_defaults(self) -> None:
        p = ResiliencePolicy()
        assert p.name == "default"
        assert p.circuit_breaker_threshold == 5
        assert p.circuit_breaker_timeout == 30.0
        assert p.max_retries == 3
        assert p.timeout == 30.0

    def test_custom(self) -> None:
        p = ResiliencePolicy(name="svc1", circuit_breaker_threshold=10, timeout=60.0)
        assert p.name == "svc1"
        assert p.circuit_breaker_threshold == 10
        assert p.timeout == 60.0

    def test_to_dict(self) -> None:
        p = ResiliencePolicy(name="test")
        d = p.to_dict()
        assert d["name"] == "test"
        assert "retry_strategy" in d
        assert "fallback_strategy" in d


class TestResiliencePolicyManager:
    def test_get(self) -> None:
        mgr = ResiliencePolicyManager()
        p = mgr.get("svc1")
        assert p is not None
        assert p.name == "svc1"

    def test_set(self) -> None:
        mgr = ResiliencePolicyManager()
        p = ResiliencePolicy(name="custom", circuit_breaker_threshold=99)
        mgr.set(p)
        assert mgr.get("custom").circuit_breaker_threshold == 99

    def test_get_all(self) -> None:
        mgr = ResiliencePolicyManager()
        all_p = mgr.get_all()
        assert len(all_p) >= 20
        assert "cognitive_engine" in all_p
        assert "memory_system" in all_p

    def test_get_all_as_dicts(self) -> None:
        mgr = ResiliencePolicyManager()
        d = mgr.get_all_as_dicts()
        assert isinstance(d, dict)
        first_key = next(iter(d))
        assert "circuit_breaker_threshold" in d[first_key]


# ===== Diagnostics =====

class TestResilienceDiagnostics:
    def test_generate(self) -> None:
        diag = ResilienceDiagnostics()
        report = diag.generate()
        assert "circuit_breakers" in report
        assert "retry_stats" in report

    def test_generate_with_data(self) -> None:
        diag = ResilienceDiagnostics()
        report = diag.generate(
            circuit_breakers={"open": 1},
            retry_stats={"total": 10, "failure": 8},
            degraded_services=["svc1"],
        )
        assert report["degraded_services"] == ["svc1"]

    def test_get_reports(self) -> None:
        diag = ResilienceDiagnostics()
        diag.generate()
        reports = diag.get_reports()
        assert len(reports) == 1

    def test_get_reports_limit(self) -> None:
        diag = ResilienceDiagnostics()
        for _ in range(10):
            diag.generate()
        reports = diag.get_reports(limit=3)
        assert len(reports) == 3

    def test_recommendations_open_breakers(self) -> None:
        diag = ResilienceDiagnostics()
        report = diag.generate(circuit_breakers={"open": 2})
        recs = diag.get_recommendations(report)
        assert any(r["severity"] == "critical" for r in recs)

    def test_recommendations_high_retry_failures(self) -> None:
        diag = ResilienceDiagnostics()
        report = diag.generate(retry_stats={"total": 100, "failure": 60})
        recs = diag.get_recommendations(report)
        assert any(r["severity"] == "high" and "retry" in r["title"].lower() for r in recs)

    def test_recommendations_many_degraded(self) -> None:
        diag = ResilienceDiagnostics()
        report = diag.generate(degraded_services=["a", "b", "c", "d"])
        recs = diag.get_recommendations(report)
        assert any("degraded" in r["title"].lower() for r in recs)

    def test_recommendations_none(self) -> None:
        diag = ResilienceDiagnostics()
        report = diag.generate()
        recs = diag.get_recommendations(report)
        assert recs == []


# ===== Lifecycle =====

class TestResilienceLifecycle:
    def test_initial_state(self) -> None:
        lc = ResilienceLifecycle()
        assert lc.state == ResilienceState.REGISTERED

    def test_transition(self) -> None:
        lc = ResilienceLifecycle()
        assert lc.transition(ResilienceState.INITIALIZED, "init") is True
        assert lc.state == ResilienceState.INITIALIZED

    def test_invalid_transition(self) -> None:
        lc = ResilienceLifecycle()
        assert lc.transition(ResilienceState.RUNNING, "skip") is False

    def test_full_lifecycle(self) -> None:
        lc = ResilienceLifecycle()
        assert lc.transition(ResilienceState.INITIALIZED) is True
        assert lc.transition(ResilienceState.READY) is True
        assert lc.transition(ResilienceState.RUNNING) is True
        assert lc.state == ResilienceState.RUNNING

    def test_degraded_and_recover(self) -> None:
        lc = ResilienceLifecycle()
        lc.transition(ResilienceState.INITIALIZED)
        lc.transition(ResilienceState.READY)
        lc.transition(ResilienceState.RUNNING)
        lc.transition(ResilienceState.DEGRADED)
        assert lc.state == ResilienceState.DEGRADED
        lc.transition(ResilienceState.RUNNING)
        assert lc.state == ResilienceState.RUNNING

    def test_is_running(self) -> None:
        lc = ResilienceLifecycle()
        assert lc.is_running() is False
        lc.transition(ResilienceState.INITIALIZED)
        lc.transition(ResilienceState.READY)
        lc.transition(ResilienceState.RUNNING)
        assert lc.is_running() is True

    def test_get_status(self) -> None:
        lc = ResilienceLifecycle()
        status = lc.get_status()
        assert "state" in status
        assert "uptime_seconds" in status
        assert "transitions" in status

    def test_get_history(self) -> None:
        lc = ResilienceLifecycle()
        lc.transition(ResilienceState.INITIALIZED, "init")
        history = lc.get_history()
        assert len(history) == 1
        assert history[0]["from"] == "registered"
        assert history[0]["to"] == "initialized"

    def test_shutdown_terminal(self) -> None:
        lc = ResilienceLifecycle()
        lc.transition(ResilienceState.INITIALIZED)
        lc.transition(ResilienceState.READY)
        lc.transition(ResilienceState.RUNNING)
        lc.transition(ResilienceState.SHUTDOWN)
        assert lc.state == ResilienceState.SHUTDOWN
        assert lc.transition(ResilienceState.RUNNING) is False


# ===== Metrics =====

class TestResilienceMetricsCollector:
    def test_start(self) -> None:
        mc = ResilienceMetricsCollector()
        mc.start()
        s = mc.snapshot()
        assert s.retries == 0

    def test_record_retry(self) -> None:
        mc = ResilienceMetricsCollector()
        mc.start()
        mc.record_retry()
        mc.record_retry()
        s = mc.snapshot()
        assert s.retries == 2

    def test_record_all(self) -> None:
        mc = ResilienceMetricsCollector()
        mc.start()
        mc.record_circuit_breaker_trip()
        mc.record_failover()
        mc.record_recovery()
        mc.record_timeout()
        mc.record_degraded()
        mc.record_watchdog_intervention()
        s = mc.snapshot()
        assert s.circuit_breaker_trips == 1
        assert s.failovers == 1
        assert s.recoveries == 1
        assert s.timeouts == 1
        assert s.degraded_operations == 1
        assert s.watchdog_interventions == 1

    def test_reset(self) -> None:
        mc = ResilienceMetricsCollector()
        mc.start()
        mc.record_retry()
        mc.reset()
        s = mc.snapshot()
        assert s.retries == 0

    def test_to_dict(self) -> None:
        mc = ResilienceMetricsCollector()
        mc.start()
        s = mc.snapshot()
        d = s.to_dict()
        assert "retries" in d
        assert "uptime_seconds" in d
        assert "failovers" in d


# ===== Tracing =====

class TestResilienceTracer:
    def test_start_and_finish(self) -> None:
        tracer = ResilienceTracer()
        tid = tracer.start_trace("op1")
        assert len(tid) > 0
        assert tracer.count() == 1
        tracer.finish_trace(tid, "completed")
        traces = tracer.get_traces()
        assert traces[0]["status"] == "completed"
        assert traces[0]["duration_ms"] is not None

    def test_finish_with_error(self) -> None:
        tracer = ResilienceTracer()
        tid = tracer.start_trace("op1")
        tracer.finish_trace(tid, "error", "something broke")
        t = tracer.get_trace(tid)
        assert t is not None
        assert t["status"] == "error"
        assert t["error"] == "something broke"

    def test_get_trace(self) -> None:
        tracer = ResilienceTracer()
        tid = tracer.start_trace("op1")
        t = tracer.get_trace(tid)
        assert t is not None
        assert t["trace_id"] == tid

    def test_get_trace_not_found(self) -> None:
        tracer = ResilienceTracer()
        assert tracer.get_trace("nope") is None

    def test_max_traces(self) -> None:
        tracer = ResilienceTracer(max_traces=5)
        for i in range(10):
            tracer.start_trace(f"op{i}")
        assert tracer.count() == 5

    def test_clear(self) -> None:
        tracer = ResilienceTracer()
        tracer.start_trace("op1")
        tracer.clear()
        assert tracer.count() == 0

    def test_with_metadata(self) -> None:
        tracer = ResilienceTracer()
        tid = tracer.start_trace("op1", metadata={"key": "value"})
        t = tracer.get_trace(tid)
        assert t is not None
        assert t["metadata"]["key"] == "value"


# ===== Engine =====

class TestResilienceEngine:
    @pytest.mark.asyncio
    async def test_start_stop(self) -> None:
        engine = ResilienceEngine()
        await engine.start()
        assert engine.is_running() is True
        await engine.shutdown()
        assert engine.is_running() is False

    @pytest.mark.asyncio
    async def test_execute_protected_success(self) -> None:
        engine = ResilienceEngine()
        await engine.start()

        async def ok() -> str:
            return "result"

        result = await engine.execute_protected("svc1", ok)
        assert result == "result"
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_execute_protected_failure_fallback(self) -> None:
        engine = ResilienceEngine()
        await engine.start()

        async def fail() -> None:
            raise ValueError("boom")

        def fb(*args: Any, **kwargs: Any) -> str:
            return "fallback"

        engine.fallback.register_handler("svc1", fb)
        result = await engine.execute_protected("svc1", fail)
        assert result == "fallback"
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_get_health(self) -> None:
        engine = ResilienceEngine()
        await engine.start()
        health = engine.get_health()
        assert health["status"] in ("healthy", "degraded")
        assert "circuit_breakers" in health
        assert "degraded_services" in health
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_get_status(self) -> None:
        engine = ResilienceEngine()
        await engine.start()
        status = engine.get_status()
        assert "state" in status
        assert "total_protections" in status
        assert status["total_protections"] >= 20
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_get_diagnostics(self) -> None:
        engine = ResilienceEngine()
        await engine.start()
        diag = engine.get_diagnostics()
        assert isinstance(diag, dict)
        assert "circuit_breakers" in diag
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_get_metrics(self) -> None:
        engine = ResilienceEngine()
        await engine.start()
        m = engine.get_metrics()
        assert m.retries == 0
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_get_traces(self) -> None:
        engine = ResilienceEngine()
        await engine.start()
        traces = engine.get_traces()
        assert isinstance(traces, list)
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_reset(self) -> None:
        engine = ResilienceEngine()
        await engine.start()
        await engine.reset()
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_recover(self) -> None:
        engine = ResilienceEngine()
        await engine.start()
        success = await engine.recover("svc1")
        assert isinstance(success, bool)
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_subsystems_accessible(self) -> None:
        engine = ResilienceEngine()
        await engine.start()
        assert engine.circuit_breakers is not None
        assert engine.retry is not None
        assert engine.timeout is not None
        assert engine.fallback is not None
        assert engine.bulkhead is not None
        assert engine.backpressure is not None
        assert engine.rate_control is not None
        assert engine.health_guard is not None
        assert engine.watchdog is not None
        assert engine.recovery is not None
        assert engine.failover is not None
        assert engine.degradation is not None
        assert engine.policies is not None
        assert engine.diagnostics is not None
        assert engine.lifecycle is not None
        await engine.shutdown()


# ===== Factory =====

class TestResilienceFactory:
    def test_create_default(self) -> None:
        engine = ResilienceFactory.create_default()
        assert isinstance(engine, ResilienceEngine)

    def test_create(self) -> None:
        engine = ResilienceFactory.create(name="test")
        assert isinstance(engine, ResilienceEngine)

    def test_get_or_create(self) -> None:
        ResilienceFactory.reset()
        e1 = ResilienceFactory.get_or_create()
        e2 = ResilienceFactory.get_or_create()
        assert e1 is e2
        ResilienceFactory.reset()

    def test_reset(self) -> None:
        ResilienceFactory.reset()
        assert ResilienceFactory._instance is None

    def test_separate_instances(self) -> None:
        e1 = ResilienceFactory.create()
        e2 = ResilienceFactory.create()
        assert e1 is not e2
