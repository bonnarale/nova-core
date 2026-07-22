"""Tests for Chapter 15 — Tool System."""

from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tools.base import Tool, ToolParam, ToolSpec
from app.tools.context import ToolContext
from app.tools.exceptions import (
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolPermissionError,
    ToolTimeoutError,
    ToolValidationError,
)
from app.tools.executor import ToolExecutor
from app.tools.factory import ToolFactory
from app.tools.lifecycle import ToolLifecycle, ToolState
from app.tools.manager import ToolManager
from app.tools.metrics import ToolMetrics
from app.tools.permissions import PermissionChecker, PermissionLevel, ToolPermission
from app.tools.policies import (
    BackgroundPolicy,
    ExclusivePolicy,
    IdempotentPolicy,
    ImmediatePolicy,
    ParallelPolicy,
    RetryablePolicy,
    ToolPolicyType,
    get_tool_policy,
    list_tool_policies,
)
from app.tools.registry import ToolRegistry
from app.tools.result import ToolResult
from app.tools.runtime import ToolRuntime
from app.tools.schema import build_input_schema, validate_schema
from app.tools.tracing import ToolTracer, ToolTrace


# ======================================================================
# Helpers
# ======================================================================

class _EchoTool(Tool):
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="echo",
            description="Echo tool for testing",
            category="test",
            tool_id="echo",
            version="1.0.0",
            capabilities=["echo", "test"],
            tags=["test"],
            policy="immediate",
            parameters=[
                ToolParam(name="message", type="string", required=True, description="Message to echo"),
                ToolParam(name="count", type="integer", required=False, default=1, description="Repeat count"),
            ],
        )

    async def run(self, params: dict[str, Any]) -> ToolResult:
        msg = params.get("message", "")
        count = params.get("count", 1)
        return ToolResult(success=True, data={"echo": msg * count})


class _FailTool(Tool):
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(name="fail_tool", description="Always fails", parameters=[])

    async def run(self, params: dict[str, Any]) -> ToolResult:
        raise RuntimeError("intentional failure")


class _SlowTool(Tool):
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(name="slow_tool", description="Slow tool", parameters=[], timeout_default=0.1)

    async def run(self, params: dict[str, Any]) -> ToolResult:
        await asyncio.sleep(10)
        return ToolResult(success=True)


class _LifecycleTool(Tool):
    def __init__(self) -> None:
        self._initialized = False
        self._shutdown_called = False

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(name="lifecycle_tool", description="Lifecycle test", parameters=[])

    async def initialize(self) -> None:
        self._initialized = True

    async def shutdown(self) -> None:
        self._shutdown_called = True

    async def health(self) -> dict[str, Any]:
        return {"tool_id": "lifecycle_tool", "status": "healthy", "initialized": self._initialized}

    async def run(self, params: dict[str, Any]) -> ToolResult:
        return ToolResult(success=True, data={"initialized": self._initialized})


class _CancelTool(Tool):
    def __init__(self) -> None:
        self._cancelled = False

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(name="cancel_tool", description="Cancellable", parameters=[])

    async def cancel(self) -> bool:
        self._cancelled = True
        return True

    async def run(self, params: dict[str, Any]) -> ToolResult:
        await asyncio.sleep(10)
        return ToolResult(success=True)


# ======================================================================
# ToolContext
# ======================================================================

class TestToolContext:
    def test_defaults(self):
        ctx = ToolContext()
        assert ctx.execution_id
        assert ctx.tool_id == ""
        assert ctx.agent_id == ""
        assert ctx.start_time > 0

    def test_has_permission_wildcard(self):
        ctx = ToolContext(permissions=["*"])
        assert ctx.has_permission("anything") is True

    def test_has_permission_specific(self):
        ctx = ToolContext(permissions=["read", "write"])
        assert ctx.has_permission("read") is True
        assert ctx.has_permission("admin") is False

    def test_elapsed(self):
        ctx = ToolContext()
        time.sleep(0.01)
        assert ctx.elapsed() > 0

    def test_to_dict(self):
        ctx = ToolContext(tool_id="test", agent_id="a1", user_id="u1")
        d = ctx.to_dict()
        assert d["tool_id"] == "test"
        assert d["agent_id"] == "a1"
        assert d["user_id"] == "u1"

    def test_with_tool(self):
        ctx = ToolContext(agent_id="a1", user_id="u1")
        ctx2 = ctx.with_tool("my_tool")
        assert ctx2.tool_id == "my_tool"
        assert ctx2.agent_id == "a1"
        assert ctx.execution_id == ctx2.execution_id


# ======================================================================
# Schema Validation
# ======================================================================

class TestSchema:
    def test_validate_type_string(self):
        validate_schema("hello", {"type": "string"})

    def test_validate_type_integer(self):
        validate_schema(42, {"type": "integer"})

    def test_validate_type_fails(self):
        with pytest.raises(ToolValidationError):
            validate_schema(42, {"type": "string"})

    def test_validate_required_fields(self):
        schema = {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}
        with pytest.raises(ToolValidationError, match="Missing required"):
            validate_schema({}, schema)

    def test_validate_enum(self):
        with pytest.raises(ToolValidationError):
            validate_schema("c", {"enum": ["a", "b"]})

    def test_validate_min_max(self):
        validate_schema(5, {"minimum": 0, "maximum": 10})
        with pytest.raises(ToolValidationError):
            validate_schema(15, {"maximum": 10})

    def test_validate_string_length(self):
        validate_schema("hi", {"minLength": 1, "maxLength": 10})
        with pytest.raises(ToolValidationError):
            validate_schema("", {"minLength": 1})

    def test_validate_nested_properties(self):
        schema = {
            "type": "object",
            "properties": {"nested": {"type": "object", "properties": {"val": {"type": "string"}}, "required": ["val"]}},
            "required": ["nested"],
        }
        validate_schema({"nested": {"val": "ok"}}, schema)
        with pytest.raises(ToolValidationError):
            validate_schema({"nested": {}}, schema)

    def test_validate_items(self):
        schema = {"type": "array", "items": {"type": "string"}}
        validate_schema(["a", "b"], schema)
        with pytest.raises(ToolValidationError):
            validate_schema([1], schema)

    def test_validate_empty_schema(self):
        validate_schema({"any": "data"}, {})

    def test_build_input_schema(self):
        params = [
            {"name": "query", "type": "string", "required": True, "description": "Search"},
            {"name": "limit", "type": "integer", "required": False, "default": 10},
        ]
        schema = build_input_schema(params)
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "limit" in schema["properties"]
        assert "query" in schema["required"]


# ======================================================================
# ToolLifecycle
# ======================================================================

class TestToolLifecycle:
    def test_initial_state(self):
        lc = ToolLifecycle("test_tool")
        assert lc.state == ToolState.REGISTERED

    def test_initialize(self):
        lc = ToolLifecycle("t")
        assert lc.initialize() is True
        assert lc.state == ToolState.INITIALIZING

    def test_ready(self):
        lc = ToolLifecycle("t")
        lc.initialize()
        assert lc.ready() is True
        assert lc.state == ToolState.READY

    def test_running(self):
        lc = ToolLifecycle("t")
        lc.initialize()
        lc.ready()
        assert lc.start() is True
        assert lc.state == ToolState.RUNNING

    def test_complete(self):
        lc = ToolLifecycle("t")
        lc.initialize()
        lc.ready()
        lc.start()
        assert lc.complete() is True
        assert lc.state == ToolState.READY

    def test_suspend_resume(self):
        lc = ToolLifecycle("t")
        lc.initialize()
        lc.ready()
        assert lc.suspend() is True
        assert lc.state == ToolState.SUSPENDED
        assert lc.resume() is True
        assert lc.state == ToolState.READY

    def test_error_and_recover(self):
        lc = ToolLifecycle("t")
        lc.initialize()
        lc.ready()
        assert lc.fail() is True
        assert lc.state == ToolState.ERROR
        assert lc.recover() is True
        assert lc.state == ToolState.READY

    def test_shutdown(self):
        lc = ToolLifecycle("t")
        assert lc.shutdown() is True
        assert lc.state == ToolState.SHUTDOWN

    def test_shutdown_from_registered(self):
        lc = ToolLifecycle("t")
        assert lc.shutdown() is True
        assert lc.is_terminal

    def test_invalid_transition(self):
        lc = ToolLifecycle("t")
        assert lc.start() is False  # can't go from REGISTERED -> RUNNING

    def test_history(self):
        lc = ToolLifecycle("t")
        lc.initialize()
        lc.ready()
        assert len(lc.history) == 3

    def test_is_ready(self):
        lc = ToolLifecycle("t")
        assert lc.is_ready is False
        lc.initialize()
        lc.ready()
        assert lc.is_ready is True

    def test_to_dict(self):
        lc = ToolLifecycle("t")
        d = lc.to_dict()
        assert d["tool_id"] == "t"
        assert d["state"] == "registered"


# ======================================================================
# Tool Policies
# ======================================================================

class TestToolPolicies:
    def test_immediate(self):
        p = ImmediatePolicy()
        assert p.name == "immediate"
        assert p.can_run_concurrently() is True
        assert p.should_retry_on_failure() is False
        assert p.is_idempotent() is False
        assert p.should_run_in_background() is False

    def test_background(self):
        p = BackgroundPolicy()
        assert p.name == "background"
        assert p.should_run_in_background() is True
        assert p.should_retry_on_failure() is True

    def test_retryable(self):
        p = RetryablePolicy(max_retries=5)
        assert p.name == "retryable"
        assert p.should_retry_on_failure() is True
        assert p.is_idempotent() is True
        assert p.max_retries == 5

    def test_exclusive(self):
        p = ExclusivePolicy()
        assert p.name == "exclusive"
        assert p.can_run_concurrently() is False

    def test_parallel(self):
        p = ParallelPolicy()
        assert p.name == "parallel"
        assert p.can_run_concurrently() is True

    def test_idempotent(self):
        p = IdempotentPolicy()
        assert p.name == "idempotent"
        assert p.is_idempotent() is True

    def test_get_tool_policy(self):
        p = get_tool_policy("immediate")
        assert isinstance(p, ImmediatePolicy)

    def test_get_tool_policy_unknown(self):
        with pytest.raises(ValueError):
            get_tool_policy("nonexistent")

    def test_list_tool_policies(self):
        policies = list_tool_policies()
        assert "immediate" in policies
        assert "background" in policies
        assert len(policies) == 6

    def test_policy_to_dict(self):
        p = ImmediatePolicy()
        d = p.to_dict()
        assert d["name"] == "immediate"


# ======================================================================
# Tool Metrics
# ======================================================================

class TestToolMetrics:
    def test_record_execution(self):
        m = ToolMetrics()
        m.record_execution("t1", 10.0, True)
        assert m.get_executions("t1") == 1
        assert m.get_failures("t1") == 0

    def test_record_failure(self):
        m = ToolMetrics()
        m.record_execution("t1", 10.0, False)
        assert m.get_failures("t1") == 1

    def test_record_timeout(self):
        m = ToolMetrics()
        m.record_execution("t1", 10.0, False, timed_out=True)
        assert m.get_timeouts("t1") == 1

    def test_success_rate(self):
        m = ToolMetrics()
        m.record_execution("t1", 10.0, True)
        m.record_execution("t1", 10.0, True)
        m.record_execution("t1", 10.0, False)
        assert m.get_success_rate("t1") == pytest.approx(2 / 3, abs=0.01)

    def test_success_rate_empty(self):
        m = ToolMetrics()
        assert m.get_success_rate("nonexistent") == 1.0

    def test_latency(self):
        m = ToolMetrics()
        m.record_execution("t1", 10.0, True)
        m.record_execution("t1", 20.0, True)
        lat = m.get_latency("t1")
        assert lat["avg_ms"] == 15.0
        assert lat["count"] == 2

    def test_usage_frequency(self):
        m = ToolMetrics()
        m.record_execution("t1", 1.0, True)
        m.record_execution("t1", 1.0, True)
        assert m.get_usage_frequency("t1") == 2

    def test_snapshot(self):
        m = ToolMetrics()
        m.record_execution("t1", 10.0, True)
        s = m.snapshot()
        assert "global" in s
        assert "tools" in s
        assert s["global"]["executions"] == 1

    def test_clear(self):
        m = ToolMetrics()
        m.record_execution("t1", 10.0, True)
        m.clear()
        assert m.get_executions("t1") == 0

    def test_global_counts(self):
        m = ToolMetrics()
        m.record_execution("t1", 10.0, True)
        m.record_execution("t2", 10.0, False)
        assert m.get_executions() == 2
        assert m.get_failures() == 1


# ======================================================================
# Tool Tracing
# ======================================================================

class TestToolTracing:
    def test_start_trace(self):
        tracer = ToolTracer()
        trace = tracer.start_trace(tool_id="t1", agent_id="a1")
        assert trace.tool_id == "t1"
        assert trace.agent_id == "a1"
        assert trace.status == "pending"

    def test_close_trace(self):
        tracer = ToolTracer()
        trace = tracer.start_trace(tool_id="t1")
        trace.close(status="success")
        assert trace.status == "success"
        assert trace.duration_ms >= 0

    def test_get_trace(self):
        tracer = ToolTracer()
        trace = tracer.start_trace(tool_id="t1")
        found = tracer.get_trace(trace.execution_id)
        assert found is trace

    def test_get_traces_for_tool(self):
        tracer = ToolTracer()
        tracer.start_trace(tool_id="t1")
        tracer.start_trace(tool_id="t1")
        tracer.start_trace(tool_id="t2")
        traces = tracer.get_traces_for_tool("t1")
        assert len(traces) == 2

    def test_to_dict(self):
        tracer = ToolTracer()
        tracer.start_trace(tool_id="t1")
        d = tracer.to_dict()
        assert len(d) == 1
        assert d[0]["tool_id"] == "t1"

    def test_max_traces(self):
        tracer = ToolTracer(max_traces=3)
        for i in range(5):
            tracer.start_trace(tool_id=f"t{i}")
        assert len(tracer.get_all_traces()) == 3

    def test_clear(self):
        tracer = ToolTracer()
        tracer.start_trace(tool_id="t1")
        tracer.clear()
        assert len(tracer.get_all_traces()) == 0


# ======================================================================
# Permissions (enhanced)
# ======================================================================

class TestEnhancedPermissions:
    def test_role_based_allow(self):
        p = ToolPermission(tool_name="t", allowed_roles=["admin"])
        assert p.allows(agent_id="a1", roles=["admin"]) is True
        assert p.allows(agent_id="a1", roles=["user"]) is False

    def test_denied_agent(self):
        p = ToolPermission(tool_name="t", denied_agents=["bad_agent"])
        assert p.allows(agent_id="bad_agent") is False
        assert p.allows(agent_id="good_agent") is True

    def test_denied_user(self):
        p = ToolPermission(tool_name="t", denied_users=["bad_user"])
        assert p.allows(user_id="bad_user") is False
        assert p.allows(user_id="good_user") is True

    def test_user_based_allow(self):
        p = ToolPermission(tool_name="t", allowed_users=["user1"])
        assert p.allows(user_id="user1") is True
        assert p.allows(user_id="user2") is False

    def test_checker_with_user(self):
        checker = PermissionChecker()
        checker.register(ToolPermission(tool_name="t", allowed_users=["u1"]))
        assert checker.check("t", user_id="u1") is True
        assert checker.check("t", user_id="u2") is False

    def test_checker_with_roles(self):
        checker = PermissionChecker()
        checker.register(ToolPermission(tool_name="t", allowed_roles=["admin"]))
        assert checker.check("t", agent_id="a", roles=["admin"]) is True
        assert checker.check("t", agent_id="a", roles=["user"]) is False

    def test_to_dict_enhanced(self):
        checker = PermissionChecker()
        checker.register(ToolPermission(tool_name="t", allowed_roles=["admin"], denied_agents=["bad"]))
        d = checker.to_dict()
        assert d["t"]["allowed_roles"] == ["admin"]
        assert d["t"]["denied_agents"] == ["bad"]


# ======================================================================
# ToolRegistry (enhanced)
# ======================================================================

class TestEnhancedToolRegistry:
    def test_discover_by_category(self):
        r = ToolRegistry()
        t1 = _EchoTool()
        r.register(t1)
        found = r.discover(category="test")
        assert len(found) == 1
        assert r.discover(category="nonexistent") == []

    def test_discover_by_capability(self):
        r = ToolRegistry()
        r.register(_EchoTool())
        found = r.discover(capability="echo")
        assert len(found) == 1

    def test_discover_by_tag(self):
        r = ToolRegistry()
        r.register(_EchoTool())
        found = r.discover(tag="test")
        assert len(found) == 1

    def test_health_check(self):
        r = ToolRegistry()
        r.register(_EchoTool())
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(r.health_check())
        assert "echo" in result
        assert result["echo"]["status"] == "healthy"
        loop.close()

    def test_get_lifecycle(self):
        r = ToolRegistry()
        r.register(_EchoTool())
        lc = r.get_lifecycle("echo")
        assert lc is not None
        assert lc.state == ToolState.REGISTERED

    def test_lifecycle_initialized(self):
        r = ToolRegistry()
        r.register(_EchoTool())
        lc = r.get_lifecycle("echo")
        assert lc is not None
        lc.initialize()
        lc.ready()
        assert lc.state == ToolState.READY


# ======================================================================
# ToolManager
# ======================================================================

class TestToolManager:
    def test_register_and_get(self):
        mgr = ToolManager()
        tool = _EchoTool()
        mgr.register(tool)
        assert mgr.get_tool("echo") is tool

    def test_unregister(self):
        mgr = ToolManager()
        mgr.register(_EchoTool())
        mgr.unregister("echo")
        assert mgr.get_tool("echo") is None

    def test_list_tools(self):
        mgr = ToolManager()
        mgr.register(_EchoTool())
        specs = mgr.list_tools()
        assert len(specs) == 1
        assert specs[0].name == "echo"

    def test_lifecycle_integration(self):
        mgr = ToolManager()
        mgr.register(_EchoTool())
        lc = mgr.get_lifecycle("echo")
        assert lc is not None
        assert lc.state == ToolState.READY

    def test_policy_integration(self):
        mgr = ToolManager()
        mgr.register(_EchoTool(), policy="background")
        p = mgr.get_policy("echo")
        assert p is not None
        assert p.name == "background"

    def test_permissions_integration(self):
        mgr = ToolManager()
        perm = ToolPermission(tool_name="echo", allowed_agents=["admin"])
        mgr.register(_EchoTool(), permissions=perm)
        assert mgr.check_permission("echo", agent_id="admin") is True
        assert mgr.check_permission("echo", agent_id="user") is False

    def test_dependencies(self):
        mgr = ToolManager()
        mgr.register(_EchoTool(), dependencies=["dep1"])
        assert mgr.get_dependencies("echo") == ["dep1"]
        assert mgr.check_dependencies("echo") is False  # dep1 not registered
        mgr.register(_FailTool())
        mgr._dependencies["echo"] = ["fail_tool"]
        assert mgr.check_dependencies("echo") is True

    def test_discover(self):
        mgr = ToolManager()
        mgr.register(_EchoTool())
        found = mgr.discover(category="test")
        assert len(found) == 1

    def test_initialize_all(self):
        tool = _LifecycleTool()
        mgr = ToolManager()
        mgr.register(tool)
        loop = asyncio.new_event_loop()
        loop.run_until_complete(mgr.initialize_all())
        assert tool._initialized is True
        loop.close()

    def test_shutdown_all(self):
        tool = _LifecycleTool()
        mgr = ToolManager()
        mgr.register(tool)
        loop = asyncio.new_event_loop()
        loop.run_until_complete(mgr.shutdown_all())
        assert tool._shutdown_called is True
        loop.close()

    def test_health_check(self):
        mgr = ToolManager()
        mgr.register(_EchoTool())
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(mgr.health_check())
        assert "echo" in result
        loop.close()

    def test_to_dict(self):
        mgr = ToolManager()
        mgr.register(_EchoTool())
        d = mgr.to_dict()
        assert "echo" in d["tools"]
        assert "metrics" in d


# ======================================================================
# ToolRuntime
# ======================================================================

class TestToolRuntime:
    def _make_runtime(self) -> ToolRuntime:
        mgr = ToolManager()
        mgr.register(_EchoTool())
        mgr.register(_FailTool())
        mgr.register(_SlowTool())
        return ToolRuntime(manager=mgr, default_timeout=1.0)

    @pytest.mark.asyncio
    async def test_execute_tool_success(self):
        rt = self._make_runtime()
        result = await rt.execute_tool("echo", {"message": "hello"})
        assert result.success is True
        assert result.data["echo"] == "hello"
        assert result.tool_name == "echo"

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self):
        rt = self._make_runtime()
        result = await rt.execute_tool("nonexistent")
        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_execute_tool_with_context(self):
        rt = self._make_runtime()
        ctx = ToolContext(agent_id="a1", user_id="u1")
        result = await rt.execute_tool("echo", {"message": "hi"}, context=ctx)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_tool_timeout(self):
        rt = self._make_runtime()
        result = await rt.execute_tool("slow_tool", timeout=0.1)
        assert result.success is False
        assert "Timed out" in result.error

    @pytest.mark.asyncio
    async def test_execute_tool_retry(self):
        mgr = ToolManager()
        mgr.register(_FailTool())
        rt = ToolRuntime(manager=mgr, default_timeout=1.0, default_retries=2)
        result = await rt.execute_tool("fail_tool")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_validate_request(self):
        rt = self._make_runtime()
        ctx = ToolContext()
        assert rt.validate_request("echo", ctx) is True
        assert rt.validate_request("nonexistent", ctx) is False

    @pytest.mark.asyncio
    async def test_prepare_context(self):
        rt = self._make_runtime()
        ctx = ToolContext()
        ctx2 = rt.prepare_context("echo", ctx)
        assert ctx2.tool_id == "echo"

    @pytest.mark.asyncio
    async def test_collect_result(self):
        rt = self._make_runtime()
        trace = rt.tracer.start_trace(tool_id="echo")
        result = ToolResult(success=True, data={"ok": True}, tool_name="echo", duration_ms=10.0)
        rt.collect_result(trace, result)
        assert trace.status == "success"

    @pytest.mark.asyncio
    async def test_metrics_after_execution(self):
        rt = self._make_runtime()
        await rt.execute_tool("echo", {"message": "test"})
        assert rt.metrics.get_executions("echo") >= 1

    @pytest.mark.asyncio
    async def test_tracing_after_execution(self):
        rt = self._make_runtime()
        await rt.execute_tool("echo", {"message": "trace"})
        traces = rt.tracer.get_traces_for_tool("echo")
        assert len(traces) >= 1

    @pytest.mark.asyncio
    async def test_health(self):
        rt = self._make_runtime()
        result = await rt.health()
        assert "echo" in result

    @pytest.mark.asyncio
    async def test_shutdown(self):
        rt = self._make_runtime()
        await rt.shutdown()

    def test_to_dict(self):
        rt = self._make_runtime()
        d = rt.to_dict()
        assert "manager" in d


# ======================================================================
# ToolFactory
# ======================================================================

class TestToolFactory:
    def test_create_and_register(self):
        mgr = ToolManager()
        factory = ToolFactory(manager=mgr)
        tool = factory.create_and_register(_EchoTool)
        assert isinstance(tool, _EchoTool)
        assert mgr.get_tool("echo") is tool

    def test_register_all_builtins(self):
        mgr = ToolManager()
        factory = ToolFactory(manager=mgr)
        factory.register_all_builtins()
        tools = mgr.list_tools()
        names = {s.name for s in tools}
        assert "filesystem" in names
        assert "git" in names
        assert "python" in names
        assert "http" in names
        assert "web_search" in names

    def test_register_template(self):
        factory = ToolFactory()
        factory.register_template("echo", _EchoTool)
        assert "echo" in factory._templates

    def test_to_dict(self):
        factory = ToolFactory()
        d = factory.to_dict()
        assert "templates" in d
        assert "manager" in d


# ======================================================================
# Built-in Tools
# ======================================================================

class TestMemorySearchTool:
    @pytest.mark.asyncio
    async def test_no_backend(self):
        from app.tools.builtin.memory_search import MemorySearchTool
        tool = MemorySearchTool()
        result = await tool.run({"query": "test"})
        assert result.success is True
        assert result.metadata.get("stub") is True

    @pytest.mark.asyncio
    async def test_missing_query(self):
        from app.tools.builtin.memory_search import MemorySearchTool
        tool = MemorySearchTool()
        result = await tool.run({})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_with_mock_memory(self):
        from app.tools.builtin.memory_search import MemorySearchTool
        mock_mem = AsyncMock()
        mock_mem.search = AsyncMock(return_value=[{"text": "found"}])
        tool = MemorySearchTool(memory=mock_mem)
        result = await tool.run({"query": "test"})
        assert result.success is True
        assert len(result.data["results"]) == 1


class TestKnowledgeSearchTool:
    @pytest.mark.asyncio
    async def test_no_engine(self):
        from app.tools.builtin.knowledge_search import KnowledgeSearchTool
        tool = KnowledgeSearchTool()
        result = await tool.run({"query": "test"})
        assert result.success is True
        assert result.metadata.get("stub") is True

    @pytest.mark.asyncio
    async def test_missing_query(self):
        from app.tools.builtin.knowledge_search import KnowledgeSearchTool
        tool = KnowledgeSearchTool()
        result = await tool.run({})
        assert result.success is False


class TestGoalQueryTool:
    @pytest.mark.asyncio
    async def test_no_manager(self):
        from app.tools.builtin.goal_query import GoalQueryTool
        tool = GoalQueryTool()
        result = await tool.run({"operation": "list"})
        assert result.success is True
        assert result.metadata.get("stub") is True

    @pytest.mark.asyncio
    async def test_unknown_operation(self):
        from app.tools.builtin.goal_query import GoalQueryTool
        mock_manager = AsyncMock()
        tool = GoalQueryTool(goal_manager=mock_manager)
        result = await tool.run({"operation": "delete"})
        assert result.success is False


class TestTaskQueryTool:
    @pytest.mark.asyncio
    async def test_no_manager(self):
        from app.tools.builtin.task_query import TaskQueryTool
        tool = TaskQueryTool()
        result = await tool.run({"operation": "list"})
        assert result.success is True
        assert result.metadata.get("stub") is True

    @pytest.mark.asyncio
    async def test_unknown_operation(self):
        from app.tools.builtin.task_query import TaskQueryTool
        mock_manager = AsyncMock()
        tool = TaskQueryTool(task_manager=mock_manager)
        result = await tool.run({"operation": "delete"})
        assert result.success is False


class TestAgentDiscoveryTool:
    @pytest.mark.asyncio
    async def test_no_runtime(self):
        from app.tools.builtin.agent_discovery import AgentDiscoveryTool
        tool = AgentDiscoveryTool()
        result = await tool.run({"operation": "list"})
        assert result.success is True
        assert result.metadata.get("stub") is True

    @pytest.mark.asyncio
    async def test_list_agents(self):
        from app.tools.builtin.agent_discovery import AgentDiscoveryTool
        mock_runtime = MagicMock()
        mock_agent = MagicMock()
        mock_agent.agent_id = "a1"
        mock_agent.__class__.__name__ = "MockAgent"
        mock_agent.definition.to_dict.return_value = {"id": "a1"}
        mock_runtime.list_agents.return_value = [mock_agent]
        tool = AgentDiscoveryTool(agent_runtime=mock_runtime)
        result = await tool.run({"operation": "list"})
        assert result.success is True
        assert result.data["total"] == 1


# ======================================================================
# Tool Base (enhanced)
# ======================================================================

class TestEnhancedToolBase:
    @pytest.mark.asyncio
    async def test_initialize_and_shutdown(self):
        tool = _LifecycleTool()
        await tool.initialize()
        assert tool._initialized is True
        await tool.shutdown()
        assert tool._shutdown_called is True

    @pytest.mark.asyncio
    async def test_health(self):
        tool = _LifecycleTool()
        h = await tool.health()
        assert h["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_cancel(self):
        tool = _CancelTool()
        result = await tool.cancel()
        assert result is True
        assert tool._cancelled is True

    def test_spec_has_new_fields(self):
        tool = _EchoTool()
        spec = tool.spec
        assert spec.tool_id == "echo"
        assert spec.version == "1.0.0"
        assert spec.capabilities == ["echo", "test"]
        assert spec.tags == ["test"]
        assert spec.policy == "immediate"

    def test_spec_to_dict_has_new_fields(self):
        tool = _EchoTool()
        d = tool.spec.to_dict()
        assert "tool_id" in d
        assert "version" in d
        assert "capabilities" in d
        assert "tags" in d
        assert "policy" in d
        assert "input_schema" in d
        assert "output_schema" in d


# ======================================================================
# ToolSpec ToolParam
# ======================================================================

class TestToolSpec:
    def test_tool_id_auto_set(self):
        spec = ToolSpec(name="my_tool")
        assert spec.tool_id == "my_tool"

    def test_tool_id_explicit(self):
        spec = ToolSpec(name="my_tool", tool_id="custom_id")
        assert spec.tool_id == "custom_id"

    def test_defaults(self):
        spec = ToolSpec(name="t")
        assert spec.version == "1.0.0"
        assert spec.capabilities == []
        assert spec.tags == []
        assert spec.policy == "immediate"
        assert spec.input_schema == {}
        assert spec.output_schema == {}


# ======================================================================
# ToolExecutor (cancellation)
# ======================================================================

class TestToolExecutorCancellation:
    @pytest.mark.asyncio
    async def test_cancel_nonexistent(self):
        registry = ToolRegistry()
        registry.register(_EchoTool())
        executor = ToolExecutor(registry=registry)
        result = await executor.cancel("echo")
        assert result is False


# ======================================================================
# Integration: Runtime with Policies
# ======================================================================

class TestRuntimePolicyIntegration:
    @pytest.mark.asyncio
    async def test_retryable_policy_in_runtime(self):
        mgr = ToolManager()
        mgr.register(_FailTool(), policy="retryable")
        rt = ToolRuntime(manager=mgr, default_timeout=1.0)
        result = await rt.execute_tool("fail_tool")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_exclusive_policy_in_runtime(self):
        mgr = ToolManager()
        mgr.register(_EchoTool(), policy="exclusive")
        rt = ToolRuntime(manager=mgr, default_timeout=1.0)
        result = await rt.execute_tool("echo", {"message": "hi"})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_parallel_policy_in_runtime(self):
        mgr = ToolManager()
        mgr.register(_EchoTool(), policy="parallel")
        rt = ToolRuntime(manager=mgr, default_timeout=1.0)
        tasks = [rt.execute_tool("echo", {"message": f"msg{i}"}) for i in range(5)]
        results = await asyncio.gather(*tasks)
        assert all(r.success for r in results)


# ======================================================================
# Integration: Runtime + Tracer + Metrics
# ======================================================================

class TestRuntimeObservability:
    @pytest.mark.asyncio
    async def test_full_observability(self):
        mgr = ToolManager()
        mgr.register(_EchoTool())
        rt = ToolRuntime(manager=mgr)
        await rt.execute_tool("echo", {"message": "observed"})

        assert rt.metrics.get_executions("echo") >= 1
        traces = rt.tracer.get_traces_for_tool("echo")
        assert len(traces) >= 1
        assert traces[0].status == "success"

    @pytest.mark.asyncio
    async def test_error_observability(self):
        mgr = ToolManager()
        mgr.register(_FailTool())
        rt = ToolRuntime(manager=mgr)
        result = await rt.execute_tool("fail_tool")
        assert result.success is False
        assert rt.metrics.get_failures("fail_tool") >= 1

    @pytest.mark.asyncio
    async def test_timeout_observability(self):
        mgr = ToolManager()
        mgr.register(_SlowTool())
        rt = ToolRuntime(manager=mgr, default_timeout=0.1)
        result = await rt.execute_tool("slow_tool")
        assert result.success is False
        assert rt.metrics.get_timeouts("slow_tool") >= 1


# ======================================================================
# API endpoint tests (lightweight, no full FastAPI test client needed)
# ======================================================================

class TestToolAPIModels:
    def test_register_tool_request(self):
        from app.api.v1.routes.tools import RegisterToolRequest
        req = RegisterToolRequest(name="test_tool")
        assert req.name == "test_tool"
        assert req.policy == "immediate"

    def test_execute_tool_request(self):
        from app.api.v1.routes.tools import ExecuteToolRequest
        req = ExecuteToolRequest(params={"key": "val"}, agent_id="a1")
        assert req.params == {"key": "val"}
        assert req.agent_id == "a1"


# ======================================================================
# Integration: Factory -> Runtime -> Execution
# ======================================================================

class TestFactoryRuntimeIntegration:
    @pytest.mark.asyncio
    async def test_factory_to_runtime(self):
        mgr = ToolManager()
        factory = ToolFactory(manager=mgr)
        factory.register_all_builtins()
        rt = ToolRuntime(manager=mgr)
        result = await rt.execute_tool("web_search", {"query": "python"})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_runtime_shutdown(self):
        mgr = ToolManager()
        factory = ToolFactory(manager=mgr)
        factory.register_all_builtins()
        rt = ToolRuntime(manager=mgr)
        await rt.shutdown()
        d = rt.to_dict()
        assert "manager" in d


# ======================================================================
# Edge cases
# ======================================================================

class TestEdgeCases:
    def test_empty_registry_discover(self):
        r = ToolRegistry()
        assert r.discover(category="anything") == []

    def test_empty_metrics_snapshot(self):
        m = ToolMetrics()
        s = m.snapshot()
        assert s["global"]["executions"] == 0
        assert s["tools"] == {}

    def test_empty_tracer(self):
        t = ToolTracer()
        assert t.to_dict() == []

    def test_context_no_permissions(self):
        ctx = ToolContext()
        assert ctx.has_permission("anything") is False

    def test_policy_kwargs_fallback(self):
        p = get_tool_policy("retryable", max_retries=5)
        assert isinstance(p, RetryablePolicy)
        assert p.max_retries == 5

    def test_manager_empty_discover(self):
        mgr = ToolManager()
        assert mgr.discover(category="x") == []
