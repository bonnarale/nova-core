"""Tests for the Tool Runtime — base, registry, executor, permissions, exceptions, result, built-in tools."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.agent_manager import AgentManager
from app.agents.metrics import MetricsCollector
from app.agents.tracing import Tracer
from app.tools.base import Tool, ToolParam, ToolSpec
from app.tools.docker import DockerTool
from app.tools.exceptions import (
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolPermissionError,
    ToolTimeoutError,
    ToolValidationError,
)
from app.tools.executor import ToolExecutor
from app.tools.filesystem import FilesystemTool
from app.tools.git import GitTool
from app.tools.http import HttpTool
from app.tools.permissions import PermissionChecker, PermissionLevel, ToolPermission
from app.tools.python import PythonTool
from app.tools.registry import ToolRegistry
from app.tools.result import ToolResult
from app.tools.web import WebSearchTool
from app.tools import default_tool_registry


# ======================================================================
# ToolResult
# ======================================================================

class TestToolResult:
    def test_defaults(self):
        r = ToolResult()
        assert r.success is True
        assert r.data is None
        assert r.error == ""
        assert r.duration_ms == 0.0
        assert r.tool_name == ""

    def test_to_dict(self):
        r = ToolResult(success=True, data={"key": "val"}, duration_ms=12.34, tool_name="test_tool")
        d = r.to_dict()
        assert d["success"] is True
        assert d["data"] == {"key": "val"}
        assert d["duration_ms"] == 12.34
        assert d["tool_name"] == "test_tool"

    def test_error_result_class_method(self):
        r = ToolResult.error_result("my_tool", "something went wrong", duration_ms=5.0)
        assert r.success is False
        assert r.data is None
        assert r.error == "something went wrong"
        assert r.duration_ms == 5.0
        assert r.tool_name == "my_tool"


# ======================================================================
# Exceptions
# ======================================================================

class TestExceptions:
    def test_tool_error_base(self):
        exc = ToolError("msg", "my_tool")
        assert exc.tool_name == "my_tool"
        assert str(exc) == "msg"

    def test_tool_not_found(self):
        exc = ToolNotFoundError("missing_tool")
        assert "missing_tool" in str(exc)

    def test_tool_validation_error(self):
        exc = ToolValidationError("my_tool", "bad param")
        assert "bad param" in str(exc)

    def test_tool_permission_error(self):
        exc = ToolPermissionError("my_tool", "agent_1")
        assert "agent_1" in str(exc)

    def test_tool_timeout_error(self):
        exc = ToolTimeoutError("my_tool", 30.0)
        assert "30" in str(exc)

    def test_tool_execution_error(self):
        cause = ValueError("root cause")
        exc = ToolExecutionError("my_tool", "failed", cause=cause)
        assert exc.cause is cause


# ======================================================================
# ToolSpec / ToolParam / Tool ABC
# ======================================================================

class _ConcreteTool(Tool):
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="concrete",
            description="A concrete tool for testing",
            parameters=[
                ToolParam(name="input", type="string", required=True, description="The input"),
                ToolParam(name="count", type="integer", required=False, default=1, description="Count"),
            ],
        )

    async def run(self, params: dict) -> ToolResult:
        return ToolResult(success=True, data={"result": f"ran with {params.get('input', '')}"})


class TestToolBase:
    @pytest.mark.asyncio
    async def test_execute_calls_lifecycle(self):
        tool = _ConcreteTool()
        result = await tool.execute({"input": "hello", "count": 3})
        assert result.success is True
        assert "hello" in result.data["result"]

    @pytest.mark.asyncio
    async def test_execute_validates_required_params(self):
        tool = _ConcreteTool()
        with pytest.raises(ToolValidationError, match="Missing required parameter"):
            await tool.execute({})

    @pytest.mark.asyncio
    async def test_execute_validates_types(self):
        tool = _ConcreteTool()
        with pytest.raises(ToolValidationError, match="must be an integer"):
            await tool.execute({"input": "ok", "count": "not_an_int"})

    def test_spec_to_dict(self):
        tool = _ConcreteTool()
        d = tool.spec.to_dict()
        assert d["name"] == "concrete"
        assert len(d["parameters"]) == 2

    @pytest.mark.asyncio
    async def test_before_and_after_hooks(self):
        class _HookedTool(Tool):
            @property
            def spec(self) -> ToolSpec:
                return ToolSpec(name="hooked", parameters=[])

            async def run(self, params: dict) -> ToolResult:
                return ToolResult(data={"from_run": True})

            async def before_run(self, params: dict) -> dict:
                params["mutated"] = True
                return params

            async def after_run(self, result: ToolResult) -> ToolResult:
                result.metadata["mutated"] = True
                return result

        tool = _HookedTool()
        result = await tool.execute({})
        assert result.success is True
        assert result.data["from_run"] is True
        assert result.metadata["mutated"] is True


# ======================================================================
# ToolRegistry
# ======================================================================

class TestToolRegistry:
    def test_register_and_lookup(self):
        registry = ToolRegistry()
        tool = _ConcreteTool()
        registry.register(tool)
        assert registry.lookup("concrete") is tool

    def test_lookup_not_found_raises(self):
        registry = ToolRegistry()
        with pytest.raises(ToolNotFoundError):
            registry.lookup("nonexistent")

    def test_get_tool_returns_none(self):
        registry = ToolRegistry()
        assert registry.get_tool("nonexistent") is None

    def test_unregister(self):
        registry = ToolRegistry()
        tool = _ConcreteTool()
        registry.register(tool)
        registry.unregister("concrete")
        assert "concrete" not in registry

    def test_list_tools(self):
        registry = ToolRegistry()
        registry.register(_ConcreteTool())
        specs = registry.list_tools()
        assert len(specs) == 1
        assert specs[0].name == "concrete"

    def test_list_tool_specs_dict(self):
        registry = ToolRegistry()
        registry.register(_ConcreteTool())
        specs = registry.list_tool_specs_dict()
        assert len(specs) == 1
        assert specs[0]["name"] == "concrete"

    def test_contains(self):
        registry = ToolRegistry()
        registry.register(_ConcreteTool())
        assert "concrete" in registry
        assert "missing" not in registry

    def test_len(self):
        registry = ToolRegistry()
        assert len(registry) == 0
        registry.register(_ConcreteTool())
        assert len(registry) == 1

    def test_clear(self):
        registry = ToolRegistry()
        registry.register(_ConcreteTool())
        registry.clear()
        assert len(registry) == 0


# ======================================================================
# Permissions
# ======================================================================

class TestPermissions:
    def test_permission_allows_star(self):
        p = ToolPermission(tool_name="test_tool", allowed_agents=["*"])
        assert p.allows("any_agent") is True

    def test_permission_denies_none_level(self):
        p = ToolPermission(tool_name="test_tool", level=PermissionLevel.NONE)
        assert p.allows("agent_1") is False

    def test_permission_denies_unlisted_agent(self):
        p = ToolPermission(tool_name="test_tool", allowed_agents=["agent_1", "agent_2"])
        assert p.allows("agent_3") is False

    def test_permission_allows_listed_agent(self):
        p = ToolPermission(tool_name="test_tool", allowed_agents=["agent_1"])
        assert p.allows("agent_1") is True

    def test_checker_default_allows(self):
        checker = PermissionChecker()
        assert checker.check("unknown_tool", "any_agent") is True

    def test_checker_with_rules(self):
        rule = ToolPermission(tool_name="secret", allowed_agents=["admin"])
        checker = PermissionChecker(rules={"secret": rule})
        assert checker.check("secret", "admin") is True
        assert checker.check("secret", "user") is False

    def test_checker_register(self):
        checker = PermissionChecker()
        checker.register(ToolPermission(tool_name="my_tool", allowed_agents=["foo"]))
        assert checker.check("my_tool", "foo") is True
        assert checker.check("my_tool", "bar") is False

    def test_checker_unregister(self):
        checker = PermissionChecker()
        checker.register(ToolPermission(tool_name="my_tool"))
        checker.unregister("my_tool")
        assert checker.check("my_tool", "any") is True

    def test_to_dict(self):
        checker = PermissionChecker()
        checker.register(ToolPermission(tool_name="my_tool", allowed_agents=["agent_a"]))
        d = checker.to_dict()
        assert "my_tool" in d
        assert d["my_tool"]["allowed_agents"] == ["agent_a"]


# ======================================================================
# ToolExecutor
# ======================================================================

class _AlwaysWorksTool(Tool):
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(name="always_works", parameters=[
            ToolParam(name="x", type="string", required=True),
        ])

    async def run(self, params: dict) -> ToolResult:
        return ToolResult(success=True, data={"echo": params.get("x", "")})


class _NeverWorksTool(Tool):
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(name="never_works", parameters=[])

    async def run(self, params: dict) -> ToolResult:
        raise RuntimeError("always fails")


class _SlowTool(Tool):
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(name="slow", parameters=[])

    async def run(self, params: dict) -> ToolResult:
        await asyncio.sleep(10)
        return ToolResult(success=True)


class TestToolExecutor:
    @pytest.fixture
    def registry(self):
        r = ToolRegistry()
        r.register(_AlwaysWorksTool())
        r.register(_NeverWorksTool())
        return r

    @pytest.fixture
    def executor(self, registry):
        return ToolExecutor(registry=registry, default_timeout=5.0, default_retries=0)

    @pytest.mark.asyncio
    async def test_execute_success(self, executor):
        result = await executor.execute("always_works", {"x": "test_val"})
        assert result.success is True
        assert result.data["echo"] == "test_val"
        assert result.tool_name == "always_works"

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, executor):
        result = await executor.execute("nonexistent")
        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_execute_validation_failure(self, executor):
        result = await executor.execute("always_works", {})  # missing 'x'
        assert result.success is False
        assert "Missing required parameter" in result.error

    @pytest.mark.asyncio
    async def test_execute_runtime_error(self, executor):
        result = await executor.execute("never_works")
        assert result.success is False
        assert "always fails" in result.error

    @pytest.mark.asyncio
    async def test_execute_permission_denied(self, registry):
        checker = PermissionChecker()
        checker.register(ToolPermission(tool_name="always_works", allowed_agents=["admin"]))
        executor = ToolExecutor(registry=registry, permission_checker=checker)
        result = await executor.execute("always_works", {"x": "test"}, agent_id="user1")
        assert result.success is False
        assert "not permitted" in result.error

    @pytest.mark.asyncio
    async def test_execute_timeout(self):
        registry = ToolRegistry()
        registry.register(_SlowTool())
        executor = ToolExecutor(registry=registry, default_timeout=0.1, default_retries=0)
        result = await executor.execute("slow")
        assert result.success is False
        assert "Timed out" in result.error

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, registry):
        executor = ToolExecutor(registry=registry, default_timeout=0.1, default_retries=2)
        result = await executor.execute("slow")
        assert result.success is False
        # Should have retried before giving up

    @pytest.mark.asyncio
    async def test_retry_on_error(self, registry):
        executor = ToolExecutor(registry=registry, default_timeout=5.0, default_retries=2)
        result = await executor.execute("never_works")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_tracing_integration(self, registry):
        tracer = Tracer()
        executor = ToolExecutor(registry=registry, tracer=tracer)
        await executor.execute("always_works", {"x": "trace_me"}, agent_id="test_agent")
        traces = tracer.get_all_traces()
        assert len(traces) > 0
        # Find our span
        found = False
        for trace_spans in traces.values():
            for span in trace_spans:
                if span.agent_id == "tool:always_works":
                    found = True
                    assert span.status == "success"
        assert found, "Expected a trace span for tool:always_works"

    @pytest.mark.asyncio
    async def test_metrics_integration(self, registry):
        metrics = MetricsCollector()
        executor = ToolExecutor(registry=registry, metrics=metrics)
        await executor.execute("always_works", {"x": "count_me"})
        snapshot = metrics.snapshot()
        counters = snapshot["counters"]
        assert counters.get("tool.always_works.calls", 0) >= 1
        assert counters.get("tool.always_works.success", 0) >= 1

    @pytest.mark.asyncio
    async def test_list_tools(self, executor):
        specs = await executor.list_tools()
        names = {s.name for s in specs}
        assert "always_works" in names
        assert "never_works" in names

    @pytest.mark.asyncio
    async def test_get_spec(self, executor):
        spec = await executor.get_spec("always_works")
        assert spec is not None
        assert spec.name == "always_works"

    @pytest.mark.asyncio
    async def test_get_spec_nonexistent(self, executor):
        spec = await executor.get_spec("nope")
        assert spec is None

    @pytest.mark.asyncio
    async def test_execute_non_toolresult_return(self, registry):
        class _DictTool(Tool):
            @property
            def spec(self) -> ToolSpec:
                return ToolSpec(name="dict_returner", parameters=[])
            async def run(self, params: dict) -> ToolResult:
                return {"raw": "data"}

        registry.register(_DictTool())
        executor = ToolExecutor(registry=registry)
        result = await executor.execute("dict_returner")
        assert result.success is True
        assert result.data == {"raw": "data"}


# ======================================================================
# Permission-based executor
# ======================================================================

class TestToolExecutorWithPermissions:
    @pytest.mark.asyncio
    async def test_permission_check_on_execute(self):
        registry = ToolRegistry()
        registry.register(_AlwaysWorksTool())
        checker = PermissionChecker()
        checker.register(ToolPermission(tool_name="always_works", level=PermissionLevel.ADMIN, allowed_agents=["super"]))
        executor = ToolExecutor(registry=registry, permission_checker=checker)

        # Without proper agent_id
        result = await executor.execute("always_works", {"x": "hi"})
        assert result.success is False

        # With proper agent_id
        result = await executor.execute("always_works", {"x": "hi"}, agent_id="super")
        assert result.success is True


# ======================================================================
# Built-in tools: FilesystemTool
# ======================================================================

class TestFilesystemTool:
    @pytest.fixture
    def tool(self):
        return FilesystemTool()

    @pytest.mark.asyncio
    async def test_write_and_read(self, tool):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test.txt")
            write_result = await tool.run({"operation": "write", "path": path, "content": "hello world"})
            assert write_result.success is True

            read_result = await tool.run({"operation": "read", "path": path})
            assert read_result.success is True
            assert read_result.data["content"] == "hello world"

    @pytest.mark.asyncio
    async def test_list_directory(self, tool):
        with tempfile.TemporaryDirectory() as tmp:
            Path(os.path.join(tmp, "a.txt")).touch()
            Path(os.path.join(tmp, "b.txt")).touch()
            result = await tool.run({"operation": "list", "path": tmp})
            assert result.success is True
            assert result.data["count"] == 2

    @pytest.mark.asyncio
    async def test_exists(self, tool):
        with tempfile.TemporaryDirectory() as tmp:
            result = await tool.run({"operation": "exists", "path": tmp})
            assert result.success is True
            assert result.data["exists"] is True

            result = await tool.run({"operation": "exists", "path": os.path.join(tmp, "nonexistent")})
            assert result.data["exists"] is False

    @pytest.mark.asyncio
    async def test_mkdir(self, tool):
        with tempfile.TemporaryDirectory() as tmp:
            new_dir = os.path.join(tmp, "new_dir")
            result = await tool.run({"operation": "mkdir", "path": new_dir})
            assert result.success is True
            assert os.path.isdir(new_dir)

    @pytest.mark.asyncio
    async def test_delete_file(self, tool):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "to_delete.txt")
            Path(path).write_text("delete me")
            result = await tool.run({"operation": "delete", "path": path})
            assert result.success is True
            assert not os.path.exists(path)

    @pytest.mark.asyncio
    async def test_delete_directory(self, tool):
        with tempfile.TemporaryDirectory() as tmp:
            sub = os.path.join(tmp, "subdir")
            os.mkdir(sub)
            result = await tool.run({"operation": "delete", "path": sub})
            assert result.success is True
            assert not os.path.exists(sub)

    @pytest.mark.asyncio
    async def test_copy_file(self, tool):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "src.txt")
            dst = os.path.join(tmp, "dst.txt")
            Path(src).write_text("content")
            result = await tool.run({"operation": "copy", "path": src, "destination": dst})
            assert result.success is True
            assert os.path.exists(dst)

    @pytest.mark.asyncio
    async def test_move_file(self, tool):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "src.txt")
            dst = os.path.join(tmp, "dst.txt")
            Path(src).write_text("content")
            result = await tool.run({"operation": "move", "path": src, "destination": dst})
            assert result.success is True
            assert os.path.exists(dst)
            assert not os.path.exists(src)

    @pytest.mark.asyncio
    async def test_unknown_operation(self, tool):
        result = await tool.run({"operation": "unknown", "path": "/tmp"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, tool):
        result = await tool.run({"operation": "read", "path": "/tmp/nonexistent_file_12345"})
        assert result.success is False
        assert "not found" in result.error.lower()


# ======================================================================
# Built-in tools: HttpTool
# ======================================================================

class TestHttpTool:
    @pytest.fixture
    def tool(self):
        return HttpTool()

    @pytest.mark.asyncio
    async def test_unsupported_method(self, tool):
        result = await tool.run({"method": "OPTIONS", "url": "http://example.com"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_missing_url(self, tool):
        result = await tool.run({"method": "GET", "url": ""})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_spec(self, tool):
        assert tool.spec.name == "http"
        assert tool.spec.timeout_default == 30.0


# ======================================================================
# Built-in tools: WebSearchTool
# ======================================================================

class TestWebSearchTool:
    @pytest.fixture
    def tool(self):
        return WebSearchTool()

    @pytest.mark.asyncio
    async def test_search_stub(self, tool):
        result = await tool.run({"query": "python programming"})
        assert result.success is True
        assert result.metadata.get("stub") is True
        assert result.data["results"] == []

    @pytest.mark.asyncio
    async def test_missing_query(self, tool):
        result = await tool.run({})
        assert result.success is False

    def test_spec(self, tool):
        assert tool.spec.name == "web_search"
        assert tool.spec.category == "network"


# ======================================================================
# Built-in tools: GitTool (unit tests with mocked subprocess)
# ======================================================================

class TestGitTool:
    @pytest.fixture
    def tool(self):
        return GitTool()

    @pytest.mark.asyncio
    async def test_unknown_operation(self, tool):
        result = await tool.run({"operation": "xyz", "repo_path": "/tmp"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_nonexistent_repo_path(self, tool):
        result = await tool.run({"operation": "status", "repo_path": "/nonexistent_path_abc"})
        assert result.success is False

    def test_spec(self, tool):
        assert tool.spec.name == "git"
        assert tool.spec.timeout_default == 60.0


# ======================================================================
# Built-in tools: DockerTool (unit tests)
# ======================================================================

class TestDockerTool:
    @pytest.fixture
    def tool(self):
        return DockerTool()

    @pytest.mark.asyncio
    async def test_unknown_operation(self, tool):
        result = await tool.run({"operation": "xyz"})
        assert result.success is False

    def test_spec(self, tool):
        assert tool.spec.name == "docker"
        assert tool.spec.permission_level == "admin"


# ======================================================================
# Built-in tools: PythonTool (unit tests)
# ======================================================================

class TestPythonTool:
    @pytest.fixture
    def tool(self):
        return PythonTool()

    @pytest.mark.asyncio
    async def test_missing_code(self, tool):
        result = await tool.run({"operation": "eval"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_missing_file_path(self, tool):
        result = await tool.run({"operation": "run_file"})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_unknown_operation(self, tool):
        result = await tool.run({"operation": "xyz"})
        assert result.success is False

    def test_spec(self, tool):
        assert tool.spec.name == "python"
        assert tool.spec.permission_level == "admin"


# ======================================================================
# default_tool_registry
# ======================================================================

class TestDefaultToolRegistry:
    def test_all_builtins_registered(self):
        registry = default_tool_registry()
        names = {s.name for s in registry.list_tools()}
        expected = {"filesystem", "git", "docker", "python", "http", "web_search"}
        assert names == expected

    def test_each_tool_is_accessible(self):
        registry = default_tool_registry()
        for name in ("filesystem", "git", "docker", "python", "http", "web_search"):
            tool = registry.get_tool(name)
            assert tool is not None, f"{name} should be registered"


# ======================================================================
# AgentManager integration
# ======================================================================

class TestAgentManagerIntegration:
    @pytest.mark.asyncio
    async def test_tool_executor_injected_into_context(self):
        registry = ToolRegistry()
        registry.register(_AlwaysWorksTool())
        executor = ToolExecutor(registry=registry)

        db = MagicMock()
        db.session_factory = MagicMock()
        am = AgentManager(database=db, tool_executor=executor)

        # Register a mock agent that checks context for tool_executor
        mock_agent = MagicMock()
        mock_agent.agent_id = "test_agent"
        mock_agent.execute = AsyncMock(return_value={"status": "completed"})
        am.register_runtime_agent(mock_agent)

        await am.dispatch("test_agent", "do something", {"extra": "data"})

        _call_context = mock_agent.execute.call_args[0][1]
        assert "tool_executor" in _call_context
        assert _call_context["tool_executor"] is executor
        assert "tool_registry" in _call_context
        assert _call_context["tool_registry"] is registry

    @pytest.mark.asyncio
    async def test_agentmanager_without_tool_executor(self):
        db = MagicMock()
        db.session_factory = MagicMock()
        am = AgentManager(database=db)  # no tool_executor

        mock_agent = MagicMock()
        mock_agent.agent_id = "test_agent"
        mock_agent.execute = AsyncMock(return_value={"status": "completed"})
        am.register_runtime_agent(mock_agent)

        await am.dispatch("test_agent", "task")
        _call_context = mock_agent.execute.call_args[0][1]
        assert "tool_executor" not in _call_context
