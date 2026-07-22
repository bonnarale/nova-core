"""Metrics collection for model providers."""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """Metrics for a single request."""

    request_id: str
    provider: str
    model: str
    start_time: float
    end_time: Optional[float] = None
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: float = 0.0
    success: bool = True
    error_type: Optional[str] = None
    cache_hit: bool = False

    def complete(self, success: bool = True, error_type: Optional[str] = None) -> None:
        self.end_time = time.time()
        self.latency_ms = (self.end_time - self.start_time) * 1000
        self.success = success
        self.error_type = error_type


@dataclass
class ProviderMetrics:
    """Aggregated metrics for a provider."""

    provider_id: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_latency_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    error_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    request_history: list[RequestMetrics] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    @property
    def average_latency(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    @property
    def total_cost(self) -> float:
        return 0.0

    def record_request(self, metrics: RequestMetrics) -> None:
        self.total_requests += 1
        if metrics.success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if metrics.error_type:
                self.error_counts[metrics.error_type] += 1
        self.total_tokens_input += metrics.tokens_input
        self.total_tokens_output += metrics.tokens_output
        self.total_latency_ms += metrics.latency_ms
        if metrics.cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        self.request_history.append(metrics)
        if len(self.request_history) > 1000:
            self.request_history = self.request_history[-500:]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.success_rate,
            "total_tokens_input": self.total_tokens_input,
            "total_tokens_output": self.total_tokens_output,
            "average_latency": self.average_latency,
            "cache_hit_rate": self.cache_hit_rate,
            "error_counts": dict(self.error_counts),
        }


class MetricsCollector:
    """Collects and aggregates metrics across providers."""

    def __init__(self) -> None:
        self._provider_metrics: dict[str, ProviderMetrics] = {}
        self._request_count = 0
        self._start_time = time.time()

    def record_request(self, metrics: RequestMetrics) -> None:
        self._request_count += 1
        if metrics.provider not in self._provider_metrics:
            self._provider_metrics[metrics.provider] = ProviderMetrics(provider_id=metrics.provider)
        self._provider_metrics[metrics.provider].record_request(metrics)

    def get_provider_metrics(self, provider_id: str) -> Optional[ProviderMetrics]:
        return self._provider_metrics.get(provider_id)

    def get_all_metrics(self) -> dict[str, ProviderMetrics]:
        return dict(self._provider_metrics)

    def get_summary(self) -> dict[str, Any]:
        total_requests = sum(m.total_requests for m in self._provider_metrics.values())
        total_successful = sum(m.successful_requests for m in self._provider_metrics.values())
        total_failed = sum(m.failed_requests for m in self._provider_metrics.values())
        total_latency = sum(m.total_latency_ms for m in self._provider_metrics.values())
        uptime_seconds = time.time() - self._start_time
        return {
            "total_requests": total_requests,
            "successful_requests": total_successful,
            "failed_requests": total_failed,
            "success_rate": total_successful / total_requests if total_requests > 0 else 0.0,
            "average_latency": total_latency / total_requests if total_requests > 0 else 0.0,
            "uptime_seconds": uptime_seconds,
            "requests_per_second": total_requests / uptime_seconds if uptime_seconds > 0 else 0.0,
            "provider_count": len(self._provider_metrics),
        }

    def reset(self) -> None:
        self._provider_metrics.clear()
        self._request_count = 0
        self._start_time = time.time()


def get_metrics_collector() -> MetricsCollector:
    return MetricsCollector()
