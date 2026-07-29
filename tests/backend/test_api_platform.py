"""Comprehensive tests for Chapter 25 — API Platform."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest

# ─── Enums ────────────────────────────────────────────────────────────────
from app.api.enums import (
    APIVersion,
    DeprecationStatus,
    ErrorCode,
    FilterOperator,
    HTTPMethod,
    LifecycleState,
    PaginationStyle,
    ResponseFormat,
    SortDirection,
)


class TestEnums:
    def test_api_version_values(self) -> None:
        assert APIVersion.V1.value == "v1"
        assert APIVersion.V2.value == "v2"

    def test_http_method_values(self) -> None:
        assert HTTPMethod.GET.value == "GET"
        assert HTTPMethod.POST.value == "POST"
        assert HTTPMethod.DELETE.value == "DELETE"

    def test_error_code_values(self) -> None:
        assert ErrorCode.VALIDATION_ERROR.value == "validation_error"
        assert ErrorCode.RESOURCE_NOT_FOUND.value == "resource_not_found"
        assert ErrorCode.INTERNAL_ERROR.value == "internal_error"

    def test_lifecycle_state_values(self) -> None:
        assert LifecycleState.REGISTERED.value == "registered"
        assert LifecycleState.RUNNING.value == "running"
        assert LifecycleState.SHUTDOWN.value == "shutdown"

    def test_pagination_style_values(self) -> None:
        assert PaginationStyle.PAGE.value == "page"
        assert PaginationStyle.CURSOR.value == "cursor"

    def test_filter_operator_values(self) -> None:
        assert FilterOperator.EQ.value == "eq"
        assert FilterOperator.GT.value == "gt"
        assert FilterOperator.IN.value == "in"

    def test_sort_direction_values(self) -> None:
        assert SortDirection.ASC.value == "asc"
        assert SortDirection.DESC.value == "desc"

    def test_deprecation_status_values(self) -> None:
        assert DeprecationStatus.CURRENT.value == "current"
        assert DeprecationStatus.SUNSET.value == "sunset"

    def test_response_format_values(self) -> None:
        assert ResponseFormat.JSON.value == "json"
        assert ResponseFormat.CSV.value == "csv"

    def test_all_error_codes_are_strings(self) -> None:
        for ec in ErrorCode:
            assert isinstance(ec.value, str)


# ─── Models ────────────────────────────────────────────────────────────────
from app.api.models import (
    APIMetrics,
    APIResponse,
    APIStatistics,
    APIVersionInfo,
    EndpointInfo,
    ErrorDetail,
    FilterParams,
    PaginatedResponse,
    PaginationParams,
    SortParams,
)


class TestModels:
    def test_api_response_defaults(self) -> None:
        resp = APIResponse()
        assert resp.success is True
        assert resp.data is None
        assert resp.request_id == ""
        assert resp.timestamp > 0

    def test_api_response_to_dict(self) -> None:
        resp = APIResponse(success=True, data={"key": "val"}, request_id="r1")
        d = resp.to_dict()
        assert d["success"] is True
        assert d["data"] == {"key": "val"}
        assert d["request_id"] == "r1"

    def test_paginated_response_defaults(self) -> None:
        resp = PaginatedResponse()
        assert resp.success is True
        assert resp.data == []
        assert resp.pagination == {}

    def test_paginated_response_to_dict(self) -> None:
        resp = PaginatedResponse(data=[1, 2], pagination={"page": 1})
        d = resp.to_dict()
        assert d["data"] == [1, 2]
        assert d["pagination"]["page"] == 1

    def test_error_detail_to_dict(self) -> None:
        e = ErrorDetail(code="not_found", message="Missing", field="id")
        d = e.to_dict()
        assert d["code"] == "not_found"
        assert d["field"] == "id"

    def test_pagination_params_to_dict(self) -> None:
        p = PaginationParams(page=2, page_size=10)
        d = p.to_dict()
        assert d["page"] == 2
        assert d["page_size"] == 10

    def test_filter_params_to_dict(self) -> None:
        f = FilterParams(field="name", operator="eq", value="test")
        d = f.to_dict()
        assert d["field"] == "name"
        assert d["value"] == "test"

    def test_sort_params_to_dict(self) -> None:
        s = SortParams(field="created_at", direction="desc")
        d = s.to_dict()
        assert d["direction"] == "desc"

    def test_endpoint_info_to_dict(self) -> None:
        e = EndpointInfo(path="/test", method="GET", tags=["testing"])
        d = e.to_dict()
        assert d["path"] == "/test"
        assert "testing" in d["tags"]

    def test_api_metrics_to_dict(self) -> None:
        m = APIMetrics(total_requests=100, error_rate=5.0)
        d = m.to_dict()
        assert d["total_requests"] == 100
        assert d["error_rate"] == 5.0

    def test_api_version_info_to_dict(self) -> None:
        v = APIVersionInfo(version="v1", status="current")
        d = v.to_dict()
        assert d["version"] == "v1"

    def test_api_statistics_to_dict(self) -> None:
        s = APIStatistics(total_endpoints=10, endpoints_by_version={"v1": 10})
        d = s.to_dict()
        assert d["total_endpoints"] == 10


# ─── Base ABCs ─────────────────────────────────────────────────────────────
from app.api.base import (
    APIProvider,
    APIRegistry,
    APIVersionProvider,
    ErrorHandler,
    OpenAPIProvider,
    ResponseFormatter,
)


class TestBaseABCs:
    def test_cannot_instantiate_api_provider(self) -> None:
        with pytest.raises(TypeError):
            APIProvider()  # type: ignore[abstract]

    def test_cannot_instantiate_version_provider(self) -> None:
        with pytest.raises(TypeError):
            APIVersionProvider()  # type: ignore[abstract]

    def test_cannot_instantiate_registry(self) -> None:
        with pytest.raises(TypeError):
            APIRegistry()  # type: ignore[abstract]

    def test_cannot_instantiate_response_formatter(self) -> None:
        with pytest.raises(TypeError):
            ResponseFormatter()  # type: ignore[abstract]

    def test_cannot_instantiate_error_handler(self) -> None:
        with pytest.raises(TypeError):
            ErrorHandler()  # type: ignore[abstract]

    def test_cannot_instantiate_openapi_provider(self) -> None:
        with pytest.raises(TypeError):
            OpenAPIProvider()  # type: ignore[abstract]


# ─── Response Formatter ───────────────────────────────────────────────────
from app.api.response import StandardResponseFormatter
from app.api.enums import ErrorCode


class TestResponseFormatter:
    def setup_method(self) -> None:
        self.fmt = StandardResponseFormatter()

    def test_success_response(self) -> None:
        resp = self.fmt.success(data={"id": 1})
        assert resp["success"] is True
        assert resp["data"] == {"id": 1}
        assert resp["request_id"] != ""

    def test_success_with_metadata(self) -> None:
        resp = self.fmt.success(metadata={"key": "val"})
        assert resp["metadata"]["key"] == "val"

    def test_error_response(self) -> None:
        resp = self.fmt.error(ErrorCode.VALIDATION_ERROR, "bad input")
        assert resp["success"] is False
        assert resp["errors"][0]["code"] == "validation_error"

    def test_error_with_details(self) -> None:
        details = [{"code": "x", "message": "y", "field": "f", "location": "body"}]
        resp = self.fmt.error(ErrorCode.VALIDATION_ERROR, "fail", details=details)
        assert len(resp["errors"]) == 1
        assert resp["errors"][0]["field"] == "f"

    def test_paginated_response(self) -> None:
        resp = self.fmt.paginated(data=[1, 2, 3], total=10, page=1, page_size=3)
        assert resp["success"] is True
        assert resp["data"] == [1, 2, 3]
        assert resp["pagination"]["total_items"] == 10
        assert resp["pagination"]["total_pages"] == 4

    def test_paginated_empty_data(self) -> None:
        resp = self.fmt.paginated(data=[], total=0)
        assert resp["data"] == []
        assert resp["pagination"]["total_items"] == 0

    def test_paginated_has_next_previous(self) -> None:
        resp = self.fmt.paginated(data=[], total=30, page=2, page_size=10)
        assert resp["pagination"]["has_next"] is True
        assert resp["pagination"]["has_previous"] is True

    def test_cursor_paginated(self) -> None:
        resp = self.fmt.cursor_paginated(data=[1], next_cursor="abc", has_more=True)
        assert resp["pagination"]["next_cursor"] == "abc"
        assert resp["pagination"]["has_more"] is True

    def test_offset_paginated(self) -> None:
        resp = self.fmt.offset_paginated(data=[1, 2], total=5, offset=0, limit=2)
        assert resp["pagination"]["has_next"] is True
        assert resp["pagination"]["has_previous"] is False

    def test_timestamp_is_set(self) -> None:
        resp = self.fmt.success()
        assert resp["timestamp"] > 0


# ─── Error Handler ────────────────────────────────────────────────────────
from app.api.errors import StandardErrorHandler


class TestErrorHandler:
    def setup_method(self) -> None:
        self.handler = StandardErrorHandler()

    def test_handle_validation(self) -> None:
        errs = [{"code": "required", "message": "name required", "field": "name"}]
        resp = self.handler.handle_validation(errs)
        assert resp["success"] is False
        assert resp["errors"][0]["field"] == "name"

    def test_handle_not_found(self) -> None:
        resp = self.handler.handle_not_found("User")
        assert resp["success"] is False
        assert resp["errors"][0]["code"] == "resource_not_found"

    def test_handle_unauthorized(self) -> None:
        resp = self.handler.handle_unauthorized()
        assert resp["errors"][0]["code"] == "authentication_required"

    def test_handle_forbidden(self) -> None:
        resp = self.handler.handle_forbidden()
        assert resp["errors"][0]["code"] == "authorization_denied"

    def test_handle_conflict(self) -> None:
        resp = self.handler.handle_conflict("duplicate")
        assert resp["errors"][0]["code"] == "resource_conflict"

    def test_handle_rate_limit(self) -> None:
        resp = self.handler.handle_rate_limit(retry_after=30)
        assert resp["errors"][0]["code"] == "rate_limit_exceeded"
        assert resp["retry_after"] == 30

    def test_handle_internal(self) -> None:
        resp = self.handler.handle_internal()
        assert resp["errors"][0]["code"] == "internal_error"

    def test_handle_timeout(self) -> None:
        resp = self.handler.handle_timeout()
        assert resp["errors"][0]["code"] == "timeout"

    def test_handle_deprecated(self) -> None:
        resp = self.handler.handle_deprecated(sunset_date="2026-12-31")
        assert resp["errors"][0]["code"] == "deprecated"
        assert resp["sunset_date"] == "2026-12-31"

    def test_handle_dependency_failure(self) -> None:
        resp = self.handler.handle_dependency_failure("redis")
        assert resp["errors"][0]["code"] == "dependency_failure"


# ─── Pagination ────────────────────────────────────────────────────────────
from app.api.pagination import PaginationHandler


class TestPagination:
    def setup_method(self) -> None:
        self.ph = PaginationHandler()

    def test_normalize_defaults(self) -> None:
        p = self.ph.normalize()
        assert p.page == 1
        assert p.page_size == 20

    def test_normalize_clamp_page_size(self) -> None:
        p = self.ph.normalize(page_size=200)
        assert p.page_size == 100

    def test_normalize_clamp_limit(self) -> None:
        p = self.ph.normalize(limit=500)
        assert p.limit == 100

    def test_paginate_page(self) -> None:
        items = list(range(50))
        result = self.ph.paginate_page(items, total=50, page=2, page_size=10)
        assert result["items"] == list(range(10, 20))
        assert result["pagination"]["has_next"] is True
        assert result["pagination"]["has_previous"] is True

    def test_paginate_page_last(self) -> None:
        items = list(range(25))
        result = self.ph.paginate_page(items, total=25, page=3, page_size=10)
        assert result["items"] == list(range(20, 25))
        assert result["pagination"]["has_next"] is False

    def test_paginate_cursor(self) -> None:
        class Obj:
            def __init__(self, oid: str) -> None:
                self.id = oid
        items = [Obj(str(i)) for i in range(10)]
        result = self.ph.paginate_cursor(items, limit=3)
        assert len(result["items"]) == 3
        assert result["pagination"]["has_more"] is True

    def test_paginate_offset(self) -> None:
        items = list(range(30))
        result = self.ph.paginate_offset(items, total=30, offset=10, limit=10)
        assert result["items"] == list(range(10, 20))

    def test_paginate_offset_empty(self) -> None:
        result = self.ph.paginate_offset([], total=0)
        assert result["items"] == []


# ─── Filtering ─────────────────────────────────────────────────────────────
from app.api.filtering import FilteringHandler


class TestFiltering:
    def setup_method(self) -> None:
        self.fh = FilteringHandler()

    def test_parse_filters_eq(self) -> None:
        filters = self.fh.parse_filters({"name": "alice"})
        assert len(filters) == 1
        assert filters[0].operator == "eq"

    def test_parse_filters_dict(self) -> None:
        filters = self.fh.parse_filters({"age": {"operator": "gt", "value": 18}})
        assert filters[0].operator == "gt"
        assert filters[0].value == 18

    def test_apply_eq(self) -> None:
        items = [{"name": "alice"}, {"name": "bob"}, {"name": "alice"}]
        filters = self.fh.parse_filters({"name": "alice"})
        result = self.fh.apply(items, filters)
        assert len(result) == 2

    def test_apply_gt(self) -> None:
        class Item:
            def __init__(self, age: int) -> None:
                self.age = age
        items = [Item(10), Item(20), Item(30)]
        filters = self.fh.parse_filters({"age": {"operator": "gt", "value": 15}})
        result = self.fh.apply(items, filters)
        assert len(result) == 2

    def test_apply_contains(self) -> None:
        items = [{"name": "hello world"}, {"name": "goodbye"}]
        filters = self.fh.parse_filters({"name": {"operator": "contains", "value": "hello"}})
        result = self.fh.apply(items, filters)
        assert len(result) == 1

    def test_apply_no_match(self) -> None:
        items = [{"name": "a"}, {"name": "b"}]
        filters = self.fh.parse_filters({"name": "z"})
        result = self.fh.apply(items, filters)
        assert len(result) == 0


# ─── Sorting ───────────────────────────────────────────────────────────────
from app.api.sorting import SortingHandler


class TestSorting:
    def setup_method(self) -> None:
        self.sh = SortingHandler()

    def test_parse_sort_string(self) -> None:
        params = self.sh.parse_sort("-created_at,name")
        assert len(params) == 2
        assert params[0].direction == "desc"
        assert params[1].direction == "asc"

    def test_parse_sort_empty(self) -> None:
        params = self.sh.parse_sort("")
        assert len(params) == 1
        assert params[0].field == "created_at"

    def test_parse_sort_list(self) -> None:
        params = self.sh.parse_sort(["-age", "+name"])
        assert params[0].direction == "desc"
        assert params[1].direction == "asc"

    def test_sort_dicts(self) -> None:
        items = [{"name": "b"}, {"name": "a"}, {"name": "c"}]
        params = self.sh.parse_sort("name")
        result = self.sh.sort(items, params)
        assert [i["name"] for i in result] == ["a", "b", "c"]

    def test_sort_dicts_desc(self) -> None:
        items = [{"name": "b"}, {"name": "a"}, {"name": "c"}]
        params = self.sh.parse_sort("-name")
        result = self.sh.sort(items, params)
        assert [i["name"] for i in result] == ["c", "b", "a"]

    def test_sort_objects(self) -> None:
        class Obj:
            def __init__(self, n: int) -> None:
                self.n = n
        items = [Obj(3), Obj(1), Obj(2)]
        params = self.sh.parse_sort("n")
        result = self.sh.sort(items, params)
        assert [i.n for i in result] == [1, 2, 3]


# ─── Versioning ────────────────────────────────────────────────────────────
from app.api.versioning import DefaultAPIVersionProvider


class TestVersioning:
    def setup_method(self) -> None:
        self.vp = DefaultAPIVersionProvider()

    def test_get_version(self) -> None:
        assert self.vp.get_version() == "v1"

    def test_supported_versions(self) -> None:
        versions = self.vp.get_supported_versions()
        assert "v1" in versions

    def test_is_deprecated_false(self) -> None:
        assert self.vp.is_deprecated("v1") is False

    def test_is_deprecated_unknown(self) -> None:
        assert self.vp.is_deprecated("v99") is True

    def test_negotiate_default(self) -> None:
        assert self.vp.negotiate(None) == "v1"

    def test_negotiate_v2(self) -> None:
        assert self.vp.negotiate("application/vnd.nova.v2+json") == "v2"

    def test_get_version_info(self) -> None:
        info = self.vp.get_version_info("v1")
        assert info is not None
        assert info.version == "v1"

    def test_get_all_version_info(self) -> None:
        all_info = self.vp.get_all_version_info()
        assert len(all_info) >= 1

    def test_add_version(self) -> None:
        from app.api.models import APIVersionInfo
        self.vp.add_version(APIVersionInfo(version="v3", status="current"))
        assert "v3" in self.vp.get_supported_versions()

    def test_set_default(self) -> None:
        self.vp.set_default("v2")
        assert self.vp.get_version() == "v2"


# ─── Registry ──────────────────────────────────────────────────────────────
from app.api.registry import DefaultAPIRegistry


class TestRegistry:
    def setup_method(self) -> None:
        self.reg = DefaultAPIRegistry()

    def test_register_endpoint(self) -> None:
        self.reg.register_endpoint("/test", "GET", None, tags=["test"])
        assert self.reg.count() == 1

    def test_get_endpoint(self) -> None:
        self.reg.register_endpoint("/users", "GET", None, tags=["users"])
        ep = self.reg.get_endpoint("/users", "GET")
        assert ep is not None
        assert ep["path"] == "/users"

    def test_get_endpoint_not_found(self) -> None:
        assert self.reg.get_endpoint("/none", "GET") is None

    def test_list_by_tag(self) -> None:
        self.reg.register_endpoint("/a", "GET", None, tags=["alpha"])
        self.reg.register_endpoint("/b", "GET", None, tags=["beta"])
        result = self.reg.list_by_tag("alpha")
        assert len(result) == 1

    def test_list_by_version(self) -> None:
        self.reg.register_endpoint("/v1", "GET", None, version="v1")
        self.reg.register_endpoint("/v2", "GET", None, version="v2")
        result = self.reg.list_by_version("v1")
        assert len(result) == 1

    def test_list_deprecated(self) -> None:
        self.reg.register_endpoint("/old", "GET", None, deprecated=True)
        self.reg.register_endpoint("/new", "GET", None)
        result = self.reg.list_deprecated()
        assert len(result) == 1

    def test_get_tags(self) -> None:
        self.reg.register_endpoint("/a", "GET", None, tags=["alpha", "beta"])
        tags = self.reg.get_tags()
        assert "alpha" in tags
        assert "beta" in tags

    def test_get_statistics(self) -> None:
        self.reg.register_endpoint("/a", "GET", None, tags=["x"], version="v1")
        stats = self.reg.get_statistics()
        assert stats["total"] == 1
        assert stats["by_version"]["v1"] == 1


# ─── OpenAPI ───────────────────────────────────────────────────────────────
from app.api.openapi import DefaultOpenAPIProvider


class TestOpenAPI:
    def setup_method(self) -> None:
        self.reg = DefaultAPIRegistry()
        self.reg.register_endpoint("/users", "GET", None, tags=["users"], summary="List users")
        self.openapi = DefaultOpenAPIProvider(self.reg)

    def test_get_schema(self) -> None:
        schema = self.openapi.get_schema()
        assert schema["openapi"] == "3.0.3"
        assert "/users" in schema["paths"]

    def test_get_tags(self) -> None:
        tags = self.openapi.get_tags()
        assert any(t["name"] == "users" for t in tags)

    def test_get_security_schemes(self) -> None:
        schemes = self.openapi.get_security_schemes()
        assert "BearerAuth" in schemes

    def test_get_info(self) -> None:
        info = self.openapi.get_info()
        assert "NOVA CORE" in info["title"]

    def test_get_endpoint_count(self) -> None:
        assert self.openapi.get_endpoint_count() == 1


# ─── Docs ──────────────────────────────────────────────────────────────────
from app.api.docs import APIDocumentation


class TestDocs:
    def setup_method(self) -> None:
        self.doc = APIDocumentation()

    def test_get_router(self) -> None:
        r = self.doc.get_router()
        assert r is not None

    def test_documentation_routes_count(self) -> None:
        r = self.doc.get_router()
        assert len(r.routes) >= 3

    def test_documentation_has_catalog(self) -> None:
        r = self.doc.get_router()
        paths = [route.path for route in r.routes if hasattr(route, "path")]
        assert "/api/docs/catalog" in paths

    def test_documentation_has_spec(self) -> None:
        r = self.doc.get_router()
        paths = [route.path for route in r.routes if hasattr(route, "path")]
        assert "/api/docs/openapi-spec" in paths


# ─── Middleware ─────────────────────────────────────────────────────────────
from app.api.middleware import (
    APIMetricsMiddleware,
    ExceptionHandlingMiddleware,
    RequestIDMiddleware,
    TimingMiddleware,
)


class TestMiddleware:
    def test_request_id_middleware_exists(self) -> None:
        assert RequestIDMiddleware is not None

    def test_timing_middleware_exists(self) -> None:
        assert TimingMiddleware is not None

    def test_metrics_middleware_exists(self) -> None:
        assert APIMetricsMiddleware is not None

    def test_exception_middleware_exists(self) -> None:
        assert ExceptionHandlingMiddleware is not None


# ─── Dependencies ──────────────────────────────────────────────────────────
from app.api.dependencies import (
    DependencyContainer,
    get_container,
    get_correlation_id,
    get_request_id,
    get_response_time,
)


class TestDependencies:
    def test_container_register_singleton(self) -> None:
        c = DependencyContainer()
        c.register_singleton("val", 42)
        assert c.resolve("val") == 42

    def test_container_register_factory(self) -> None:
        c = DependencyContainer()
        c.register_factory("val", lambda: 99)
        assert c.resolve("val") == 99

    def test_container_resolve_missing(self) -> None:
        c = DependencyContainer()
        with pytest.raises(KeyError):
            c.resolve("missing")

    def test_container_has(self) -> None:
        c = DependencyContainer()
        c.register_singleton("a", 1)
        assert c.has("a") is True
        assert c.has("b") is False

    def test_container_list(self) -> None:
        c = DependencyContainer()
        c.register_singleton("a", 1)
        c.register_factory("b", lambda: 2)
        deps = c.list_dependencies()
        assert "a" in deps
        assert "b" in deps

    def test_get_container_singleton(self) -> None:
        c1 = get_container()
        c2 = get_container()
        assert c1 is c2

    def test_get_request_id(self) -> None:
        state = MagicMock()
        state.request_id = "req-1"
        req = MagicMock()
        req.state = state
        assert get_request_id(req) == "req-1"

    def test_get_correlation_id(self) -> None:
        state = MagicMock()
        state.correlation_id = "corr-1"
        req = MagicMock()
        req.state = state
        assert get_correlation_id(req) == "corr-1"

    def test_get_response_time(self) -> None:
        state = MagicMock()
        state.response_time_ms = 42.5
        req = MagicMock()
        req.state = state
        assert get_response_time(req) == 42.5


# ─── Lifecycle ─────────────────────────────────────────────────────────────
from app.api.lifecycle import APILifecycle


class TestLifecycle:
    def setup_method(self) -> None:
        self.lc = APILifecycle()

    def test_initial_state(self) -> None:
        assert self.lc.state == LifecycleState.REGISTERED

    def test_transition_to_initialized(self) -> None:
        assert self.lc.transition(LifecycleState.INITIALIZED) is True
        assert self.lc.state == LifecycleState.INITIALIZED

    def test_transition_to_ready(self) -> None:
        self.lc.transition(LifecycleState.INITIALIZED)
        self.lc.transition(LifecycleState.READY)
        assert self.lc.state == LifecycleState.READY

    def test_transition_to_running(self) -> None:
        self.lc.transition(LifecycleState.INITIALIZED)
        self.lc.transition(LifecycleState.READY)
        self.lc.transition(LifecycleState.RUNNING)
        assert self.lc.state == LifecycleState.RUNNING

    def test_invalid_transition(self) -> None:
        assert self.lc.transition(LifecycleState.RUNNING) is False

    def test_can_accept_requests(self) -> None:
        self.lc.transition(LifecycleState.INITIALIZED)
        self.lc.transition(LifecycleState.READY)
        assert self.lc.can_accept_requests() is True

    def test_get_history(self) -> None:
        self.lc.transition(LifecycleState.INITIALIZED)
        h = self.lc.get_history()
        assert len(h) == 1

    def test_get_status(self) -> None:
        s = self.lc.get_status()
        assert s["state"] == "registered"
        assert s["can_accept_requests"] is False

    def test_degraded_to_running(self) -> None:
        self.lc.transition(LifecycleState.INITIALIZED)
        self.lc.transition(LifecycleState.READY)
        self.lc.transition(LifecycleState.RUNNING)
        self.lc.transition(LifecycleState.DEGRADED)
        assert self.lc.transition(LifecycleState.RUNNING) is True

    def test_shutdown(self) -> None:
        self.lc.transition(LifecycleState.INITIALIZED)
        self.lc.transition(LifecycleState.READY)
        self.lc.transition(LifecycleState.RUNNING)
        self.lc.transition(LifecycleState.SHUTDOWN)
        assert self.lc.is_running() is False


# ─── Metrics ───────────────────────────────────────────────────────────────
from app.api.metrics import APIMetricsCollector


class TestMetrics:
    def setup_method(self) -> None:
        self.m = APIMetricsCollector()

    def test_record_request(self) -> None:
        self.m.record_request("/users", "GET")
        stats = self.m.get_statistics()
        assert stats["total_requests"] == 1

    def test_record_response(self) -> None:
        self.m.record_response("/users", 200)
        stats = self.m.get_statistics()
        assert stats["total_responses"] == 1

    def test_record_error(self) -> None:
        self.m.record_error("/users")
        stats = self.m.get_statistics()
        assert stats["total_errors"] == 1

    def test_error_rate(self) -> None:
        for _ in range(8):
            self.m.record_request("/a")
        for _ in range(2):
            self.m.record_error("/a")
        stats = self.m.get_statistics()
        assert stats["error_rate"] == 25.0

    def test_endpoint_usage(self) -> None:
        self.m.record_request("/a")
        self.m.record_request("/a")
        self.m.record_request("/b")
        usage = self.m.get_endpoint_usage()
        assert usage["GET /a"] == 2

    def test_reset(self) -> None:
        self.m.record_request("/x")
        self.m.reset()
        stats = self.m.get_statistics()
        assert stats["total_requests"] == 0

    def test_latency(self) -> None:
        self.m.record_latency(10.0)
        self.m.record_latency(20.0)
        stats = self.m.get_statistics()
        assert stats["average_latency_ms"] == 15.0


# ─── Tracing ───────────────────────────────────────────────────────────────
from app.api.tracing import APITracer


class TestTracing:
    def setup_method(self) -> None:
        self.tracer = APITracer()

    def test_start_trace(self) -> None:
        tid = self.tracer.start_trace(path="/users")
        assert tid != ""

    def test_add_span(self) -> None:
        tid = self.tracer.start_trace(path="/test")
        self.tracer.add_span(tid, "auth")
        trace = self.tracer.get_trace(tid)
        assert trace is not None
        assert len(trace["spans"]) == 1

    def test_end_span(self) -> None:
        tid = self.tracer.start_trace(path="/test")
        self.tracer.add_span(tid, "auth")
        self.tracer.end_span(tid, "auth")
        trace = self.tracer.get_trace(tid)
        assert trace is not None
        assert trace["spans"][0]["duration_ms"] >= 0

    def test_finish_trace(self) -> None:
        tid = self.tracer.start_trace(path="/test")
        self.tracer.finish_trace(tid, "ok")
        trace = self.tracer.get_trace(tid)
        assert trace is not None
        assert trace["status"] == "ok"
        assert trace["duration_ms"] >= 0

    def test_get_recent_traces(self) -> None:
        self.tracer.start_trace()
        self.tracer.start_trace()
        recent = self.tracer.get_recent_traces(10)
        assert len(recent) == 2

    def test_get_trace_not_found(self) -> None:
        assert self.tracer.get_trace("nonexistent") is None

    def test_statistics(self) -> None:
        self.tracer.start_trace(path="/a")
        self.tracer.start_trace(path="/b")
        stats = self.tracer.get_statistics()
        assert stats["total_traces"] == 2


# ─── Factory ───────────────────────────────────────────────────────────────
from app.api.factory import APIPlatformFactory


class TestFactory:
    def test_create_all(self) -> None:
        components = APIPlatformFactory.create_all()
        assert "registry" in components
        assert "version_provider" in components
        assert "response_formatter" in components
        assert "error_handler" in components
        assert "pagination_handler" in components
        assert "filtering_handler" in components
        assert "sorting_handler" in components
        assert "lifecycle" in components
        assert "metrics" in components
        assert "tracer" in components
        assert "openapi_provider" in components
        assert "documentation" in components

    def test_create_registry(self) -> None:
        r = APIPlatformFactory.create_registry()
        assert r.count() == 0

    def test_create_version_provider(self) -> None:
        vp = APIPlatformFactory.create_version_provider()
        assert "v1" in vp.get_supported_versions()

    def test_create_response_formatter(self) -> None:
        f = APIPlatformFactory.create_response_formatter()
        resp = f.success(data="ok")
        assert resp["success"] is True

    def test_create_error_handler(self) -> None:
        h = APIPlatformFactory.create_error_handler()
        resp = h.handle_not_found("X")
        assert resp["success"] is False

    def test_create_pagination(self) -> None:
        p = APIPlatformFactory.create_pagination_handler()
        result = p.paginate_page(list(range(5)), total=5, page=1, page_size=10)
        assert result["items"] == list(range(5))

    def test_create_filtering(self) -> None:
        f = APIPlatformFactory.create_filtering_handler()
        filters = f.parse_filters({"x": 1})
        assert len(filters) == 1

    def test_create_sorting(self) -> None:
        s = APIPlatformFactory.create_sorting_handler()
        params = s.parse_sort("name")
        assert params[0].field == "name"

    def test_create_lifecycle(self) -> None:
        lc = APIPlatformFactory.create_lifecycle()
        assert lc.state == LifecycleState.REGISTERED

    def test_create_metrics(self) -> None:
        m = APIPlatformFactory.create_metrics()
        m.record_request("/test")
        assert m.get_statistics()["total_requests"] == 1

    def test_create_tracer(self) -> None:
        t = APIPlatformFactory.create_tracer()
        tid = t.start_trace()
        assert tid != ""


# ─── Schemas ───────────────────────────────────────────────────────────────
from app.api.schemas import (
    APIErrorResponse,
    APIResponseSchema,
    APIStatisticsResponse,
    APIMetricsResponse,
    EndpointRegistration,
    FilterQuery,
    PaginationQuery,
    SortQuery,
    VersionInfo,
    VersionNegotiation,
)


class TestSchemas:
    def test_pagination_query_defaults(self) -> None:
        q = PaginationQuery()
        assert q.page == 1
        assert q.page_size == 20

    def test_pagination_query_validation(self) -> None:
        with pytest.raises(Exception):
            PaginationQuery(page=0)

    def test_endpoint_registration(self) -> None:
        e = EndpointRegistration(path="/test", method="GET")
        assert e.path == "/test"

    def test_api_response_schema(self) -> None:
        s = APIResponseSchema(success=True, data={"x": 1})
        assert s.success is True

    def test_api_error_response(self) -> None:
        e = APIErrorResponse(errors=[{"code": "err", "message": "bad"}])
        assert e.success is False

    def test_version_info(self) -> None:
        v = VersionInfo(version="v1")
        assert v.version == "v1"

    def test_version_negotiation(self) -> None:
        v = VersionNegotiation()
        assert v.accept == ""

    def test_filter_query(self) -> None:
        f = FilterQuery(filters={"name": "test"})
        assert f.filters["name"] == "test"

    def test_sort_query(self) -> None:
        s = SortQuery(sort="-name")
        assert s.sort == "-name"

    def test_api_statistics_response(self) -> None:
        s = APIStatisticsResponse(total_endpoints=10)
        assert s.total_endpoints == 10

    def test_api_metrics_response(self) -> None:
        m = APIMetricsResponse(total_requests=100)
        assert m.total_requests == 100


# ─── Platform ──────────────────────────────────────────────────────────────
from app.api.platform import APIPlatform


class TestPlatform:
    def setup_method(self) -> None:
        self.platform = APIPlatform()

    @pytest.mark.asyncio
    async def test_start_shutdown(self) -> None:
        await self.platform.start()
        assert self.platform.lifecycle.is_running()
        await self.platform.shutdown()

    def test_health(self) -> None:
        health = self.platform.health()
        assert "status" in health
        assert "endpoints" in health

    def test_format_success(self) -> None:
        resp = self.platform.format_success(data={"key": "val"})
        assert resp["success"] is True

    def test_format_error(self) -> None:
        from app.api.enums import ErrorCode
        resp = self.platform.format_error(ErrorCode.INTERNAL_ERROR, "oops")
        assert resp["success"] is False

    def test_format_paginated(self) -> None:
        resp = self.platform.format_paginated(data=[1, 2], total=10)
        assert resp["pagination"]["total_items"] == 10

    def test_filter_items(self) -> None:
        items = [{"name": "alice"}, {"name": "bob"}]
        result = self.platform.filter_items(items, {"name": "alice"})
        assert len(result) == 1

    def test_sort_items(self) -> None:
        items = [{"name": "b"}, {"name": "a"}]
        result = self.platform.sort_items(items, "-name")
        assert result[0]["name"] == "b"

    def test_pagination_page(self) -> None:
        result = self.platform.paginate_page(list(range(30)), total=30, page=2, page_size=10)
        assert result["items"] == list(range(10, 20))

    def test_pagination_offset(self) -> None:
        result = self.platform.paginate_offset(list(range(30)), total=30, offset=5, limit=5)
        assert result["items"] == list(range(5, 10))

    def test_pagination_cursor(self) -> None:
        result = self.platform.paginate_cursor(list(range(5)), limit=2)
        assert len(result["items"]) == 2

    def test_record_request_response(self) -> None:
        self.platform.record_request("/test")
        self.platform.record_response("/test", 200)
        stats = self.platform.metrics.get_statistics()
        assert stats["total_requests"] == 1

    def test_get_statistics(self) -> None:
        stats = self.platform.get_statistics()
        assert "endpoints" in stats
        assert "metrics" in stats

    def test_registry_count(self) -> None:
        self.platform.registry.register_endpoint("/a", "GET", None)
        assert self.platform.registry.count() == 1


# ─── Backward Compatibility ───────────────────────────────────────────────
class TestBackwardCompatibility:
    def test_v1_still_supported(self) -> None:
        vp = DefaultAPIVersionProvider()
        assert "v1" in vp.get_supported_versions()

    def test_v1_not_deprecated(self) -> None:
        vp = DefaultAPIVersionProvider()
        assert vp.is_deprecated("v1") is False

    def test_existing_v1_routes_not_broken(self) -> None:
        from app.api.v1.router import router
        assert len(router.routes) >= 15


# ─── Concurrency ───────────────────────────────────────────────────────────
class TestConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_metrics(self) -> None:
        m = APIMetricsCollector()

        async def _record() -> None:
            for _ in range(100):
                m.record_request("/test")
                m.record_response("/test", 200)

        await asyncio.gather(*[_record() for _ in range(10)])
        stats = m.get_statistics()
        assert stats["total_requests"] == 1000

    @pytest.mark.asyncio
    async def test_concurrent_tracing(self) -> None:
        t = APITracer()

        async def _trace() -> None:
            for _ in range(50):
                tid = t.start_trace(path="/concurrent")
                t.finish_trace(tid)

        await asyncio.gather(*[_trace() for _ in range(10)])
        stats = t.get_statistics()
        assert stats["total_traces"] == 500

    @pytest.mark.asyncio
    async def test_concurrent_registry(self) -> None:
        reg = DefaultAPIRegistry()

        async def _register() -> None:
            for i in range(20):
                reg.register_endpoint(f"/ep-{uuid.uuid4()}", "GET", None)

        await asyncio.gather(*[_register() for _ in range(10)])
        assert reg.count() == 200


# ─── Edge Cases ────────────────────────────────────────────────────────────
class TestEdgeCases:
    def test_filter_nonexistent_field(self) -> None:
        fh = FilteringHandler()
        items = [{"name": "a"}]
        filters = fh.parse_filters({"nonexistent": "x"})
        result = fh.apply(items, filters)
        assert len(result) == 0

    def test_sort_empty_list(self) -> None:
        sh = SortingHandler()
        result = sh.sort([], [SortParams(field="name")])
        assert result == []

    def test_pagination_zero_items(self) -> None:
        ph = PaginationHandler()
        result = ph.paginate_page([], total=0)
        assert result["items"] == []
        assert result["pagination"]["total_pages"] == 1

    def test_version_negotiate_unknown(self) -> None:
        vp = DefaultAPIVersionProvider()
        assert vp.negotiate("application/vnd.unknown+json") == "v1"

    def test_error_handler_all_return_success_false(self) -> None:
        h = StandardErrorHandler()
        assert h.handle_validation([])["success"] is False
        assert h.handle_not_found("X")["success"] is False
        assert h.handle_unauthorized()["success"] is False
        assert h.handle_forbidden()["success"] is False
        assert h.handle_conflict("X")["success"] is False
        assert h.handle_rate_limit()["success"] is False
        assert h.handle_internal()["success"] is False
        assert h.handle_timeout()["success"] is False
        assert h.handle_deprecated()["success"] is False
        assert h.handle_dependency_failure("X")["success"] is False
