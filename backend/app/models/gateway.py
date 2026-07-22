"""Model Gateway - top-level orchestrator for model provider operations."""

import asyncio
import logging
import time
from typing import Any, AsyncIterator, Optional

from app.models.cache import ResponseCache, get_response_cache
from app.models.capabilities import ModelCapabilities
from app.models.context import ModelContext, RequestStatus
from app.models.lifecycle import ProviderState
from app.models.load_balancer import LoadBalancer, LoadBalancingStrategy, get_load_balancer
from app.models.metrics import MetricsCollector, RequestMetrics, get_metrics_collector
from app.models.policies import (
    CircuitBreakerPolicy,
    FallbackPolicy,
    RateLimitPolicy,
    RetryPolicy,
    RetryStrategy,
)
from app.models.registry import ProviderRegistry, get_provider_registry
from app.models.router import ModelRouter
from app.models.tracing import ModelTracer, get_model_tracer

logger = logging.getLogger(__name__)


class GatewayError(Exception):
    """Base exception for gateway errors."""


class ProviderNotFoundError(GatewayError):
    """Raised when a provider is not found."""


class RequestFailedError(GatewayError):
    """Raised when a request fails after all retries."""


class ModelGateway:
    """Top-level orchestrator for model provider operations.

    Coordinates routing, caching, retry, circuit breaking, load balancing,
    metrics, and tracing across all registered providers.
    """

    def __init__(
        self,
        registry: Optional[ProviderRegistry] = None,
        router: Optional[ModelRouter] = None,
        cache: Optional[ResponseCache] = None,
        load_balancer: Optional[LoadBalancer] = None,
        metrics: Optional[MetricsCollector] = None,
        tracer: Optional[ModelTracer] = None,
    ) -> None:
        self._registry = registry or get_provider_registry()
        self._cache = cache or get_response_cache()
        self._load_balancer = load_balancer or get_load_balancer()
        self._metrics = metrics or get_metrics_collector()
        self._tracer = tracer or get_model_tracer()
        self._router = router or ModelRouter(
            registry=self._registry,
            load_balancer=self._load_balancer,
        )
        self._initialized = False
        self._request_count = 0

    @property
    def registry(self) -> ProviderRegistry:
        return self._registry

    @property
    def router(self) -> ModelRouter:
        return self._router

    @property
    def cache(self) -> ResponseCache:
        return self._cache

    @property
    def load_balancer(self) -> LoadBalancer:
        return self._load_balancer

    @property
    def metrics(self) -> MetricsCollector:
        return self._metrics

    @property
    def tracer(self) -> ModelTracer:
        return self._tracer

    async def initialize(self) -> None:
        if self._initialized:
            return
        results = await self._registry.initialize_all()
        failed = [pid for pid, ok in results.items() if not ok]
        if failed:
            logger.warning("Some providers failed to initialize: %s", failed)
        self._initialized = True
        logger.info("Model gateway initialized with %d providers", len(results))

    async def shutdown(self) -> None:
        if not self._initialized:
            return
        await self._registry.shutdown_all()
        self._initialized = False
        logger.info("Model gateway shutdown")

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        provider: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        priority: str = "normal",
        use_cache: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        from uuid import UUID
        context = ModelContext(
            agent_id=agent_id,
            session_id=UUID(session_id) if session_id else None,
            user_id=user_id,
            provider=provider,
            model=model,
            messages=messages,
            parameters=kwargs,
        )

        if use_cache:
            cache_key = self._cache.build_key(model, messages, **kwargs)
            cached = self._cache.get(cache_key)
            if cached is not None:
                context.cache_hit = True
                context.mark_completed()
                return cached

        trace = self._tracer.start_trace("chat", {"model": model, "provider": provider})
        span = self._tracer.start_span("chat_request", trace, provider or "", model)

        start_time = time.time()
        last_error = None
        selected_provider = None

        try:
            selected_provider = self._select_provider(context)
            context.provider = selected_provider

            self._tracer.finish_span(span, "executing")
            exec_span = self._tracer.start_span("execute", trace, selected_provider, model)

            provider_instance = self._registry.get(selected_provider)
            if not provider_instance:
                raise ProviderNotFoundError(f"Provider {selected_provider} not found")

            result = await asyncio.wait_for(
                provider_instance.chat(model, messages, **kwargs),
                timeout=context.timeout,
            )

            latency_ms = (time.time() - start_time) * 1000
            self._tracer.finish_span(exec_span, "completed")
            self._tracer.finish_trace(trace, "completed")

            self._router.record_success(selected_provider)
            self._load_balancer.record_request(selected_provider, latency_ms, True)

            tokens_input = result.get("usage", {}).get("prompt_tokens", 0)
            tokens_output = result.get("usage", {}).get("completion_tokens", 0)
            self._metrics.record_request(RequestMetrics(
                request_id=str(context.request_id),
                provider=selected_provider,
                model=model,
                start_time=start_time,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                latency_ms=latency_ms,
                success=True,
            ))

            context.tokens_input = tokens_input
            context.tokens_output = tokens_output
            context.mark_completed()

            if use_cache:
                self._cache.set(cache_key, result)

            return result

        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            context.mark_timed_out()
            self._tracer.finish_span(span, "timeout", "Request timed out")
            self._tracer.finish_trace(trace, "timeout")
            if selected_provider:
                self._router.record_failure(selected_provider)
                self._load_balancer.record_request(selected_provider, latency_ms, False)
                self._metrics.record_request(RequestMetrics(
                    request_id=str(context.request_id),
                    provider=selected_provider,
                    model=model,
                    start_time=start_time,
                    latency_ms=latency_ms,
                    success=False,
                    error_type="timeout",
                ))
            last_error = "Request timed out"

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_type = type(e).__name__
            context.mark_failed(str(e), error_type)
            self._tracer.finish_span(span, "error", str(e))
            self._tracer.finish_trace(trace, "error")
            if selected_provider:
                self._router.record_failure(selected_provider)
                self._load_balancer.record_request(selected_provider, latency_ms, False)
                self._metrics.record_request(RequestMetrics(
                    request_id=str(context.request_id),
                    provider=selected_provider,
                    model=model,
                    start_time=start_time,
                    latency_ms=latency_ms,
                    success=False,
                    error_type=error_type,
                ))
            last_error = str(e)

        if context.can_retry():
            context.mark_retrying()
            delay = self._router.get_retry_delay(context.attempt)
            logger.info("Retrying request %s (attempt %d) after %.1fs", context.request_id, context.attempt, delay)
            await asyncio.sleep(delay)
            return await self._execute_with_retry(context, trace)

        if selected_provider:
            fallback = self._router.get_fallback_provider(selected_provider)
            if fallback:
                logger.info("Falling back from %s to %s", selected_provider, fallback)
                context.provider = fallback
                try:
                    provider_instance = self._registry.get(fallback)
                    if provider_instance:
                        result = await asyncio.wait_for(
                            provider_instance.chat(model, messages, **kwargs),
                            timeout=context.timeout,
                        )
                        context.mark_completed()
                        return result
                except Exception as fb_error:
                    logger.error("Fallback also failed: %s", fb_error)

        raise RequestFailedError(f"Request failed: {last_error}")

    async def _execute_with_retry(self, context: ModelContext, trace: Any) -> dict[str, Any]:
        selected_provider = self._select_provider(context)
        context.provider = selected_provider

        span = self._tracer.start_span("retry_execute", trace, selected_provider, context.model or "")
        start_time = time.time()

        try:
            provider_instance = self._registry.get(selected_provider)
            if not provider_instance:
                raise ProviderNotFoundError(f"Provider {selected_provider} not found")

            result = await asyncio.wait_for(
                provider_instance.chat(context.model or "", context.messages, **context.parameters),
                timeout=context.timeout,
            )

            latency_ms = (time.time() - start_time) * 1000
            self._tracer.finish_span(span, "completed")
            self._router.record_success(selected_provider)
            self._load_balancer.record_request(selected_provider, latency_ms, True)
            self._metrics.record_request(RequestMetrics(
                request_id=str(context.request_id),
                provider=selected_provider,
                model=context.model or "",
                start_time=start_time,
                latency_ms=latency_ms,
                success=True,
            ))
            context.mark_completed()
            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._tracer.finish_span(span, "error", str(e))
            self._router.record_failure(selected_provider)
            self._load_balancer.record_request(selected_provider, latency_ms, False)
            self._metrics.record_request(RequestMetrics(
                request_id=str(context.request_id),
                provider=selected_provider,
                model=context.model or "",
                start_time=start_time,
                latency_ms=latency_ms,
                success=False,
                error_type=type(e).__name__,
            ))
            raise

    def _select_provider(self, context: ModelContext) -> str:
        available = self._router._get_available_providers()
        if not available:
            raise GatewayError("No providers available")
        return self._router.select_provider(context, available)

    async def chat_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        provider: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        context = ModelContext(provider=provider, model=model, messages=messages, parameters=kwargs)
        selected_provider = provider or self._select_provider(context)
        provider_instance = self._registry.get(selected_provider)
        if not provider_instance:
            raise ProviderNotFoundError(f"Provider {selected_provider} not found")
        async for chunk in provider_instance.chat_stream(model, messages, **kwargs):
            yield chunk

    async def list_models(self, provider: Optional[str] = None) -> list[str]:
        if provider:
            provider_instance = self._registry.get(provider)
            if not provider_instance:
                raise ProviderNotFoundError(f"Provider {provider} not found")
            return await provider_instance.list_models()
        all_models = []
        for pid in self._registry.list_active_providers():
            try:
                provider_instance = self._registry.get(pid)
                if provider_instance:
                    models = await provider_instance.list_models()
                    all_models.extend([f"{pid}:{m}" for m in models])
            except Exception as e:
                logger.warning("Failed to list models from %s: %s", pid, e)
        return all_models

    async def health(self) -> dict[str, Any]:
        return await self._registry.health_check_all()

    def get_metrics_summary(self) -> dict[str, Any]:
        return {
            "gateway": {
                "initialized": self._initialized,
                "request_count": self._request_count,
            },
            "registry": self._registry.to_dict(),
            "metrics": self._metrics.get_summary(),
            "cache": self._cache.get_stats(),
            "load_balancer": self._load_balancer.to_dict(),
            "tracer": self._tracer.to_dict(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "initialized": self._initialized,
            "request_count": self._request_count,
            "provider_count": self._registry.provider_count,
            "active_providers": self._registry.active_count,
        }
