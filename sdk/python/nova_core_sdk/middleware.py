from __future__ import annotations

from typing import Any, Callable


class Middleware:
    def __init__(self) -> None:
        self._request_hooks: list[Callable[..., Any]] = []
        self._response_hooks: list[Callable[..., Any]] = []
        self._error_hooks: list[Callable[..., Any]] = []

    def add_request_hook(self, hook: Callable[..., Any]) -> None:
        self._request_hooks.append(hook)

    def add_response_hook(self, hook: Callable[..., Any]) -> None:
        self._response_hooks.append(hook)

    def add_error_hook(self, hook: Callable[..., Any]) -> None:
        self._error_hooks.append(hook)

    def process_request(self, method: str, url: str, headers: dict[str, str], body: Any = None) -> dict[str, Any]:
        context: dict[str, Any] = {"method": method, "url": url, "headers": headers, "body": body}
        for hook in self._request_hooks:
            result = hook(context)
            if isinstance(result, dict):
                context = result
        return context

    def process_response(self, response: dict[str, Any]) -> dict[str, Any]:
        result = response
        for hook in self._response_hooks:
            output = hook(result)
            if isinstance(output, dict):
                result = output
        return result

    def process_error(self, error: Exception) -> Exception:
        result = error
        for hook in self._error_hooks:
            output = hook(result)
            if isinstance(output, Exception):
                result = output
        return result


class LoggingMiddleware(Middleware):
    def __init__(self, logger: Any = None) -> None:
        super().__init__()
        self._logger = logger

    def process_request(self, method: str, url: str, headers: dict[str, str], body: Any = None) -> dict[str, Any]:
        if self._logger:
            self._logger.debug(f"SDK Request: {method} {url}")
        return super().process_request(method, url, headers, body)

    def process_response(self, response: dict[str, Any]) -> dict[str, Any]:
        if self._logger:
            self._logger.debug(f"SDK Response: {response.get('status_code', 'unknown')}")
        return super().process_response(response)


class TelemetryMiddleware(Middleware):
    def __init__(self) -> None:
        super().__init__()
        self.metrics: dict[str, Any] = {"requests": 0, "errors": 0, "total_latency_ms": 0.0}

    def process_request(self, method: str, url: str, headers: dict[str, str], body: Any = None) -> dict[str, Any]:
        import time
        context = super().process_request(method, url, headers, body)
        context["_start_time"] = time.time()
        self.metrics["requests"] += 1
        return context

    def process_response(self, response: dict[str, Any]) -> dict[str, Any]:
        import time
        start = response.get("_start_time")
        if start:
            latency = (time.time() - start) * 1000
            self.metrics["total_latency_ms"] += latency
        return super().process_response(response)

    def process_error(self, error: Exception) -> Exception:
        self.metrics["errors"] += 1
        return super().process_error(error)
