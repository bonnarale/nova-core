"""Middleware for the API Platform."""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Injects a unique request ID and tracks correlation ID."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        correlation_id = request.headers.get("X-Correlation-ID", request_id)
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Measures response time and injects timing headers."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = (time.monotonic() - start) * 1000.0
        response.headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"
        request.state.response_time_ms = elapsed_ms
        return response


class APIMetricsMiddleware(BaseHTTPMiddleware):
    """Tracks request/response metrics on request.state and accumulates into global APIMetricsCollector."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not hasattr(request.state, "_api_metrics"):
            request.state._api_metrics = {"requests": 0, "errors": 0}
        request.state._api_metrics["requests"] += 1

        # Global metrics and tracing
        api_metrics = getattr(request.app.state, "api_metrics", None)
        api_tracer = getattr(request.app.state, "api_tracer", None)
        path = request.url.path
        method = request.method
        request_id = getattr(request.state, "request_id", "")

        if api_metrics:
            api_metrics.record_request(path, method)
        trace_id = None
        if api_tracer:
            trace_id = api_tracer.start_trace(request_id, path, method)

        response = await call_next(request)

        status_code = response.status_code
        if status_code >= 400:
            request.state._api_metrics["errors"] += 1

        if api_metrics:
            api_metrics.record_response(path, status_code)
            response_time_ms = getattr(request.state, "response_time_ms", 0.0)
            if response_time_ms:
                api_metrics.record_latency(response_time_ms)
        if api_tracer and trace_id:
            status = "ok" if status_code < 400 else "error"
            api_tracer.finish_trace(trace_id, status)

        return response


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """Catches unhandled exceptions and returns a standardized JSON error."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "data": None,
                    "metadata": {},
                    "errors": [{"code": "internal_error", "message": str(exc)}],
                    "request_id": request_id,
                },
            )
