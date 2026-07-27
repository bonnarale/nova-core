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
    """Tracks request/response metrics on request.state."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not hasattr(request.state, "_api_metrics"):
            request.state._api_metrics = {"requests": 0, "errors": 0}
        request.state._api_metrics["requests"] += 1
        response = await call_next(request)
        if response.status_code >= 400:
            request.state._api_metrics["errors"] += 1
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
