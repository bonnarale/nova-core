"""API metrics collection."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)


class APIMetricsCollector:
    """Collects request, response, latency, throughput, and error metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._total_requests = 0
        self._total_responses = 0
        self._total_errors = 0
        self._latencies: list[float] = []
        self._endpoint_usage: dict[str, int] = {}
        self._start_time = time.time()

    def record_request(self, path: str = "", method: str = "GET") -> None:
        with self._lock:
            self._total_requests += 1
            key = f"{method} {path}"
            self._endpoint_usage[key] = self._endpoint_usage.get(key, 0) + 1

    def record_response(self, path: str = "", status_code: int = 200) -> None:
        with self._lock:
            self._total_responses += 1
            if status_code >= 400:
                self._total_errors += 1

    def record_latency(self, latency_ms: float) -> None:
        with self._lock:
            self._latencies.append(latency_ms)
            if len(self._latencies) > 10000:
                self._latencies = self._latencies[-5000:]

    def record_error(self, path: str = "", method: str = "GET") -> None:
        with self._lock:
            self._total_errors += 1

    def get_statistics(self) -> dict[str, Any]:
        with self._lock:
            uptime = time.time() - self._start_time
            avg_latency = (sum(self._latencies) / len(self._latencies)) if self._latencies else 0.0
            error_rate = (self._total_errors / self._total_requests * 100.0) if self._total_requests > 0 else 0.0
            throughput = self._total_requests / uptime if uptime > 0 else 0.0
            return {
                "total_requests": self._total_requests,
                "total_responses": self._total_responses,
                "total_errors": self._total_errors,
                "average_latency_ms": round(avg_latency, 2),
                "error_rate": round(error_rate, 2),
                "throughput_per_second": round(throughput, 2),
                "endpoint_usage": dict(self._endpoint_usage),
                "uptime_seconds": round(uptime, 2),
            }

    def get_endpoint_usage(self) -> dict[str, int]:
        with self._lock:
            return dict(self._endpoint_usage)

    def reset(self) -> None:
        with self._lock:
            self._total_requests = 0
            self._total_responses = 0
            self._total_errors = 0
            self._latencies.clear()
            self._endpoint_usage.clear()
            self._start_time = time.time()
