from __future__ import annotations

import pytest
from nova_core_sdk.telemetry import TelemetryCollector


class TestTelemetryCollector:
    def test_disabled_no_records(self) -> None:
        tc = TelemetryCollector(enabled=False)
        tc.record_request("/test", 10.0, 200)
        assert tc.get_metrics()["total_requests"] == 0

    def test_enabled_records_requests(self) -> None:
        tc = TelemetryCollector(enabled=True)
        tc.record_request("/test", 10.0, 200)
        tc.record_request("/test", 15.0, 200)
        metrics = tc.get_metrics()
        assert metrics["total_requests"] == 2
        assert metrics["total_latency_ms"] == 25.0

    def test_records_errors(self) -> None:
        tc = TelemetryCollector(enabled=True)
        tc.record_request("/test", 10.0, 500)
        assert tc.get_metrics()["total_errors"] == 1

    def test_records_by_endpoint(self) -> None:
        tc = TelemetryCollector(enabled=True)
        tc.record_request("/a", 10.0, 200)
        tc.record_request("/a", 10.0, 200)
        tc.record_request("/b", 10.0, 200)
        endpoints = tc.get_metrics()["requests_by_endpoint"]
        assert endpoints["/a"] == 2
        assert endpoints["/b"] == 1

    def test_record_error_type(self) -> None:
        tc = TelemetryCollector(enabled=True)
        tc.record_error("NovaAPIError")
        tc.record_error("NovaAPIError")
        tc.record_error("NovaTimeoutError")
        errors = tc.get_metrics()["errors_by_type"]
        assert errors["NovaAPIError"] == 2
        assert errors["NovaTimeoutError"] == 1

    def test_span_lifecycle(self) -> None:
        tc = TelemetryCollector(enabled=True)
        span = tc.start_span("op1")
        assert span["status"] == "ok"
        tc.end_span(span, "error")
        assert span["status"] == "error"
        assert span["end_time"] is not None

    def test_get_spans(self) -> None:
        tc = TelemetryCollector(enabled=True)
        span_a = tc.start_span("a")
        span_b = tc.start_span("b")
        tc.end_span(span_a)
        tc.end_span(span_b)
        assert len(tc.get_spans()) == 2

    def test_reset(self) -> None:
        tc = TelemetryCollector(enabled=True)
        tc.record_request("/test", 10.0, 200)
        tc.start_span("op")
        tc.reset()
        assert tc.get_metrics()["total_requests"] == 0
        assert len(tc.get_spans()) == 0
