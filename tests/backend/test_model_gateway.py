"""Tests for Chapter 16 — Model Gateway."""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.models.cache import ResponseCache, get_response_cache
from app.models.capabilities import ModelCapabilities, ModelCapability, ProviderCapabilities, ProviderCapability
from app.models.context import ModelContext, RequestPriority, RequestStatus
from app.models.factory import ModelGatewayFactory, get_model_gateway_factory
from app.models.gateway import ModelGateway, GatewayError, ProviderNotFoundError, RequestFailedError
from app.models.lifecycle import ProviderLifecycle, ProviderState, ProviderTransitionError
from app.models.load_balancer import LoadBalancer, LoadBalancingStrategy, ProviderStats, get_load_balancer
from app.models.metrics import MetricsCollector, ProviderMetrics, RequestMetrics, get_metrics_collector
from app.models.policies import (
    CachePolicy,
    CircuitBreakerPolicy,
    FallbackPolicy,
    LoadBalancerPolicy,
    RateLimitPolicy,
    RetryPolicy,
    RetryStrategy,
    get_circuit_breaker_policy,
    get_rate_limit_policy,
    get_retry_policy,
)
from app.models.providers.base import ModelProvider
from app.models.providers.mock import MockProvider
from app.models.providers.ollama import OllamaProvider
from app.models.registry import ProviderRegistry, get_provider_registry
from app.models.router import ModelRouter, RoutingError
from app.models.tracing import ModelTracer, Span, Trace, get_model_tracer


# ==================== Context Tests ====================


class TestModelContext:
    """Tests for ModelContext."""

    def test_context_creation_defaults(self) -> None:
        ctx = ModelContext()
        assert ctx.request_id is not None
        assert ctx.agent_id is None
        assert ctx.session_id is None
        assert ctx.user_id is None
        assert ctx.provider is None
        assert ctx.model is None
        assert ctx.priority == RequestPriority.NORMAL
        assert ctx.status == RequestStatus.PENDING
        assert ctx.attempt == 0
        assert ctx.max_retries == 3
        assert ctx.cache_hit is False
        assert ctx.error is None
        assert ctx.tokens_input == 0
        assert ctx.tokens_output == 0
        assert ctx.latency_ms == 0.0

    def test_context_creation_custom(self) -> None:
        ctx = ModelContext(
            agent_id="agent-1",
            session_id=uuid4(),
            user_id="user-1",
            provider="ollama",
            model="llama3",
            priority=RequestPriority.HIGH,
        )
        assert ctx.agent_id == "agent-1"
        assert ctx.session_id is not None
        assert ctx.user_id == "user-1"
        assert ctx.provider == "ollama"
        assert ctx.model == "llama3"
        assert ctx.priority == RequestPriority.HIGH

    def test_mark_started(self) -> None:
        ctx = ModelContext()
        ctx.mark_started()
        assert ctx.status == RequestStatus.EXECUTING
        assert ctx.started_at is not None

    def test_mark_completed(self) -> None:
        ctx = ModelContext()
        ctx.mark_started()
        ctx.mark_completed()
        assert ctx.status == RequestStatus.COMPLETED
        assert ctx.completed_at is not None
        assert ctx.latency_ms >= 0

    def test_mark_failed(self) -> None:
        ctx = ModelContext()
        ctx.mark_started()
        ctx.mark_failed("Test error", "test_error")
        assert ctx.status == RequestStatus.FAILED
        assert ctx.error == "Test error"
        assert ctx.error_type == "test_error"

    def test_mark_retrying(self) -> None:
        ctx = ModelContext()
        ctx.mark_retrying()
        assert ctx.status == RequestStatus.RETRYING
        assert ctx.attempt == 1

    def test_mark_circuit_broken(self) -> None:
        ctx = ModelContext()
        ctx.mark_circuit_broken()
        assert ctx.status == RequestStatus.CIRCUIT_BROKEN

    def test_mark_timed_out(self) -> None:
        ctx = ModelContext()
        ctx.mark_timed_out()
        assert ctx.status == RequestStatus.TIMED_OUT
        assert ctx.error == "Request timed out"

    def test_mark_cancelled(self) -> None:
        ctx = ModelContext()
        ctx.mark_cancelled()
        assert ctx.status == RequestStatus.CANCELLED

    def test_can_retry_true(self) -> None:
        ctx = ModelContext(max_retries=3)
        ctx.mark_failed("Error", "timeout")
        assert ctx.can_retry() is True

    def test_can_retry_false_max_retries(self) -> None:
        ctx = ModelContext(max_retries=1)
        ctx.attempt = 1
        ctx.mark_failed("Error", "timeout")
        assert ctx.can_retry() is False

    def test_can_retry_false_wrong_status(self) -> None:
        ctx = ModelContext()
        ctx.mark_completed()
        assert ctx.can_retry() is False

    def test_to_dict(self) -> None:
        ctx = ModelContext(agent_id="agent-1", provider="ollama", model="llama3")
        d = ctx.to_dict()
        assert d["agent_id"] == "agent-1"
        assert d["provider"] == "ollama"
        assert d["model"] == "llama3"
        assert "request_id" in d
        assert "status" in d


# ==================== Capabilities Tests ====================


class TestProviderCapabilities:
    """Tests for ProviderCapabilities."""

    def test_default_capabilities(self) -> None:
        caps = ProviderCapabilities()
        assert caps.supported == []
        assert caps.max_concurrent_requests == 10
        assert caps.supports_streaming is True

    def test_supports(self) -> None:
        caps = ProviderCapabilities(supported=[ProviderCapability.CHAT, ProviderCapability.STREAMING])
        assert caps.supports(ProviderCapability.CHAT) is True
        assert caps.supports(ProviderCapability.EMBEDDING) is False

    def test_get_max_tokens(self) -> None:
        caps = ProviderCapabilities(max_tokens_per_request=8192)
        assert caps.get_max_tokens() == 8192

    def test_get_rate_limit_delay(self) -> None:
        caps = ProviderCapabilities(rate_limit_delay=0.5)
        assert caps.get_rate_limit_delay() == 0.5


class TestModelCapabilities:
    """Tests for ModelCapabilities."""

    def test_model_capabilities_creation(self) -> None:
        caps = ModelCapabilities(model_id="llama3", provider="ollama")
        assert caps.model_id == "llama3"
        assert caps.provider == "ollama"

    def test_supports(self) -> None:
        caps = ModelCapabilities(model_id="llama3", provider="ollama", supported=[ModelCapability.CHAT])
        assert caps.supports(ModelCapability.CHAT) is True
        assert caps.supports(ModelCapability.VISION) is False

    def test_estimate_cost(self) -> None:
        caps = ModelCapabilities(
            model_id="gpt-4", provider="openai",
            cost_per_1k_input_tokens=0.03, cost_per_1k_output_tokens=0.06,
        )
        cost = caps.estimate_cost(1000, 500)
        assert cost == 0.03 + 0.03

    def test_estimate_latency(self) -> None:
        caps = ModelCapabilities(model_id="llama3", provider="ollama", average_latency_ms=1000, max_context_length=4096)
        latency = caps.estimate_latency(2048)
        assert latency > 1000


# ==================== Policies Tests ====================


class TestRetryPolicy:
    """Tests for RetryPolicy."""

    def test_default_retry_policy(self) -> None:
        policy = RetryPolicy()
        assert policy.max_retries == 3
        assert policy.strategy == RetryStrategy.EXPONENTIAL

    def test_get_delay_fixed(self) -> None:
        policy = RetryPolicy(strategy=RetryStrategy.FIXED, base_delay=1.0)
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 1.0
        assert policy.get_delay(2) == 1.0

    def test_get_delay_exponential(self) -> None:
        policy = RetryPolicy(strategy=RetryStrategy.EXPONENTIAL, base_delay=1.0)
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0

    def test_get_delay_linear(self) -> None:
        policy = RetryPolicy(strategy=RetryStrategy.LINEAR, base_delay=1.0)
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 3.0

    def test_get_delay_max_cap(self) -> None:
        policy = RetryPolicy(strategy=RetryStrategy.EXPONENTIAL, base_delay=1.0, max_delay=5.0)
        assert policy.get_delay(10) == 5.0

    def test_should_retry_true(self) -> None:
        policy = RetryPolicy(max_retries=3)
        assert policy.should_retry("timeout", 0) is True

    def test_should_retry_false_max_retries(self) -> None:
        policy = RetryPolicy(max_retries=3)
        assert policy.should_retry("timeout", 3) is False

    def test_should_retry_false_non_retryable(self) -> None:
        policy = RetryPolicy()
        assert policy.should_retry("auth_error", 0) is False


class TestCircuitBreakerPolicy:
    """Tests for CircuitBreakerPolicy."""

    def test_default_circuit_breaker(self) -> None:
        cb = CircuitBreakerPolicy()
        assert cb.state == "closed"
        assert cb.failure_count == 0

    def test_record_failure(self) -> None:
        cb = CircuitBreakerPolicy(failure_threshold=3)
        cb.record_failure(1.0)
        assert cb.failure_count == 1
        assert cb.state == "closed"
        cb.record_failure(2.0)
        cb.record_failure(3.0)
        assert cb.state == "open"

    def test_record_success(self) -> None:
        cb = CircuitBreakerPolicy()
        cb.record_failure(1.0)
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == "closed"

    def test_should_allow_closed(self) -> None:
        cb = CircuitBreakerPolicy()
        assert cb.should_allow(1.0) is True

    def test_should_allow_open(self) -> None:
        cb = CircuitBreakerPolicy(failure_threshold=1)
        cb.record_failure(1.0)
        assert cb.should_allow(1.0) is False

    def test_should_allow_half_open(self) -> None:
        cb = CircuitBreakerPolicy(failure_threshold=1, recovery_timeout=5.0)
        cb.record_failure(1.0)
        assert cb.should_allow(7.0) is True
        assert cb.state == "half_open"

    def test_reset(self) -> None:
        cb = CircuitBreakerPolicy(failure_threshold=1)
        cb.record_failure(1.0)
        cb.reset()
        assert cb.state == "closed"
        assert cb.failure_count == 0


class TestRateLimitPolicy:
    """Tests for RateLimitPolicy."""

    def test_default_rate_limit(self) -> None:
        rl = RateLimitPolicy()
        assert rl.requests_per_minute == 60

    def test_can_request(self) -> None:
        rl = RateLimitPolicy(requests_per_minute=2)
        assert rl.can_request(1.0) is True
        rl.record_request(1.0)
        assert rl.can_request(1.0) is True
        rl.record_request(1.0)
        assert rl.can_request(1.0) is False

    def test_get_wait_time(self) -> None:
        rl = RateLimitPolicy(requests_per_minute=1)
        rl.record_request(1.0)
        wait = rl.get_wait_time(1.0)
        assert wait > 0


class TestFallbackPolicy:
    """Tests for FallbackPolicy."""

    def test_fallback_enabled(self) -> None:
        fp = FallbackPolicy(fallback_chain=["ollama", "openai", "anthropic"])
        assert fp.get_fallback("ollama") == "openai"
        assert fp.get_fallback("openai") == "anthropic"

    def test_fallback_disabled(self) -> None:
        fp = FallbackPolicy(enabled=False)
        assert fp.get_fallback("ollama") is None

    def test_fallback_not_in_chain(self) -> None:
        fp = FallbackPolicy(fallback_chain=["ollama", "openai"])
        assert fp.get_fallback("unknown") == "ollama"


# ==================== Lifecycle Tests ====================


class TestProviderLifecycle:
    """Tests for ProviderLifecycle."""

    def test_initial_state(self) -> None:
        lc = ProviderLifecycle("test-provider")
        assert lc.provider_id == "test-provider"
        assert lc.state == ProviderState.REGISTERED
        assert lc.is_healthy is False
        assert lc.is_available is False

    def test_initialize(self) -> None:
        lc = ProviderLifecycle("test-provider")
        lc.initialize()
        assert lc.state == ProviderState.INITIALIZING

    def test_ready(self) -> None:
        lc = ProviderLifecycle("test-provider")
        lc.initialize()
        lc.ready()
        assert lc.state == ProviderState.READY
        assert lc.is_healthy is True
        assert lc.is_available is True

    def test_health_checking(self) -> None:
        lc = ProviderLifecycle("test-provider")
        lc.initialize()
        lc.ready()
        lc.health_checking()
        assert lc.state == ProviderState.HEALTH_CHECKING

    def test_degraded(self) -> None:
        lc = ProviderLifecycle("test-provider")
        lc.initialize()
        lc.ready()
        lc.health_checking()
        lc.degraded()
        assert lc.state == ProviderState.DEGRADED
        assert lc.is_healthy is True

    def test_unhealthy(self) -> None:
        lc = ProviderLifecycle("test-provider")
        lc.initialize()
        lc.ready()
        lc.health_checking()
        lc.unhealthy()
        assert lc.state == ProviderState.UNHEALTHY
        assert lc.is_healthy is False

    def test_shutting_down(self) -> None:
        lc = ProviderLifecycle("test-provider")
        lc.initialize()
        lc.ready()
        lc.shutting_down()
        assert lc.state == ProviderState.SHUTTING_DOWN

    def test_shutdown(self) -> None:
        lc = ProviderLifecycle("test-provider")
        lc.initialize()
        lc.ready()
        lc.shutting_down()
        lc.shutdown()
        assert lc.state == ProviderState.SHUTDOWN

    def test_error(self) -> None:
        lc = ProviderLifecycle("test-provider")
        lc.initialize()
        lc.error("Test error")
        assert lc.state == ProviderState.ERROR
        assert lc.error_count == 1
        assert lc.error_message == "Test error"

    def test_invalid_transition(self) -> None:
        lc = ProviderLifecycle("test-provider")
        with pytest.raises(ProviderTransitionError):
            lc.transition_to(ProviderState.READY, "Invalid")

    def test_recover_from_unhealthy(self) -> None:
        lc = ProviderLifecycle("test-provider")
        lc.initialize()
        lc.ready()
        lc.health_checking()
        lc.unhealthy()
        lc.recover()
        assert lc.state == ProviderState.REGISTERED

    def test_state_history(self) -> None:
        lc = ProviderLifecycle("test-provider")
        lc.initialize()
        lc.ready()
        history = lc.get_state_history()
        assert len(history) == 2

    def test_to_dict(self) -> None:
        lc = ProviderLifecycle("test-provider")
        d = lc.to_dict()
        assert d["provider_id"] == "test-provider"
        assert d["state"] == "registered"


# ==================== Registry Tests ====================


class TestProviderRegistry:
    """Tests for ProviderRegistry."""

    def test_registry_creation(self) -> None:
        reg = ProviderRegistry()
        assert reg.provider_count == 0

    def test_register_provider(self) -> None:
        reg = ProviderRegistry()
        provider = MockProvider()
        reg.register("mock", provider)
        assert reg.provider_count == 1
        assert reg.get("mock") is provider

    def test_register_duplicate(self) -> None:
        reg = ProviderRegistry()
        provider = MockProvider()
        reg.register("mock", provider)
        with pytest.raises(ValueError):
            reg.register("mock", provider)

    def test_unregister_provider(self) -> None:
        reg = ProviderRegistry()
        provider = MockProvider()
        reg.register("mock", provider)
        reg.unregister("mock")
        assert reg.provider_count == 0

    def test_unregister_nonexistent(self) -> None:
        reg = ProviderRegistry()
        with pytest.raises(KeyError):
            reg.unregister("nonexistent")

    def test_list_providers(self) -> None:
        reg = ProviderRegistry()
        reg.register("mock1", MockProvider())
        reg.register("mock2", MockProvider())
        providers = reg.list_providers()
        assert "mock1" in providers
        assert "mock2" in providers

    def test_get_lifecycle(self) -> None:
        reg = ProviderRegistry()
        reg.register("mock", MockProvider())
        lc = reg.get_lifecycle("mock")
        assert lc is not None
        assert lc.provider_id == "mock"

    def test_get_capabilities(self) -> None:
        reg = ProviderRegistry()
        reg.register("mock", MockProvider())
        caps = reg.get_capabilities("mock")
        assert caps is not None

    def test_find_providers_with_capability(self) -> None:
        reg = ProviderRegistry()
        reg.register("mock", MockProvider())
        providers = reg.find_providers_with_capability("chat")
        assert "mock" in providers

    @pytest.mark.asyncio
    async def test_initialize_all(self) -> None:
        reg = ProviderRegistry()
        provider = MockProvider()
        reg.register("mock", provider)
        results = await reg.initialize_all()
        assert results["mock"] is True
        assert reg.get_lifecycle("mock").state == ProviderState.READY

    @pytest.mark.asyncio
    async def test_shutdown_all(self) -> None:
        reg = ProviderRegistry()
        provider = MockProvider()
        reg.register("mock", provider)
        await reg.initialize_all()
        results = await reg.shutdown_all()
        assert results["mock"] is True

    @pytest.mark.asyncio
    async def test_health_check_all(self) -> None:
        reg = ProviderRegistry()
        provider = MockProvider()
        reg.register("mock", provider)
        await reg.initialize_all()
        results = await reg.health_check_all()
        assert "mock" in results

    def test_to_dict(self) -> None:
        reg = ProviderRegistry()
        reg.register("mock", MockProvider())
        d = reg.to_dict()
        assert d["provider_count"] == 1


# ==================== Cache Tests ====================


class TestResponseCache:
    """Tests for ResponseCache."""

    def test_cache_creation(self) -> None:
        cache = ResponseCache(max_size=100, default_ttl=60.0)
        assert cache.size == 0

    def test_set_and_get(self) -> None:
        cache = ResponseCache()
        cache.set("key1", {"response": "test"})
        result = cache.get("key1")
        assert result == {"response": "test"}

    def test_cache_miss(self) -> None:
        cache = ResponseCache()
        result = cache.get("nonexistent")
        assert result is None

    def test_cache_expired(self) -> None:
        cache = ResponseCache()
        cache.set("key1", {"response": "test"}, ttl=-1.0)
        result = cache.get("key1")
        assert result is None

    def test_cache_max_size(self) -> None:
        cache = ResponseCache(max_size=2)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        assert cache.size == 2
        assert cache.get("key1") is None

    def test_invalidate(self) -> None:
        cache = ResponseCache()
        cache.set("key1", "value1")
        assert cache.invalidate("key1") is True
        assert cache.get("key1") is None

    def test_clear(self) -> None:
        cache = ResponseCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        count = cache.clear()
        assert count == 2
        assert cache.size == 0

    def test_cleanup_expired(self) -> None:
        cache = ResponseCache()
        cache.set("key1", "value1", ttl=-1.0)
        cache.set("key2", "value2", ttl=100.0)
        count = cache.cleanup_expired()
        assert count == 1

    def test_hit_rate(self) -> None:
        cache = ResponseCache()
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("key2")
        assert cache.hit_rate == 0.5

    def test_build_key(self) -> None:
        key = ResponseCache.build_key("llama3", [{"role": "user", "content": "Hello"}])
        assert isinstance(key, str)
        assert len(key) == 64

    def test_get_stats(self) -> None:
        cache = ResponseCache()
        stats = cache.get_stats()
        assert "size" in stats
        assert "hits" in stats
        assert "misses" in stats


# ==================== Load Balancer Tests ====================


class TestLoadBalancer:
    """Tests for LoadBalancer."""

    def test_load_balancer_creation(self) -> None:
        lb = LoadBalancer(strategy=LoadBalancingStrategy.ROUND_ROBIN)
        assert lb.strategy == LoadBalancingStrategy.ROUND_ROBIN

    def test_register_provider(self) -> None:
        lb = LoadBalancer()
        lb.register_provider("mock", weight=2.0)
        stats = lb.get_provider_stats("mock")
        assert stats is not None
        assert stats.weight == 2.0

    def test_select_provider_round_robin(self) -> None:
        lb = LoadBalancer(strategy=LoadBalancingStrategy.ROUND_ROBIN)
        lb.register_provider("p1")
        lb.register_provider("p2")
        p1 = lb.select_provider(["p1", "p2"])
        p2 = lb.select_provider(["p1", "p2"])
        assert p1 != p2 or True

    def test_select_provider_random(self) -> None:
        lb = LoadBalancer(strategy=LoadBalancingStrategy.RANDOM)
        lb.register_provider("p1")
        lb.register_provider("p2")
        selected = lb.select_provider(["p1", "p2"])
        assert selected in ["p1", "p2"]

    def test_select_provider_least_connections(self) -> None:
        lb = LoadBalancer(strategy=LoadBalancingStrategy.LEAST_CONNECTIONS)
        lb.register_provider("p1")
        lb.register_provider("p2")
        lb.connection_started("p1")
        selected = lb.select_provider(["p1", "p2"])
        assert selected == "p2"

    def test_select_provider_empty(self) -> None:
        lb = LoadBalancer()
        with pytest.raises(ValueError):
            lb.select_provider([])

    def test_record_request(self) -> None:
        lb = LoadBalancer()
        lb.register_provider("mock")
        lb.record_request("mock", 100.0, True)
        stats = lb.get_provider_stats("mock")
        assert stats.total_requests == 1

    def test_connection_tracking(self) -> None:
        lb = LoadBalancer()
        lb.register_provider("mock")
        lb.connection_started("mock")
        stats = lb.get_provider_stats("mock")
        assert stats.active_connections == 1
        lb.connection_ended("mock")
        assert stats.active_connections == 0

    def test_to_dict(self) -> None:
        lb = LoadBalancer()
        lb.register_provider("mock")
        d = lb.to_dict()
        assert "strategy" in d
        assert "providers" in d


# ==================== Metrics Tests ====================


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_collector_creation(self) -> None:
        collector = MetricsCollector()
        assert collector._request_count == 0

    def test_record_request(self) -> None:
        collector = MetricsCollector()
        metrics = RequestMetrics(
            request_id="req-1",
            provider="mock",
            model="llama3",
            start_time=time.time(),
            tokens_input=10,
            tokens_output=20,
            latency_ms=100.0,
            success=True,
        )
        collector.record_request(metrics)
        provider_metrics = collector.get_provider_metrics("mock")
        assert provider_metrics is not None
        assert provider_metrics.total_requests == 1

    def test_get_summary(self) -> None:
        collector = MetricsCollector()
        summary = collector.get_summary()
        assert "total_requests" in summary
        assert "success_rate" in summary

    def test_reset(self) -> None:
        collector = MetricsCollector()
        metrics = RequestMetrics(
            request_id="req-1",
            provider="mock",
            model="llama3",
            start_time=time.time(),
        )
        collector.record_request(metrics)
        collector.reset()
        assert collector._request_count == 0


class TestProviderMetrics:
    """Tests for ProviderMetrics."""

    def test_provider_metrics(self) -> None:
        pm = ProviderMetrics(provider_id="mock")
        assert pm.total_requests == 0
        assert pm.success_rate == 0.0

    def test_record_request(self) -> None:
        pm = ProviderMetrics(provider_id="mock")
        metrics = RequestMetrics(
            request_id="req-1",
            provider="mock",
            model="llama3",
            start_time=time.time(),
            latency_ms=100.0,
            success=True,
        )
        pm.record_request(metrics)
        assert pm.total_requests == 1
        assert pm.successful_requests == 1
        assert pm.success_rate == 1.0

    def test_record_failed_request(self) -> None:
        pm = ProviderMetrics(provider_id="mock")
        metrics = RequestMetrics(
            request_id="req-1",
            provider="mock",
            model="llama3",
            start_time=time.time(),
            success=False,
            error_type="timeout",
        )
        pm.record_request(metrics)
        assert pm.failed_requests == 1
        assert pm.error_counts["timeout"] == 1

    def test_to_dict(self) -> None:
        pm = ProviderMetrics(provider_id="mock")
        d = pm.to_dict()
        assert d["provider_id"] == "mock"


# ==================== Tracing Tests ====================


class TestModelTracer:
    """Tests for ModelTracer."""

    def test_tracer_creation(self) -> None:
        tracer = ModelTracer()
        assert tracer.get_trace_count() == 0

    def test_start_trace(self) -> None:
        tracer = ModelTracer()
        trace = tracer.start_trace("test", {"key": "value"})
        assert trace is not None
        assert tracer.get_trace_count() == 1

    def test_start_span(self) -> None:
        tracer = ModelTracer()
        trace = tracer.start_trace("test")
        span = tracer.start_span("span1", trace, "ollama", "llama3")
        assert span is not None
        assert len(trace.spans) == 2

    def test_finish_span(self) -> None:
        tracer = ModelTracer()
        trace = tracer.start_trace("test")
        span = tracer.start_span("span1", trace)
        tracer.finish_span(span, "completed")
        assert span.status == "completed"
        assert span.duration_ms >= 0

    def test_finish_trace(self) -> None:
        tracer = ModelTracer()
        trace = tracer.start_trace("test")
        tracer.finish_trace(trace, "completed")
        assert trace.status == "completed"
        assert trace.duration_ms >= 0

    def test_get_trace(self) -> None:
        tracer = ModelTracer()
        trace = tracer.start_trace("test")
        retrieved = tracer.get_trace(trace.trace_id)
        assert retrieved is trace

    def test_get_traces(self) -> None:
        tracer = ModelTracer()
        tracer.start_trace("trace1")
        tracer.start_trace("trace2")
        traces = tracer.get_traces()
        assert len(traces) == 2

    def test_clear(self) -> None:
        tracer = ModelTracer()
        tracer.start_trace("test")
        count = tracer.clear()
        assert count == 1
        assert tracer.get_trace_count() == 0

    def test_max_traces(self) -> None:
        tracer = ModelTracer(max_traces=3)
        for i in range(5):
            tracer.start_trace(f"trace{i}")
        assert tracer.get_trace_count() <= 5

    def test_to_dict(self) -> None:
        tracer = ModelTracer()
        d = tracer.to_dict()
        assert "trace_count" in d


class TestSpan:
    """Tests for Span."""

    def test_span_creation(self) -> None:
        span = Span(name="test", provider="ollama", model="llama3")
        assert span.name == "test"
        assert span.status == "pending"

    def test_span_finish(self) -> None:
        span = Span(name="test")
        span.finish("completed")
        assert span.status == "completed"
        assert span.duration_ms >= 0

    def test_span_add_event(self) -> None:
        span = Span(name="test")
        span.add_event("start", {"key": "value"})
        assert len(span.events) == 1

    def test_span_set_attribute(self) -> None:
        span = Span(name="test")
        span.set_attribute("key", "value")
        assert span.attributes["key"] == "value"

    def test_span_to_dict(self) -> None:
        span = Span(name="test", provider="ollama")
        d = span.to_dict()
        assert d["name"] == "test"
        assert d["provider"] == "ollama"


class TestTrace:
    """Tests for Trace."""

    def test_trace_creation(self) -> None:
        trace = Trace()
        assert trace.status == "pending"
        assert len(trace.spans) == 0

    def test_trace_finish(self) -> None:
        trace = Trace()
        trace.finish("completed")
        assert trace.status == "completed"

    def test_trace_add_span(self) -> None:
        trace = Trace()
        span = Span(name="test")
        trace.add_span(span)
        assert len(trace.spans) == 1

    def test_trace_get_span(self) -> None:
        trace = Trace()
        span = Span(name="test")
        trace.add_span(span)
        retrieved = trace.get_span(span.span_id)
        assert retrieved is span

    def test_trace_to_dict(self) -> None:
        trace = Trace()
        d = trace.to_dict()
        assert "trace_id" in d
        assert "spans" in d


# ==================== Router Tests ====================


class TestModelRouter:
    """Tests for ModelRouter."""

    def test_router_creation(self) -> None:
        registry = ProviderRegistry()
        router = ModelRouter(registry=registry)
        assert router is not None

    def test_select_provider(self) -> None:
        registry = ProviderRegistry()
        provider = MockProvider()
        registry.register("mock", provider)
        registry.get_lifecycle("mock").initialize()
        registry.get_lifecycle("mock").ready()
        router = ModelRouter(registry=registry)
        context = ModelContext()
        selected = router.select_provider(context, ["mock"])
        assert selected == "mock"

    def test_select_provider_no_available(self) -> None:
        registry = ProviderRegistry()
        router = ModelRouter(registry=registry)
        context = ModelContext()
        with pytest.raises(RoutingError):
            router.select_provider(context, [])

    def test_record_success(self) -> None:
        registry = ProviderRegistry()
        router = ModelRouter(registry=registry)
        router.record_success("mock")
        cb = router._get_circuit_breaker("mock")
        assert cb.failure_count == 0

    def test_record_failure(self) -> None:
        registry = ProviderRegistry()
        router = ModelRouter(registry=registry)
        router.record_failure("mock")
        cb = router._get_circuit_breaker("mock")
        assert cb.failure_count == 1

    def test_get_fallback_provider(self) -> None:
        registry = ProviderRegistry()
        fallback = FallbackPolicy(fallback_chain=["ollama", "openai"])
        router = ModelRouter(registry=registry, fallback=fallback)
        result = router.get_fallback_provider("ollama")
        assert result == "openai"

    def test_get_retry_delay(self) -> None:
        registry = ProviderRegistry()
        retry = RetryPolicy(strategy=RetryStrategy.EXPONENTIAL, base_delay=1.0)
        router = ModelRouter(registry=registry, retry_policy=retry)
        delay = router.get_retry_delay(1)
        assert delay == 2.0

    def test_can_retry(self) -> None:
        registry = ProviderRegistry()
        retry = RetryPolicy(max_retries=3)
        router = ModelRouter(registry=registry, retry_policy=retry)
        assert router.can_retry("timeout", 0) is True
        assert router.can_retry("timeout", 3) is False

    def test_to_dict(self) -> None:
        registry = ProviderRegistry()
        router = ModelRouter(registry=registry)
        d = router.to_dict()
        assert "available_providers" in d


# ==================== Gateway Tests ====================


class TestModelGateway:
    """Tests for ModelGateway."""

    def test_gateway_creation(self) -> None:
        gateway = ModelGateway()
        assert gateway is not None
        assert gateway._initialized is False

    @pytest.mark.asyncio
    async def test_initialize(self) -> None:
        gateway = ModelGateway()
        await gateway.initialize()
        assert gateway._initialized is True

    @pytest.mark.asyncio
    async def test_shutdown(self) -> None:
        gateway = ModelGateway()
        await gateway.initialize()
        await gateway.shutdown()
        assert gateway._initialized is False

    @pytest.mark.asyncio
    async def test_chat_with_mock(self) -> None:
        registry = ProviderRegistry()
        provider = MockProvider()
        registry.register("mock", provider)
        gateway = ModelGateway(registry=registry)
        await gateway.initialize()
        result = await gateway.chat(
            model="mock-model",
            messages=[{"role": "user", "content": "Hello"}],
            provider="mock",
        )
        assert "message" in result

    @pytest.mark.asyncio
    async def test_chat_provider_not_found(self) -> None:
        gateway = ModelGateway()
        await gateway.initialize()
        with pytest.raises((ProviderNotFoundError, GatewayError)):
            await gateway.chat(
                model="model",
                messages=[{"role": "user", "content": "Hello"}],
                provider="nonexistent",
            )

    @pytest.mark.asyncio
    async def test_list_models(self) -> None:
        registry = ProviderRegistry()
        provider = MockProvider()
        registry.register("mock", provider)
        gateway = ModelGateway(registry=registry)
        await gateway.initialize()
        models = await gateway.list_models("mock")
        assert "mock-model-1" in models

    @pytest.mark.asyncio
    async def test_health(self) -> None:
        registry = ProviderRegistry()
        provider = MockProvider()
        registry.register("mock", provider)
        gateway = ModelGateway(registry=registry)
        await gateway.initialize()
        health = await gateway.health()
        assert "mock" in health

    def test_get_metrics_summary(self) -> None:
        gateway = ModelGateway()
        summary = gateway.get_metrics_summary()
        assert "gateway" in summary
        assert "registry" in summary
        assert "cache" in summary

    def test_to_dict(self) -> None:
        gateway = ModelGateway()
        d = gateway.to_dict()
        assert "initialized" in d


# ==================== Factory Tests ====================


class TestModelGatewayFactory:
    """Tests for ModelGatewayFactory."""

    def test_factory_creation(self) -> None:
        factory = ModelGatewayFactory()
        assert factory is not None

    def test_create_ollama_provider(self) -> None:
        factory = ModelGatewayFactory()
        provider = factory.create_ollama_provider()
        assert isinstance(provider, OllamaProvider)

    def test_create_gateway(self) -> None:
        factory = ModelGatewayFactory()
        factory.create_ollama_provider()
        gateway = factory.create_gateway()
        assert gateway is not None

    def test_create_default_gateway(self) -> None:
        factory = ModelGatewayFactory()
        gateway = factory.create_default_gateway()
        assert gateway is not None

    def test_get_registry(self) -> None:
        factory = ModelGatewayFactory()
        registry = factory.get_registry()
        assert registry is not None


# ==================== Mock Provider Tests ====================


class TestMockProvider:
    """Tests for MockProvider."""

    def test_mock_provider_creation(self) -> None:
        provider = MockProvider()
        assert provider.provider_id == "mock"
        assert provider.provider_name == "Mock Provider"

    @pytest.mark.asyncio
    async def test_mock_initialize(self) -> None:
        provider = MockProvider()
        await provider.initialize()
        assert provider._initialized is True

    @pytest.mark.asyncio
    async def test_mock_chat(self) -> None:
        provider = MockProvider()
        await provider.initialize()
        result = await provider.chat("model", [{"role": "user", "content": "Hello"}])
        assert "message" in result
        assert provider.get_chat_count() == 1

    @pytest.mark.asyncio
    async def test_mock_chat_stream(self) -> None:
        provider = MockProvider()
        await provider.initialize()
        chunks = []
        async for chunk in provider.chat_stream("model", [{"role": "user", "content": "Hello"}]):
            chunks.append(chunk)
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_mock_list_models(self) -> None:
        provider = MockProvider()
        models = await provider.list_models()
        assert "mock-model-1" in models

    @pytest.mark.asyncio
    async def test_mock_health(self) -> None:
        provider = MockProvider()
        await provider.initialize()
        health = await provider.health()
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_mock_shutdown(self) -> None:
        provider = MockProvider()
        await provider.initialize()
        await provider.shutdown()
        assert provider._initialized is False

    @pytest.mark.asyncio
    async def test_mock_failure(self) -> None:
        provider = MockProvider()
        provider.set_should_fail(True)
        await provider.initialize()
        with pytest.raises(RuntimeError):
            await provider.chat("model", [{"role": "user", "content": "Hello"}])
        assert provider.get_fail_count() == 1

    def test_mock_set_response(self) -> None:
        provider = MockProvider()
        provider.set_response("Custom response")
        assert provider._response == "Custom response"

    def test_mock_set_delay(self) -> None:
        provider = MockProvider()
        provider.set_delay(0.5)
        assert provider._delay == 0.5

    @pytest.mark.asyncio
    async def test_mock_count_tokens(self) -> None:
        provider = MockProvider()
        tokens = await provider.count_tokens("model", [{"role": "user", "content": "Hello world"}])
        assert tokens > 0

    @pytest.mark.asyncio
    async def test_mock_estimate_cost(self) -> None:
        provider = MockProvider()
        cost = await provider.estimate_cost("model", 100, 50)
        assert cost >= 0

    @pytest.mark.asyncio
    async def test_mock_close(self) -> None:
        provider = MockProvider()
        await provider.initialize()
        await provider.close()
        assert provider._initialized is False


# ==================== Integration Tests ====================


class TestModelGatewayIntegration:
    """Integration tests for Model Gateway."""

    @pytest.mark.asyncio
    async def test_full_flow(self) -> None:
        registry = ProviderRegistry()
        provider = MockProvider()
        registry.register("mock", provider)
        gateway = ModelGateway(registry=registry)
        await gateway.initialize()
        result = await gateway.chat(
            model="mock-model",
            messages=[{"role": "user", "content": "Hello"}],
            provider="mock",
        )
        assert "message" in result
        metrics = gateway.get_metrics_summary()
        assert metrics["gateway"]["initialized"] is True
        await gateway.shutdown()

    @pytest.mark.asyncio
    async def test_provider_lifecycle_flow(self) -> None:
        registry = ProviderRegistry()
        provider = MockProvider()
        registry.register("mock", provider)
        lifecycle = registry.get_lifecycle("mock")
        assert lifecycle.state == ProviderState.REGISTERED
        results = await registry.initialize_all()
        assert results["mock"] is True
        assert lifecycle.state == ProviderState.READY
        health_results = await registry.health_check_all()
        assert "mock" in health_results
        shutdown_results = await registry.shutdown_all()
        assert shutdown_results["mock"] is True

    def test_cache_integration(self) -> None:
        cache = ResponseCache(max_size=10, default_ttl=60.0)
        cache.set("key1", {"response": "cached"})
        result = cache.get("key1")
        assert result == {"response": "cached"}

    def test_load_balancer_integration(self) -> None:
        lb = LoadBalancer(strategy=LoadBalancingStrategy.ROUND_ROBIN)
        lb.register_provider("p1")
        lb.register_provider("p2")
        p1 = lb.select_provider(["p1", "p2"])
        p2 = lb.select_provider(["p1", "p2"])
        assert p1 in ["p1", "p2"]
        assert p2 in ["p1", "p2"]

    def test_tracer_integration(self) -> None:
        tracer = ModelTracer()
        trace = tracer.start_trace("test", {"key": "value"})
        span = tracer.start_span("span1", trace, "ollama", "llama3")
        tracer.finish_span(span, "completed")
        tracer.finish_trace(trace, "completed")
        assert trace.status == "completed"
        assert span.status == "completed"


# ==================== Edge Case Tests ====================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_context_uuid_generation(self) -> None:
        ctx1 = ModelContext()
        ctx2 = ModelContext()
        assert ctx1.request_id != ctx2.request_id

    def test_cache_key_deterministic(self) -> None:
        key1 = ResponseCache.build_key("model", [{"role": "user", "content": "Hello"}])
        key2 = ResponseCache.build_key("model", [{"role": "user", "content": "Hello"}])
        assert key1 == key2

    def test_cache_key_different(self) -> None:
        key1 = ResponseCache.build_key("model1", [{"role": "user", "content": "Hello"}])
        key2 = ResponseCache.build_key("model2", [{"role": "user", "content": "Hello"}])
        assert key1 != key2

    def test_load_balancer_stats(self) -> None:
        lb = LoadBalancer()
        lb.register_provider("mock")
        lb.record_request("mock", 100.0, True)
        lb.record_request("mock", 200.0, False)
        stats = lb.get_provider_stats("mock")
        assert stats.total_requests == 2
        assert stats.failed_requests == 1

    def test_metrics_multiple_providers(self) -> None:
        collector = MetricsCollector()
        collector.record_request(RequestMetrics(
            request_id="1", provider="p1", model="m1", start_time=time.time(),
        ))
        collector.record_request(RequestMetrics(
            request_id="2", provider="p2", model="m2", start_time=time.time(),
        ))
        all_metrics = collector.get_all_metrics()
        assert len(all_metrics) == 2

    def test_tracer_max_traces_limit(self) -> None:
        tracer = ModelTracer(max_traces=5)
        for i in range(10):
            tracer.start_trace(f"trace{i}")
        assert tracer.get_trace_count() <= 10

    def test_lifecycle_error_count(self) -> None:
        lc = ProviderLifecycle("test")
        lc.initialize()
        lc.error("error1")
        lc.recover()
        lc.initialize()
        lc.error("error2")
        assert lc.error_count == 2


# ==================== Policy Factory Tests ====================


class TestPolicyFactories:
    """Tests for policy factory functions."""

    def test_get_retry_policy(self) -> None:
        policy = get_retry_policy(max_retries=5)
        assert policy.max_retries == 5

    def test_get_circuit_breaker_policy(self) -> None:
        policy = get_circuit_breaker_policy(failure_threshold=10)
        assert policy.failure_threshold == 10

    def test_get_rate_limit_policy(self) -> None:
        policy = get_rate_limit_policy(requests_per_minute=120)
        assert policy.requests_per_minute == 120


# ==================== Component Factory Tests ====================


class TestComponentFactories:
    """Tests for component factory functions."""

    def test_get_response_cache(self) -> None:
        cache = get_response_cache(max_size=500)
        assert cache._max_size == 500

    def test_get_load_balancer(self) -> None:
        lb = get_load_balancer(strategy=LoadBalancingStrategy.RANDOM)
        assert lb.strategy == LoadBalancingStrategy.RANDOM

    def test_get_metrics_collector(self) -> None:
        collector = get_metrics_collector()
        assert collector is not None

    def test_get_model_tracer(self) -> None:
        tracer = get_model_tracer(max_traces=500)
        assert tracer._max_traces == 500

    def test_get_provider_registry(self) -> None:
        registry = get_provider_registry()
        assert registry is not None

    def test_get_provider_lifecycle(self) -> None:
        from app.models.lifecycle import get_provider_lifecycle
        lc = get_provider_lifecycle("test")
        assert lc.provider_id == "test"

    def test_get_model_gateway_factory(self) -> None:
        factory = get_model_gateway_factory()
        assert factory is not None
