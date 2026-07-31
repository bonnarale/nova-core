"""Resilience engine — top-level coordinator for all resilience subsystems."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Coroutine, Awaitable

from app.resilience.backpressure import BackpressureManager
from app.resilience.bulkhead import BulkheadManager
from app.resilience.circuit_breaker import CircuitBreakerManager
from app.resilience.degradation import DegradationManager
from app.resilience.diagnostics import ResilienceDiagnostics
from app.resilience.enums import (
    CircuitState,
    DegradationLevel,
    FallbackStrategy,
    RecoveryPolicy,
    ResilienceState,
    RetryStrategy,
)
from app.resilience.failover import FailoverManager
from app.resilience.fallback import FallbackManager
from app.resilience.health_guard import HealthGuard
from app.resilience.lifecycle import ResilienceLifecycle
from app.resilience.metrics import ResilienceMetrics, ResilienceMetricsCollector
from app.resilience.rate_control import RateController
from app.resilience.recovery import RecoveryManager
from app.resilience.resilience_policy import ResiliencePolicyManager
from app.resilience.retry import RetryManager, RetryPolicy
from app.resilience.timeout import TimeoutManager
from app.resilience.tracing import ResilienceTracer
from app.resilience.watchdog import Watchdog

logger = logging.getLogger(__name__)


class ResilienceEngine:
    """Top-level resilience engine protecting all subsystems."""

    def __init__(self) -> None:
        self._lifecycle = ResilienceLifecycle()
        self._circuit_breakers = CircuitBreakerManager()
        self._retry = RetryManager()
        self._timeout = TimeoutManager()
        self._fallback = FallbackManager()
        self._bulkhead = BulkheadManager()
        self._backpressure = BackpressureManager()
        self._rate_control = RateController()
        self._health_guard = HealthGuard()
        self._watchdog = Watchdog()
        self._recovery = RecoveryManager()
        self._failover = FailoverManager()
        self._degradation = DegradationManager()
        self._policies = ResiliencePolicyManager()
        self._diagnostics = ResilienceDiagnostics()
        self._metrics = ResilienceMetricsCollector()
        self._tracer = ResilienceTracer()
        self._start_time: float = 0.0
        self._running = False

    @property
    def lifecycle(self) -> ResilienceLifecycle: return self._lifecycle
    @property
    def circuit_breakers(self) -> CircuitBreakerManager: return self._circuit_breakers
    @property
    def retry(self) -> RetryManager: return self._retry
    @property
    def timeout(self) -> TimeoutManager: return self._timeout
    @property
    def fallback(self) -> FallbackManager: return self._fallback
    @property
    def bulkhead(self) -> BulkheadManager: return self._bulkhead
    @property
    def backpressure(self) -> BackpressureManager: return self._backpressure
    @property
    def rate_control(self) -> RateController: return self._rate_control
    @property
    def health_guard(self) -> HealthGuard: return self._health_guard
    @property
    def watchdog(self) -> Watchdog: return self._watchdog
    @property
    def recovery(self) -> RecoveryManager: return self._recovery
    @property
    def failover(self) -> FailoverManager: return self._failover
    @property
    def degradation(self) -> DegradationManager: return self._degradation
    @property
    def policies(self) -> ResiliencePolicyManager: return self._policies
    @property
    def diagnostics(self) -> ResilienceDiagnostics: return self._diagnostics
    @property
    def metrics(self) -> ResilienceMetricsCollector: return self._metrics
    @property
    def tracer(self) -> ResilienceTracer: return self._tracer

    async def start(self) -> None:
        trace_id = self._tracer.start_trace("resilience.start")
        self._start_time = time.time()
        self._metrics.start()
        self._lifecycle.transition(ResilienceState.INITIALIZED, "init")
        self._lifecycle.transition(ResilienceState.READY, "ready")
        self._lifecycle.transition(ResilienceState.RUNNING, "running")
        self._running = True
        self._setup_default_breakers()
        self._setup_default_health_checks()
        self._tracer.finish_trace(trace_id)
        logger.info("Resilience engine started")

    async def shutdown(self) -> None:
        trace_id = self._tracer.start_trace("resilience.shutdown")
        self._lifecycle.transition(ResilienceState.SHUTDOWN, "shutdown")
        self._running = False
        self._tracer.finish_trace(trace_id)
        logger.info("Resilience engine stopped")

    def is_running(self) -> bool:
        return self._running

    def _setup_default_breakers(self) -> None:
        for name in self._policies.get_all():
            policy = self._policies.get(name)
            self._circuit_breakers.get_or_create(
                name, policy.circuit_breaker_threshold, policy.circuit_breaker_timeout,
            )

    def _setup_default_health_checks(self) -> None:
        for name in self._policies.get_all():
            self._health_guard.register_check(name)

    async def execute_protected(
        self,
        name: str,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        trace_id = self._tracer.start_trace(f"resilience.protect.{name}")
        cb = self._circuit_breakers.get(name)
        if cb and not cb.allow_request():
            self._metrics.record_circuit_breaker_trip()
            self._tracer.finish_trace(trace_id, "circuit_open")
            try:
                return await self._fallback.execute(name, func, *args, **kwargs)
            except Exception:
                return {"fallback": True, "component": name}
        try:
            result = await func(*args, **kwargs)
            if cb:
                cb.record_success()
            self._tracer.finish_trace(trace_id)
            return result
        except Exception as exc:
            if cb:
                cb.record_failure()
            self._metrics.record_retry()
            self._tracer.finish_trace(trace_id, "error", str(exc))
            try:
                return await self._fallback.execute(name, func, *args, **kwargs)
            except Exception:
                raise exc

    def get_health(self) -> dict[str, Any]:
        cb_summary = self._circuit_breakers.get_summary()
        degraded = self._degradation.get_degraded_subsystems()
        overall = "healthy"
        if cb_summary.get("open", 0) > 0:
            overall = "degraded"
        if degraded:
            overall = "degraded"
        return {
            "status": overall,
            "circuit_breakers": cb_summary.get("states", {}),
            "degraded_services": degraded,
        }

    def get_status(self) -> dict[str, Any]:
        status = self._lifecycle.get_status()
        return {
            **status,
            "total_protections": len(self._policies.get_all()),
            "active_circuit_breakers": self._circuit_breakers.get_summary().get("total", 0),
        }

    def get_diagnostics(self) -> dict[str, Any]:
        return self._diagnostics.generate(
            circuit_breakers=self._circuit_breakers.get_summary(),
            retry_stats=self._retry.get_stats(),
            timeout_events=self._timeout.get_events(),
            failover_events=self._failover.get_events(),
            degraded_services=self._degradation.get_degraded_subsystems(),
            recovery_history=self._recovery.get_history(),
        )

    def get_metrics(self) -> ResilienceMetrics:
        return self._metrics.snapshot()

    def get_traces(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._tracer.get_traces(limit)

    async def reset(self, components: list[str] | None = None) -> None:
        trace_id = self._tracer.start_trace("resilience.reset")
        if components:
            for name in components:
                self._circuit_breakers.reset(name)
        else:
            self._circuit_breakers.reset_all()
        self._metrics.reset()
        self._tracer.finish_trace(trace_id)

    async def recover(self, component: str) -> bool:
        trace_id = self._tracer.start_trace(f"resilience.recover.{component}")
        self._lifecycle.transition(ResilienceState.RECOVERING, f"recovering {component}")
        success = await self._recovery.recover(component)
        if success:
            self._metrics.record_recovery()
            self._lifecycle.transition(ResilienceState.RUNNING, "recovered")
        self._tracer.finish_trace(trace_id)
        return success
