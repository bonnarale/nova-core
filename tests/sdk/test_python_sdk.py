from __future__ import annotations

import pytest
from nova_core_sdk.configuration import Configuration
from nova_core_sdk.auth import APIKeyAuth, BearerTokenAuth, create_auth
from nova_core_sdk.exceptions import (
    NovaError,
    NovaAPIError,
    NovaAuthError,
    NovaRateLimitError,
    NovaServerError,
    NovaConnectionError,
    NovaTimeoutError,
    NovaValidationError,
)
from nova_core_sdk.retry import RetryHandler
from nova_core_sdk.middleware import Middleware, TelemetryMiddleware
from nova_core_sdk.hooks import HookManager
from nova_core_sdk.telemetry import TelemetryCollector
from nova_core_sdk.models import (
    ChatRequestModel,
    CreateAgentRequest,
    CreateGoalRequest,
    CreateTaskRequest,
    RAGQueryRequest,
    RAGIndexDocRequest,
    WorkflowCreate,
)
from nova_core_sdk.responses import (
    APIResponse,
    PaginatedResponse,
    PaginationInfo,
    HealthResponse,
    ChatResponse,
    AgentResponse,
    GoalResponse,
    TaskResponse,
    WorkflowResponse,
    EntityResponse,
    RAGQueryResponse,
)
from nova_core_sdk.pagination import PageIterator, AsyncPageIterator


# ── Configuration ──────────────────────────────────────────────
class TestConfiguration:
    def test_default_values(self) -> None:
        config = Configuration()
        assert config.base_url == "http://localhost:8000"
        assert config.api_key is None
        assert config.bearer_token is None
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.verify_ssl is True
        assert config.telemetry_enabled is False

    def test_strips_trailing_slash(self) -> None:
        config = Configuration(base_url="http://localhost:8000/")
        assert config.base_url == "http://localhost:8000"

    def test_api_key_auth_headers(self) -> None:
        config = Configuration(api_key="test-key-123")
        headers = config.get_auth_headers()
        assert headers == {"X-API-Key": "test-key-123"}

    def test_bearer_token_auth_headers(self) -> None:
        config = Configuration(bearer_token="tok-abc")
        headers = config.get_auth_headers()
        assert headers == {"Authorization": "Bearer tok-abc"}

    def test_bearer_takes_precedence(self) -> None:
        config = Configuration(api_key="key1", bearer_token="tok1")
        headers = config.get_auth_headers()
        assert headers == {"Authorization": "Bearer tok1"}

    def test_no_auth(self) -> None:
        config = Configuration()
        headers = config.get_auth_headers()
        assert headers == {}

    def test_default_headers_include_content_type(self) -> None:
        config = Configuration()
        headers = config.get_default_headers()
        assert headers["Content-Type"] == "application/json"

    def test_custom_headers_merged(self) -> None:
        config = Configuration(headers={"X-Custom": "value"})
        headers = config.get_default_headers()
        assert headers["X-Custom"] == "value"


# ── Auth ───────────────────────────────────────────────────────
class TestAuth:
    def test_api_key_auth(self) -> None:
        config = Configuration()
        auth = APIKeyAuth(config, "my-key")
        assert auth.get_headers() == {"X-API-Key": "my-key"}

    def test_bearer_token_auth(self) -> None:
        config = Configuration()
        auth = BearerTokenAuth(config, "my-token")
        assert auth.get_headers() == {"Authorization": "Bearer my-token"}

    def test_create_auth_bearer(self) -> None:
        config = Configuration(bearer_token="tok")
        auth = create_auth(config)
        assert isinstance(auth, BearerTokenAuth)

    def test_create_auth_api_key(self) -> None:
        config = Configuration(api_key="key")
        auth = create_auth(config)
        assert isinstance(auth, APIKeyAuth)

    def test_create_auth_none(self) -> None:
        config = Configuration()
        auth = create_auth(config)
        assert auth.get_headers() == {}


# ── Exceptions ─────────────────────────────────────────────────
class TestExceptions:
    def test_nova_error_base(self) -> None:
        exc = NovaError("test error")
        assert str(exc) == "test error"
        assert exc.status_code is None

    def test_auth_error_inherits_api(self) -> None:
        exc = NovaAuthError("unauthorized")
        assert isinstance(exc, NovaAPIError)
        assert isinstance(exc, NovaError)

    def test_rate_limit_error_fields(self) -> None:
        exc = NovaRateLimitError("limited", retry_after=30.0)
        assert exc.retry_after == 30.0

    def test_validation_error_fields(self) -> None:
        exc = NovaValidationError("invalid", errors=[{"field": "name"}])
        assert len(exc.errors) == 1


# ── Retry ──────────────────────────────────────────────────────
class TestRetryHandler:
    def test_delay_calculation(self) -> None:
        handler = RetryHandler(max_retries=3, base_delay=0.5, max_delay=30.0, backoff=2.0)
        assert handler.calculate_delay(0) == 0.5
        assert handler.calculate_delay(1) == 1.0
        assert handler.calculate_delay(2) == 2.0

    def test_delay_capped_at_max(self) -> None:
        handler = RetryHandler(max_retries=10, base_delay=1.0, max_delay=5.0, backoff=2.0)
        assert handler.calculate_delay(10) == 5.0

    def test_retry_after_override(self) -> None:
        handler = RetryHandler()
        assert handler.calculate_delay(0, retry_after=10.0) == 10.0

    def test_should_retry_within_limit(self) -> None:
        handler = RetryHandler(max_retries=3)
        assert handler.should_retry(0, 500) is True
        assert handler.should_retry(2, 500) is True
        assert handler.should_retry(3, 500) is False

    def test_should_retry_status_codes(self) -> None:
        handler = RetryHandler(max_retries=5)
        assert handler.should_retry(0, 429) is True
        assert handler.should_retry(0, 500) is True
        assert handler.should_retry(0, 502) is True
        assert handler.should_retry(0, 503) is True
        assert handler.should_retry(0, 504) is True
        assert handler.should_retry(0, 400) is False
        assert handler.should_retry(0, 401) is False
        assert handler.should_retry(0, 404) is False


# ── Middleware ──────────────────────────────────────────────────
class TestMiddleware:
    def test_process_request(self) -> None:
        mw = Middleware()
        ctx = mw.process_request("GET", "/health", {"Content-Type": "application/json"})
        assert ctx["method"] == "GET"
        assert ctx["url"] == "/health"

    def test_request_hook_modification(self) -> None:
        mw = Middleware()
        mw.add_request_hook(lambda ctx: {**ctx, "headers": {**ctx["headers"], "X-Added": "yes"}})
        ctx = mw.process_request("GET", "/test", {})
        assert ctx["headers"]["X-Added"] == "yes"

    def test_response_hook(self) -> None:
        mw = Middleware()
        mw.add_response_hook(lambda resp: {**resp, "processed": True})
        result = mw.process_response({"status": 200})
        assert result["processed"] is True

    def test_error_hook(self) -> None:
        mw = Middleware()
        mw.add_error_hook(lambda err: Exception("wrapped"))
        result = mw.process_error(Exception("original"))
        assert str(result) == "wrapped"


class TestTelemetryMiddleware:
    def test_counts_requests(self) -> None:
        mw = TelemetryMiddleware()
        mw.process_request("GET", "/test", {})
        mw.process_response({"_start_time": 0})
        assert mw.metrics["requests"] == 1

    def test_counts_errors(self) -> None:
        mw = TelemetryMiddleware()
        mw.process_error(Exception("fail"))
        assert mw.metrics["errors"] == 1


# ── Hooks ──────────────────────────────────────────────────────
class TestHookManager:
    def test_register_and_emit(self) -> None:
        hm = HookManager()
        results = []
        hm.register("test", lambda x: results.append(x))
        hm.emit("test", "hello")
        assert results == ["hello"]

    def test_unregister(self) -> None:
        hm = HookManager()
        fn = lambda: None
        hm.register("test", fn)
        hm.unregister("test", fn)
        assert hm.emit("test") == []

    def test_clear_event(self) -> None:
        hm = HookManager()
        hm.register("a", lambda: 1)
        hm.register("b", lambda: 2)
        hm.clear("a")
        assert hm.emit("a") == []
        assert hm.emit("b") == [2]

    def test_clear_all(self) -> None:
        hm = HookManager()
        hm.register("a", lambda: 1)
        hm.clear()
        assert hm.emit("a") == []


# ── Telemetry ──────────────────────────────────────────────────
class TestTelemetryCollector:
    def test_disabled_no_records(self) -> None:
        tc = TelemetryCollector(enabled=False)
        tc.record_request("/test", 10.0, 200)
        assert tc.get_metrics()["total_requests"] == 0

    def test_enabled_records(self) -> None:
        tc = TelemetryCollector(enabled=True)
        tc.record_request("/test", 10.0, 200)
        tc.record_request("/test2", 20.0, 400)
        metrics = tc.get_metrics()
        assert metrics["total_requests"] == 2
        assert metrics["total_errors"] == 1
        assert metrics["total_latency_ms"] == 30.0

    def test_span_lifecycle(self) -> None:
        tc = TelemetryCollector(enabled=True)
        span = tc.start_span("op1", {"key": "val"})
        assert span["name"] == "op1"
        tc.end_span(span, "ok")
        assert span["status"] == "ok"
        assert span["end_time"] is not None

    def test_reset(self) -> None:
        tc = TelemetryCollector(enabled=True)
        tc.record_request("/test", 10.0, 200)
        tc.reset()
        assert tc.get_metrics()["total_requests"] == 0


# ── Models ─────────────────────────────────────────────────────
class TestModels:
    def test_chat_request_model(self) -> None:
        m = ChatRequestModel(model="llama3.2", messages=[{"role": "user", "content": "hi"}])
        assert m.model == "llama3.2"
        assert m.use_cache is True
        assert m.stream is False

    def test_create_agent_request(self) -> None:
        m = CreateAgentRequest(id="a1", name="Agent 1", role="analyst")
        assert m.id == "a1"
        assert m.memory_scope == "session"
        assert m.allowed_tools == []

    def test_create_goal_request(self) -> None:
        m = CreateGoalRequest(title="Goal 1")
        assert m.priority == 3

    def test_create_task_request(self) -> None:
        m = CreateTaskRequest(goal="do something")
        assert m.goal == "do something"
        assert m.plan is None

    def test_rag_query_request(self) -> None:
        m = RAGQueryRequest(query="test")
        assert m.top_k == 10
        assert m.threshold == 0.0

    def test_rag_index_request(self) -> None:
        m = RAGIndexDocRequest(content="hello world")
        assert m.chunk_size == 512

    def test_workflow_create(self) -> None:
        m = WorkflowCreate(name="test workflow")
        assert m.version == "1.0.0"
        assert m.steps == []


# ── Responses ──────────────────────────────────────────────────
class TestResponses:
    def test_api_response_defaults(self) -> None:
        r = APIResponse()
        assert r.success is True
        assert r.errors == []

    def test_paginated_response(self) -> None:
        r = PaginatedResponse(data=[1, 2, 3], pagination={"total": 10})
        assert len(r.data) == 3

    def test_health_response(self) -> None:
        r = HealthResponse()
        assert r.status == "ok"

    def test_chat_response(self) -> None:
        r = ChatResponse(model="gpt-4")
        assert r.cache_hit is False

    def test_agent_response(self) -> None:
        r = AgentResponse(id="a1", name="Agent")
        assert r.status == "active"

    def test_entity_response(self) -> None:
        r = EntityResponse(id="e1", type="PERSON", name="John")
        assert r.confidence == 1.0

    def test_rag_query_response(self) -> None:
        r = RAGQueryResponse(query="test")
        assert r.chunks_count == 0


# ── Pagination ─────────────────────────────────────────────────
class TestPagination:
    def test_page_iterator_all_empty(self) -> None:
        class MockClient:
            def _request(self, method: str, path: str, params: dict | None = None) -> dict:
                return {"data": []}

        client = MockClient()
        iterator = PageIterator(client, "GET", "/tasks", page_size=10)
        result = iterator.all()
        assert result == []
