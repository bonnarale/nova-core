from __future__ import annotations

import pytest
from nova_core_sdk.middleware import Middleware, LoggingMiddleware, TelemetryMiddleware


class TestMiddleware:
    def test_process_request_passthrough(self) -> None:
        mw = Middleware()
        ctx = mw.process_request("GET", "/health", {"Content-Type": "application/json"})
        assert ctx["method"] == "GET"
        assert ctx["url"] == "/health"

    def test_request_hook_modifies(self) -> None:
        mw = Middleware()
        mw.add_request_hook(lambda ctx: {**ctx, "headers": {**ctx["headers"], "X-Test": "1"}})
        ctx = mw.process_request("POST", "/test", {})
        assert ctx["headers"]["X-Test"] == "1"

    def test_multiple_request_hooks(self) -> None:
        mw = Middleware()
        mw.add_request_hook(lambda ctx: {**ctx, "body": "first"})
        mw.add_request_hook(lambda ctx: {**ctx, "body": ctx.get("body", "") + "_second"})
        ctx = mw.process_request("GET", "/", {})
        assert ctx["body"] == "first_second"

    def test_response_hook(self) -> None:
        mw = Middleware()
        mw.add_response_hook(lambda resp: {**resp, "extra": True})
        result = mw.process_response({"status": 200})
        assert result["extra"] is True

    def test_error_hook(self) -> None:
        mw = Middleware()
        mw.add_error_hook(lambda err: Exception("wrapped"))
        result = mw.process_error(Exception("orig"))
        assert str(result) == "wrapped"


class TestLoggingMiddleware:
    def test_init(self) -> None:
        mw = LoggingMiddleware()
        assert mw._logger is None


class TestTelemetryMiddleware:
    def test_metrics_start_zero(self) -> None:
        mw = TelemetryMiddleware()
        assert mw.metrics["requests"] == 0
        assert mw.metrics["errors"] == 0

    def test_process_request_increments(self) -> None:
        mw = TelemetryMiddleware()
        mw.process_request("GET", "/test", {})
        assert mw.metrics["requests"] == 1

    def test_process_error_increments(self) -> None:
        mw = TelemetryMiddleware()
        mw.process_error(Exception("fail"))
        assert mw.metrics["errors"] == 1

    def test_process_response_calc_latency(self) -> None:
        mw = TelemetryMiddleware()
        ctx = mw.process_request("GET", "/test", {})
        import time
        time.sleep(0.01)
        mw.process_response(ctx)
        assert mw.metrics["total_latency_ms"] > 0
