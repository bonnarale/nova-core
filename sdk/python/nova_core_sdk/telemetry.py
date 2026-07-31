from __future__ import annotations

import time
from typing import Any


class TelemetryCollector:
    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled
        self._spans: list[dict[str, Any]] = []
        self._metrics: dict[str, Any] = {
            "total_requests": 0,
            "total_errors": 0,
            "total_latency_ms": 0.0,
            "requests_by_endpoint": {},
            "errors_by_type": {},
        }

    def start_span(self, name: str, attributes: dict[str, Any] | None = None) -> dict[str, Any]:
        span: dict[str, Any] = {
            "name": name,
            "start_time": time.time(),
            "attributes": attributes or {},
            "end_time": None,
            "status": "ok",
        }
        return span

    def end_span(self, span: dict[str, Any], status: str = "ok") -> None:
        span["end_time"] = time.time()
        span["status"] = status
        if self.enabled:
            self._spans.append(span)

    def record_request(self, endpoint: str, latency_ms: float, status_code: int) -> None:
        if not self.enabled:
            return
        self._metrics["total_requests"] += 1
        self._metrics["total_latency_ms"] += latency_ms
        if status_code >= 400:
            self._metrics["total_errors"] += 1
        endpoint_counts = self._metrics["requests_by_endpoint"]
        endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1

    def record_error(self, error_type: str) -> None:
        if not self.enabled:
            return
        errors = self._metrics["errors_by_type"]
        errors[error_type] = errors.get(error_type, 0) + 1

    def get_metrics(self) -> dict[str, Any]:
        return dict(self._metrics)

    def get_spans(self) -> list[dict[str, Any]]:
        return list(self._spans)

    def reset(self) -> None:
        self._spans.clear()
        self._metrics = {
            "total_requests": 0,
            "total_errors": 0,
            "total_latency_ms": 0.0,
            "requests_by_endpoint": {},
            "errors_by_type": {},
        }
