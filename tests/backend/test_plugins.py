"""Tests for Plugin subsystem — enums, models, base ABCs, lifecycle, registry,
loader, sandbox, config, hooks, discovery, dependency, version, middleware,
metrics, tracing, events, sandbox_manager, manager, engine, factory, API routes.
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.plugins.api import PluginAPI
from app.plugins.base import (
    HookHandler,
    PluginBase,
    PluginDiscovery,
    PluginMiddlewareBase,
    PluginProvider,
    PluginRepository,
    PluginValidator,
)
from app.plugins.config import PluginConfigManager
from app.plugins.dependency import DependencyResolver
from app.plugins.discovery import PluginDiscoveryService
from app.plugins.engine import PluginEngine
from app.plugins.enums import (
    HookPriority,
    HookType,
    PluginEventType,
    PluginPermission,
    PluginState,
    PluginType,
)
from app.plugins.events import PluginEvent, PluginEventBus
from app.plugins.exceptions import (
    HookError,
    PluginConflictError,
    PluginDependencyError,
    PluginError,
    PluginInitError,
    PluginLoadError,
    PluginNotFoundError,
    PluginSandboxError,
    PluginTimeoutError,
    PluginValidationError,
    PluginVersionError,
)
from app.plugins.factory import PluginFactory
from app.plugins.hooks import HookManager, HookRegistry
from app.plugins.lifecycle import PluginLifecycle
from app.plugins.loader import PluginLoader
from app.plugins.manifest import ManifestValidator
from app.plugins.manager import PluginManager
from app.plugins.metrics import PluginMetrics, get_plugin_metrics
from app.plugins.middleware import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    MiddlewareChain,
    TimingMiddleware,
)
from app.plugins.models import (
    HookContext,
    HookRegistration,
    PluginDependency,
    PluginEvent,
    PluginExecutionResult,
    PluginInfo,
    PluginManifest,
    PluginStatistics,
    SandboxConfig,
)
from app.plugins.persistence import InMemoryPluginRepository
from app.plugins.registry import PluginRegistry
from app.plugins.sandbox import PluginSandbox
from app.plugins.sandbox_manager import SandboxManager
from app.plugins.schemas import (
    ExecutePluginRequest,
    HookListResponse,
    HookStatisticsResponse,
    PluginConfigResponse,
    PluginEventsResponse,
    PluginExecutionResponse,
    PluginHealthResponse,
    PluginListResponse,
    PluginResponse,
    PluginStatisticsResponse,
    RegisterPluginRequest,
    SandboxStatsResponse,
)
from app.plugins.tracing import PluginTracer
from app.plugins.version import SemVer, VersionManager


# ======================================================================
# Enums
# ======================================================================

class TestEnums:
    def test_plugin_state_values(self):
        assert PluginState.REGISTERED.value == "registered"
        assert PluginState.RUNNING.value == "running"
        assert PluginState.ERROR.value == "error"

    def test_plugin_type_values(self):
        assert PluginType.CORE.value == "core"
        assert PluginType.EXTENSION.value == "extension"
        assert PluginType.TOOL.value == "tool"

    def test_plugin_permission_values(self):
        assert PluginPermission.NONE.value == "none"
        assert PluginPermission.READ.value == "read"
        assert PluginPermission.ADMIN.value == "admin"

    def test_hook_type_values(self):
        assert HookType.BEFORE.value == "before"
        assert HookType.AFTER.value == "after"
        assert HookType.AROUND.value == "around"

    def test_hook_priority_values(self):
        assert HookPriority.LOWEST.value == 100
        assert HookPriority.NORMAL.value == 50
        assert HookPriority.HIGHEST.value == 0

    def test_plugin_event_type_values(self):
        assert PluginEventType.REGISTERED.value == "registered"
        assert PluginEventType.ERROR.value == "error"

    def test_all_plugin_states(self):
        states = list(PluginState)
        assert len(states) == 9

    def test_all_plugin_types(self):
        types = list(PluginType)
        assert len(types) == 8


# ======================================================================
# Models
# ======================================================================

class TestModels:
    def test_plugin_dependency_defaults(self):
        dep = PluginDependency()
        assert dep.plugin_id == ""
        assert dep.required is True

    def test_plugin_dependency_to_dict(self):
        dep = PluginDependency(plugin_id="test", version_min="1.0.0")
        d = dep.to_dict()
        assert d["plugin_id"] == "test"
        assert d["version_min"] == "1.0.0"

    def test_plugin_manifest_defaults(self):
        manifest = PluginManifest()
        assert manifest.plugin_id == ""
        assert manifest.version == "1.0.0"
        assert manifest.plugin_type == PluginType.EXTENSION

    def test_plugin_manifest_to_dict(self):
        manifest = PluginManifest(plugin_id="test", name="Test")
        d = manifest.to_dict()
        assert d["plugin_id"] == "test"
        assert d["name"] == "Test"
        assert d["type"] == "extension"

    def test_plugin_info_defaults(self):
        info = PluginInfo()
        assert info.state == PluginState.REGISTERED

    def test_plugin_info_to_dict(self):
        manifest = PluginManifest(plugin_id="p1", name="P1")
        info = PluginInfo(manifest=manifest, state=PluginState.RUNNING)
        d = info.to_dict()
        assert d["plugin_id"] == "p1"
        assert d["state"] == "running"

    def test_hook_registration_defaults(self):
        reg = HookRegistration()
        assert reg.hook_type == HookType.BEFORE
        assert reg.priority == HookPriority.NORMAL

    def test_hook_registration_to_dict(self):
        reg = HookRegistration(hook_name="test", plugin_id="p1")
        d = reg.to_dict()
        assert d["hook_name"] == "test"

    def test_hook_context_defaults(self):
        ctx = HookContext()
        assert ctx.hook_type == HookType.BEFORE

    def test_hook_context_to_dict(self):
        ctx = HookContext(hook_name="test", data={"key": "value"})
        d = ctx.to_dict()
        assert d["hook_name"] == "test"
        assert d["data"]["key"] == "value"

    def test_plugin_event_defaults(self):
        event = PluginEvent()
        assert event.event_type == ""

    def test_plugin_event_to_dict(self):
        event = PluginEvent(event_id="e1", event_type="test")
        d = event.to_dict()
        assert d["event_id"] == "e1"

    def test_plugin_execution_result_defaults(self):
        result = PluginExecutionResult()
        assert result.success is True

    def test_plugin_execution_result_to_dict(self):
        result = PluginExecutionResult(success=False, error="fail")
        d = result.to_dict()
        assert d["success"] is False
        assert d["error"] == "fail"

    def test_sandbox_config_defaults(self):
        config = SandboxConfig()
        assert config.max_memory_mb == 256.0
        assert config.restricted is True

    def test_sandbox_config_to_dict(self):
        config = SandboxConfig(max_memory_mb=512.0)
        d = config.to_dict()
        assert d["max_memory_mb"] == 512.0

    def test_plugin_statistics_defaults(self):
        stats = PluginStatistics()
        assert stats.total_plugins == 0

    def test_plugin_statistics_to_dict(self):
        stats = PluginStatistics(total_plugins=5, active_plugins=3)
        d = stats.to_dict()
        assert d["total_plugins"] == 5


# ======================================================================
# Base ABCs
# ======================================================================

class TestBaseABCs:
    def test_plugin_provider_is_abstract(self):
        with pytest.raises(TypeError):
            PluginProvider()

    def test_plugin_base_is_abstract(self):
        with pytest.raises(TypeError):
            PluginBase()

    def test_hook_handler_is_abstract(self):
        with pytest.raises(TypeError):
            HookHandler()

    def test_plugin_repository_is_abstract(self):
        with pytest.raises(TypeError):
            PluginRepository()

    def test_plugin_middleware_base_is_abstract(self):
        with pytest.raises(TypeError):
            PluginMiddlewareBase()

    def test_plugin_discovery_is_abstract(self):
        with pytest.raises(TypeError):
            PluginDiscovery()

    def test_plugin_validator_is_abstract(self):
        with pytest.raises(TypeError):
            PluginValidator()


# ======================================================================
# Lifecycle
# ======================================================================

class TestPluginLifecycle:
    def test_default_state(self):
        lc = PluginLifecycle("test")
        assert lc.state == PluginState.REGISTERED

    def test_valid_transitions(self):
        lc = PluginLifecycle("test")
        lc.transition(PluginState.LOADING)
        assert lc.state == PluginState.LOADING
        lc.transition(PluginState.LOADED)
        assert lc.state == PluginState.LOADED
        lc.transition(PluginState.INITIALIZING)
        lc.transition(PluginState.RUNNING)
        assert lc.state == PluginState.RUNNING

    def test_invalid_transition_raises(self):
        lc = PluginLifecycle("test")
        with pytest.raises(ValueError):
            lc.transition(PluginState.RUNNING)

    def test_is_running(self):
        lc = PluginLifecycle("test")
        lc.transition(PluginState.LOADING)
        lc.transition(PluginState.LOADED)
        lc.transition(PluginState.INITIALIZING)
        lc.transition(PluginState.RUNNING)
        assert lc.is_running() is True

    def test_is_error(self):
        lc = PluginLifecycle("test")
        lc.transition(PluginState.LOADING)
        lc.transition(PluginState.ERROR)
        assert lc.is_error() is True

    def test_to_dict(self):
        lc = PluginLifecycle("test")
        d = lc.to_dict()
        assert d["plugin_id"] == "test"
        assert d["state"] == "registered"

    def test_state_history(self):
        lc = PluginLifecycle("test")
        lc.transition(PluginState.LOADING)
        assert len(lc.state_history) == 2

    def test_stop_flow(self):
        lc = PluginLifecycle("test")
        lc.transition(PluginState.LOADING)
        lc.transition(PluginState.LOADED)
        lc.transition(PluginState.INITIALIZING)
        lc.transition(PluginState.RUNNING)
        lc.transition(PluginState.STOPPING)
        lc.transition(PluginState.STOPPED)
        assert lc.state == PluginState.STOPPED


# ======================================================================
# Registry
# ======================================================================

class TestPluginRegistry:
    def test_register_and_get(self):
        reg = PluginRegistry()
        manifest = PluginManifest(plugin_id="p1", name="P1")
        reg.register(manifest)
        assert reg.get("p1").manifest.plugin_id == "p1"

    def test_get_not_found(self):
        reg = PluginRegistry()
        with pytest.raises(PluginNotFoundError):
            reg.get("missing")

    def test_unregister(self):
        reg = PluginRegistry()
        manifest = PluginManifest(plugin_id="p1")
        reg.register(manifest)
        reg.unregister("p1")
        assert not reg.contains("p1")

    def test_list_all(self):
        reg = PluginRegistry()
        for i in range(3):
            reg.register(PluginManifest(plugin_id=f"p{i}", name=f"P{i}"))
        assert reg.count() == 3

    def test_list_by_type(self):
        reg = PluginRegistry()
        reg.register(PluginManifest(plugin_id="c1", plugin_type=PluginType.CORE))
        reg.register(PluginManifest(plugin_id="e1", plugin_type=PluginType.EXTENSION))
        assert len(reg.list_by_type(PluginType.CORE)) == 1

    def test_list_by_capability(self):
        reg = PluginRegistry()
        reg.register(PluginManifest(plugin_id="p1", capabilities=["auth"]))
        assert len(reg.list_by_capability("auth")) == 1

    def test_list_by_tag(self):
        reg = PluginRegistry()
        reg.register(PluginManifest(plugin_id="p1", tags=["security"]))
        assert len(reg.list_by_tag("security")) == 1

    def test_list_enabled_disabled(self):
        reg = PluginRegistry()
        reg.register(PluginManifest(plugin_id="e1", enabled=True))
        reg.register(PluginManifest(plugin_id="d1", enabled=False))
        assert len(reg.list_enabled()) == 1
        assert len(reg.list_disabled()) == 1

    def test_update_state(self):
        reg = PluginRegistry()
        reg.register(PluginManifest(plugin_id="p1"))
        reg.update_state("p1", PluginState.RUNNING)
        assert reg.get("p1").state == PluginState.RUNNING

    def test_to_dict(self):
        reg = PluginRegistry()
        reg.register(PluginManifest(plugin_id="p1"))
        d = reg.to_dict()
        assert d["total"] == 1


# ======================================================================
# Loader
# ======================================================================

class TestPluginLoader:
    @pytest.mark.asyncio
    async def test_load_plugin(self):
        registry = PluginRegistry()
        loader = PluginLoader(registry)
        manifest = PluginManifest(plugin_id="p1", name="P1")
        info = await loader.load(manifest)
        assert info.state == PluginState.LOADED

    @pytest.mark.asyncio
    async def test_load_with_config(self):
        registry = PluginRegistry()
        loader = PluginLoader(registry)
        manifest = PluginManifest(plugin_id="p1")
        info = await loader.load(manifest, config={"key": "value"})
        assert info.config["key"] == "value"

    @pytest.mark.asyncio
    async def test_unload(self):
        registry = PluginRegistry()
        loader = PluginLoader(registry)
        manifest = PluginManifest(plugin_id="p1")
        await loader.load(manifest)
        await loader.unload("p1")
        assert registry.get("p1").state == PluginState.STOPPED

    @pytest.mark.asyncio
    async def test_register_class(self):
        registry = PluginRegistry()
        loader = PluginLoader(registry)
        class DummyPlugin:
            pass
        loader.register_class("p1", DummyPlugin)
        assert loader.has_class("p1")

    def test_list_classes(self):
        registry = PluginRegistry()
        loader = PluginLoader(registry)
        loader.register_class("a", type("A", (), {}))
        loader.register_class("b", type("B", (), {}))
        assert len(loader.list_classes()) == 2


# ======================================================================
# Sandbox
# ======================================================================

class TestPluginSandbox:
    def test_default_config(self):
        sb = PluginSandbox()
        assert sb.config.restricted is True

    def test_check_permission_allowed(self):
        sb = PluginSandbox(SandboxConfig(allowed_permissions=[PluginPermission.READ]))
        assert sb.check_permission("p1", PluginPermission.READ) is True

    def test_check_permission_denied(self):
        sb = PluginSandbox(SandboxConfig(restricted=True, allowed_permissions=[]))
        assert sb.check_permission("p1", PluginPermission.WRITE) is False
        assert len(sb.violations) == 1

    @pytest.mark.asyncio
    async def test_execute_success(self):
        sb = PluginSandbox()
        async def func():
            return "ok"
        result = await sb.execute("p1", func)
        assert result.success is True
        assert result.result == "ok"

    @pytest.mark.asyncio
    async def test_execute_error(self):
        sb = PluginSandbox()
        async def func():
            raise ValueError("test")
        result = await sb.execute("p1", func)
        assert result.success is False
        assert "test" in result.error

    def test_stats(self):
        sb = PluginSandbox()
        stats = sb.get_stats()
        assert stats["active_count"] == 0

    def test_unrestricted_mode(self):
        sb = PluginSandbox(SandboxConfig(restricted=False))
        assert sb.check_permission("p1", PluginPermission.ADMIN) is True


# ======================================================================
# Config Manager
# ======================================================================

class TestPluginConfigManager:
    def test_set_and_get(self):
        cm = PluginConfigManager()
        cm.set_config("p1", {"key": "value"})
        assert cm.get_config("p1")["key"] == "value"

    def test_get_default(self):
        cm = PluginConfigManager()
        assert cm.get_config("missing") == {}

    def test_set_default(self):
        cm = PluginConfigManager()
        cm.set_default("p1", {"timeout": 30})
        assert cm.get_value("p1", "timeout") == 30

    def test_get_value_default(self):
        cm = PluginConfigManager()
        assert cm.get_value("p1", "missing", "fallback") == "fallback"

    def test_remove(self):
        cm = PluginConfigManager()
        cm.set_config("p1", {"a": 1})
        cm.remove_config("p1")
        assert not cm.has_config("p1")

    def test_reset(self):
        cm = PluginConfigManager()
        cm.set_default("p1", {"a": 1})
        cm.set_config("p1", {"a": 2})
        cm.reset_config("p1")
        assert cm.get_value("p1", "a") == 1

    def test_merge(self):
        cm = PluginConfigManager()
        cm.set_config("p1", {"a": 1, "b": 2})
        cm.merge_config("p1", {"b": 3, "c": 4})
        config = cm.get_config("p1")
        assert config["a"] == 1
        assert config["b"] == 3
        assert config["c"] == 4

    def test_list_configs(self):
        cm = PluginConfigManager()
        cm.set_config("p1", {"a": 1})
        cm.set_config("p2", {"b": 2})
        configs = cm.list_configs()
        assert len(configs) == 2


# ======================================================================
# Hooks
# ======================================================================

class TestHookRegistry:
    def test_register_and_get(self):
        hr = HookRegistry()
        hr.register("test.hook", "p1")
        hooks = hr.get_hooks("test.hook")
        assert len(hooks) == 1

    def test_unregister(self):
        hr = HookRegistry()
        hr.register("test.hook", "p1")
        assert hr.unregister("test.hook", "p1") is True

    def test_unregister_missing(self):
        hr = HookRegistry()
        assert hr.unregister("test.hook", "p1") is False

    def test_get_hooks_by_type(self):
        hr = HookRegistry()
        hr.register("h", "p1", hook_type=HookType.BEFORE)
        hr.register("h", "p2", hook_type=HookType.AFTER)
        before = hr.get_hooks_by_type("h", HookType.BEFORE)
        assert len(before) == 1

    def test_count(self):
        hr = HookRegistry()
        hr.register("h1", "p1")
        hr.register("h2", "p2")
        assert hr.count() == 2

    def test_clear(self):
        hr = HookRegistry()
        hr.register("h1", "p1")
        hr.clear()
        assert hr.count() == 0


class TestHookManager:
    @pytest.mark.asyncio
    async def test_fire_hook(self):
        hr = HookRegistry()
        hm = HookManager(hr)
        ctx = HookContext(hook_name="test", hook_type=HookType.BEFORE)
        result = await hm.fire("test", ctx)
        assert result is not None

    def test_statistics(self):
        hm = HookManager()
        stats = hm.get_statistics()
        assert "total_hooks" in stats

    def test_execution_log(self):
        hm = HookManager()
        log = hm.get_execution_log()
        assert isinstance(log, list)


# ======================================================================
# Discovery
# ======================================================================

class TestPluginDiscovery:
    @pytest.mark.asyncio
    async def test_discover(self):
        ds = PluginDiscoveryService()
        m = PluginManifest(plugin_id="p1")
        ds.add_manifest(m)
        result = await ds.discover()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_discover_by_type(self):
        ds = PluginDiscoveryService()
        ds.add_manifest(PluginManifest(plugin_id="c1", plugin_type=PluginType.CORE))
        ds.add_manifest(PluginManifest(plugin_id="e1", plugin_type=PluginType.EXTENSION))
        result = await ds.discover_by_type("core")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_discover_by_capability(self):
        ds = PluginDiscoveryService()
        ds.add_manifest(PluginManifest(plugin_id="p1", capabilities=["auth"]))
        result = await ds.discover_by_capability("auth")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_discover_by_tag(self):
        ds = PluginDiscoveryService()
        ds.add_manifest(PluginManifest(plugin_id="p1", tags=["security"]))
        result = await ds.discover_by_tag("security")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_discover_enabled(self):
        ds = PluginDiscoveryService()
        ds.add_manifest(PluginManifest(plugin_id="e1", enabled=True))
        ds.add_manifest(PluginManifest(plugin_id="d1", enabled=False))
        result = await ds.discover_enabled()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_discover_with_validation(self):
        ds = PluginDiscoveryService()
        ds.add_manifest(PluginManifest(plugin_id="p1", name="P1", version="1.0.0"))
        valid, errors = await ds.discover_with_validation()
        assert len(valid) == 1

    def test_add_source(self):
        ds = PluginDiscoveryService()
        ds.add_source("filesystem", {"path": "/plugins"})
        assert len(ds.list_sources()) == 1

    def test_count(self):
        ds = PluginDiscoveryService()
        ds.add_manifest(PluginManifest(plugin_id="p1"))
        assert ds.count() == 1


# ======================================================================
# Dependency Resolver
# ======================================================================

class TestDependencyResolver:
    def test_resolve_no_deps(self):
        dr = DependencyResolver()
        dr.add_plugin(PluginManifest(plugin_id="a"))
        dr.add_plugin(PluginManifest(plugin_id="b"))
        result = dr.resolve()
        assert len(result) == 2

    def test_resolve_with_deps(self):
        dr = DependencyResolver()
        dr.add_plugin(PluginManifest(plugin_id="b", dependencies=[PluginDependency(plugin_id="a")]))
        dr.add_plugin(PluginManifest(plugin_id="a"))
        result = dr.resolve()
        assert result.index("a") < result.index("b")

    def test_resolve_circular(self):
        dr = DependencyResolver()
        dr.add_plugin(PluginManifest(plugin_id="a", dependencies=[PluginDependency(plugin_id="b")]))
        dr.add_plugin(PluginManifest(plugin_id="b", dependencies=[PluginDependency(plugin_id="a")]))
        with pytest.raises(PluginDependencyError):
            dr.resolve()

    def test_check_missing(self):
        dr = DependencyResolver()
        m = PluginManifest(plugin_id="a", dependencies=[PluginDependency(plugin_id="missing")])
        missing = dr.check_missing([m])
        assert len(missing) == 1

    def test_dependency_tree(self):
        dr = DependencyResolver()
        dr.add_plugin(PluginManifest(plugin_id="a"))
        dr.add_plugin(PluginManifest(plugin_id="b", dependencies=[PluginDependency(plugin_id="a")]))
        tree = dr.get_dependency_tree("b")
        assert tree["plugin_id"] == "b"
        assert len(tree["depends_on"]) == 1


# ======================================================================
# Version Manager
# ======================================================================

class TestVersionManager:
    def test_parse(self):
        v = VersionManager.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_parse_with_prerelease(self):
        v = VersionManager.parse("1.0.0-alpha")
        assert v.prerelease == "alpha"

    def test_parse_invalid(self):
        with pytest.raises(ValueError):
            VersionManager.parse("invalid")

    def test_is_compatible(self):
        assert VersionManager.is_compatible("1.5.0", "1.0.0", "2.0.0") is True
        assert VersionManager.is_compatible("0.9.0", "1.0.0") is False
        assert VersionManager.is_compatible("3.0.0", "", "2.0.0") is False

    def test_is_breaking_change(self):
        assert VersionManager.is_breaking_change("1.0.0", "2.0.0") is True
        assert VersionManager.is_breaking_change("1.0.0", "1.1.0") is False

    def test_backward_compatible(self):
        assert VersionManager.is_backward_compatible("1.0.0", "1.2.0") is True
        assert VersionManager.is_backward_compatible("1.0.0", "2.0.0") is False

    def test_sort(self):
        sorted_v = VersionManager.sort_versions(["2.0.0", "1.0.0", "1.1.0"])
        assert sorted_v == ["1.0.0", "1.1.0", "2.0.0"]

    def test_semver_comparison(self):
        v1 = SemVer(1, 0, 0)
        v2 = SemVer(2, 0, 0)
        assert v1 < v2
        assert v2 > v1


# ======================================================================
# Middleware
# ======================================================================

class TestMiddleware:
    @pytest.mark.asyncio
    async def test_logging_middleware(self):
        mw = LoggingMiddleware()
        ctx = await mw.before_execute("p1", {"operation": "test"})
        assert "_start_time" in ctx
        result = await mw.after_execute("p1", ctx, "ok")
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_timing_middleware(self):
        mw = TimingMiddleware()
        ctx = await mw.before_execute("p1", {})
        await mw.after_execute("p1", ctx, None)
        stats = mw.get_all_statistics()
        assert "p1" in stats

    @pytest.mark.asyncio
    async def test_error_middleware(self):
        mw = ErrorHandlingMiddleware()
        result = await mw.on_error("p1", {}, ValueError("test"))
        assert result is False

    @pytest.mark.asyncio
    async def test_middleware_chain(self):
        chain = MiddlewareChain()
        chain.add(LoggingMiddleware())
        chain.add(TimingMiddleware())
        ctx = await chain.execute_before("p1", {"op": "test"})
        assert "_start_time" in ctx
        result = await chain.execute_after("p1", ctx, "ok")
        assert result == "ok"
        assert chain.count() == 2

    def test_middleware_chain_list(self):
        chain = MiddlewareChain()
        chain.add(LoggingMiddleware())
        assert chain.list_middlewares() == ["logging"]


# ======================================================================
# Metrics
# ======================================================================

class TestPluginMetrics:
    def test_increment(self):
        m = PluginMetrics()
        m.increment("counter1")
        assert m.get_counter("counter1") == 1.0

    def test_decrement(self):
        m = PluginMetrics()
        m.increment("c", 5.0)
        m.decrement("c", 2.0)
        assert m.get_counter("c") == 3.0

    def test_gauge(self):
        m = PluginMetrics()
        m.set_gauge("g", 42.0)
        assert m.get_gauge("g") == 42.0

    def test_timer(self):
        m = PluginMetrics()
        m.record_timer("t", 10.0)
        m.record_timer("t", 20.0)
        stats = m.get_timer_stats("t")
        assert stats["count"] == 2
        assert stats["avg_ms"] == 15.0

    def test_get_all(self):
        m = PluginMetrics()
        m.increment("c")
        m.set_gauge("g", 1.0)
        all_data = m.get_all()
        assert "counters" in all_data

    def test_reset(self):
        m = PluginMetrics()
        m.increment("c")
        m.reset()
        assert m.get_counter("c") == 0.0

    def test_labels(self):
        m = PluginMetrics()
        m.increment("c", labels={"env": "prod"})
        assert m.get_counter("c", labels={"env": "prod"}) == 1.0

    def test_singleton(self):
        m1 = get_plugin_metrics()
        m2 = get_plugin_metrics()
        assert m1 is m2


# ======================================================================
# Tracing
# ======================================================================

class TestPluginTracer:
    def test_start_and_end_span(self):
        tracer = PluginTracer()
        span = tracer.start_span("test")
        assert span.name == "test"
        tracer.end_span(span)
        assert span.duration_ms >= 0

    def test_get_traces(self):
        tracer = PluginTracer()
        span = tracer.start_span("test")
        tracer.end_span(span)
        traces = tracer.get_traces()
        assert len(traces) == 1

    def test_get_traces_by_name(self):
        tracer = PluginTracer()
        s1 = tracer.start_span("a")
        tracer.end_span(s1)
        s2 = tracer.start_span("b")
        tracer.end_span(s2)
        assert len(tracer.get_traces(name="a")) == 1

    def test_statistics(self):
        tracer = PluginTracer()
        stats = tracer.get_statistics()
        assert "total_spans" in stats

    def test_clear(self):
        tracer = PluginTracer()
        span = tracer.start_span("test")
        tracer.end_span(span)
        tracer.clear()
        assert len(tracer.get_traces()) == 0


# ======================================================================
# Events
# ======================================================================

class TestPluginEvents:
    def test_publish(self):
        bus = PluginEventBus()
        event = bus.publish("test.event", "p1")
        assert event.plugin_id == "p1"

    def test_subscribe_and_publish(self):
        bus = PluginEventBus()
        received = []
        bus.subscribe("test.event", lambda e: received.append(e))
        bus.publish("test.event", "p1")
        assert len(received) == 1

    def test_unsubscribe(self):
        bus = PluginEventBus()
        sub_id = bus.subscribe("test.event", lambda e: None)
        assert bus.unsubscribe(sub_id) is True

    def test_get_events(self):
        bus = PluginEventBus()
        bus.publish("a", "p1")
        bus.publish("b", "p2")
        events = bus.get_events()
        assert len(events) == 2

    def test_get_events_by_type(self):
        bus = PluginEventBus()
        bus.publish("a", "p1")
        bus.publish("a", "p2")
        bus.publish("b", "p3")
        events = bus.get_events(event_type="a")
        assert len(events) == 2

    def test_statistics(self):
        bus = PluginEventBus()
        stats = bus.get_statistics()
        assert "total_events" in stats

    def test_clear(self):
        bus = PluginEventBus()
        bus.publish("a", "p1")
        bus.clear()
        assert bus.get_statistics()["total_events"] == 0


# ======================================================================
# Sandbox Manager
# ======================================================================

class TestSandboxManager:
    def test_config(self):
        sm = SandboxManager()
        config = sm.get_sandbox_config("p1")
        assert config.max_memory_mb == 256.0

    def test_custom_config(self):
        sm = SandboxManager()
        custom = SandboxConfig(max_memory_mb=512.0)
        sm.set_sandbox_config("p1", custom)
        assert sm.get_sandbox_config("p1").max_memory_mb == 512.0

    def test_track_execution(self):
        sm = SandboxManager()
        sm.track_execution("p1", 10.0, 50.0)
        usage = sm.get_resource_usage("p1")
        assert usage["total_executions"] == 1

    def test_check_limits(self):
        sm = SandboxManager()
        limits = sm.check_limits("p1")
        assert limits["within_limits"] is True


# ======================================================================
# Manager
# ======================================================================

class TestPluginManager:
    @pytest.mark.asyncio
    async def test_register_plugin(self):
        manager = PluginManager()
        manifest = PluginManifest(plugin_id="p1", name="P1")
        info = await manager.register_plugin(manifest)
        assert info.manifest.plugin_id == "p1"

    @pytest.mark.asyncio
    async def test_start_plugin(self):
        manager = PluginManager()
        manifest = PluginManifest(plugin_id="p1")
        await manager.register_plugin(manifest)
        await manager.start_plugin("p1")
        assert manager.get_plugin("p1").state == PluginState.RUNNING

    @pytest.mark.asyncio
    async def test_stop_plugin(self):
        manager = PluginManager()
        manifest = PluginManifest(plugin_id="p1")
        await manager.register_plugin(manifest)
        await manager.start_plugin("p1")
        await manager.stop_plugin("p1")
        assert manager.get_plugin("p1").state == PluginState.STOPPED

    @pytest.mark.asyncio
    async def test_enable_disable(self):
        manager = PluginManager()
        manifest = PluginManifest(plugin_id="p1")
        await manager.register_plugin(manifest)
        await manager.disable_plugin("p1")
        assert manager.get_plugin("p1").manifest.enabled is False
        await manager.enable_plugin("p1")
        assert manager.get_plugin("p1").manifest.enabled is True

    @pytest.mark.asyncio
    async def test_health_check(self):
        manager = PluginManager()
        manifest = PluginManifest(plugin_id="p1")
        await manager.register_plugin(manifest)
        health = await manager.health_check()
        assert "p1" in health

    def test_list_plugins(self):
        manager = PluginManager()
        assert isinstance(manager.list_plugins(), list)

    def test_statistics(self):
        manager = PluginManager()
        stats = manager.get_statistics()
        assert "total_plugins" in stats


# ======================================================================
# Engine
# ======================================================================

class TestPluginEngine:
    @pytest.mark.asyncio
    async def test_start_and_shutdown(self):
        engine = PluginEngine()
        await engine.start()
        assert engine.is_running is True
        await engine.shutdown()
        assert engine.is_running is False

    @pytest.mark.asyncio
    async def test_register_and_start(self):
        engine = PluginEngine()
        await engine.start()
        manifest = PluginManifest(plugin_id="p1", name="P1")
        result = await engine.register_and_start(manifest)
        assert result["plugin_id"] == "p1"

    @pytest.mark.asyncio
    async def test_health(self):
        engine = PluginEngine()
        await engine.start()
        health = await engine.health()
        assert health["status"] == "ok"

    def test_statistics(self):
        engine = PluginEngine()
        stats = engine.get_statistics()
        assert "total_plugins" in stats

    def test_list_plugins(self):
        engine = PluginEngine()
        assert isinstance(engine.list_plugins(), list)


# ======================================================================
# Factory
# ======================================================================

class TestPluginFactory:
    def test_create_engine(self):
        engine = PluginFactory.create_engine()
        assert engine is not None
        assert isinstance(engine, PluginEngine)

    def test_create_with_components(self):
        components = PluginFactory.create_engine_with_components()
        assert "engine" in components
        assert "manager" in components
        assert "registry" in components
        assert "hook_manager" in components
        assert "sandbox" in components
        assert "metrics" in components
        assert "tracer" in components
        assert "event_bus" in components


# ======================================================================
# Manifest Validator
# ======================================================================

class TestManifestValidator:
    @pytest.mark.asyncio
    async def test_valid_manifest(self):
        mv = ManifestValidator()
        m = PluginManifest(plugin_id="test-plugin", name="Test", version="1.0.0")
        errors = await mv.validate_manifest(m)
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_invalid_id(self):
        mv = ManifestValidator()
        m = PluginManifest(plugin_id="INVALID!", name="Test")
        errors = await mv.validate_manifest(m)
        assert len(errors) > 0

    @pytest.mark.asyncio
    async def test_empty_id(self):
        mv = ManifestValidator()
        m = PluginManifest(plugin_id="", name="Test")
        errors = await mv.validate_manifest(m)
        assert any("plugin_id" in e for e in errors)

    @pytest.mark.asyncio
    async def test_invalid_version(self):
        mv = ManifestValidator()
        m = PluginManifest(plugin_id="test", version="abc")
        errors = await mv.validate_manifest(m)
        assert any("semver" in e for e in errors)

    @pytest.mark.asyncio
    async def test_invalid_permission(self):
        mv = ManifestValidator()
        m = PluginManifest(plugin_id="test", name="Test", permissions=["invalid"])
        errors = await mv.validate_manifest(m)
        assert len(errors) > 0

    def test_parse_manifest(self):
        data = {"plugin_id": "test", "name": "Test", "version": "2.0.0", "type": "core"}
        m = ManifestValidator.parse_manifest(data)
        assert m.plugin_id == "test"
        assert m.plugin_type == PluginType.CORE


# ======================================================================
# Persistence
# ======================================================================

class TestPluginPersistence:
    @pytest.mark.asyncio
    async def test_store_and_get(self):
        repo = InMemoryPluginRepository()
        await repo.store("p1", {"key": "value"})
        data = await repo.get("p1")
        assert data["key"] == "value"

    @pytest.mark.asyncio
    async def test_get_missing(self):
        repo = InMemoryPluginRepository()
        assert await repo.get("missing") is None

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = InMemoryPluginRepository()
        await repo.store("a", {"x": 1})
        await repo.store("b", {"y": 2})
        items = await repo.list_all()
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_delete(self):
        repo = InMemoryPluginRepository()
        await repo.store("p1", {"a": 1})
        assert await repo.delete("p1") is True
        assert await repo.get("p1") is None

    @pytest.mark.asyncio
    async def test_delete_missing(self):
        repo = InMemoryPluginRepository()
        assert await repo.delete("missing") is False

    @pytest.mark.asyncio
    async def test_count(self):
        repo = InMemoryPluginRepository()
        await repo.store("a", {})
        await repo.store("b", {})
        assert await repo.count() == 2

    def test_len(self):
        repo = InMemoryPluginRepository()
        assert len(repo) == 0

    def test_contains(self):
        repo = InMemoryPluginRepository()
        assert "p1" not in repo


# ======================================================================
# API
# ======================================================================

class TestPluginAPI:
    @pytest.mark.asyncio
    async def test_list_plugins(self):
        engine = PluginEngine()
        await engine.start()
        api = PluginAPI(engine)
        plugins = await api.list_plugins()
        assert isinstance(plugins, list)

    @pytest.mark.asyncio
    async def test_health(self):
        engine = PluginEngine()
        await engine.start()
        api = PluginAPI(engine)
        health = await api.health()
        assert health["status"] == "ok"

    @pytest.mark.asyncio
    async def test_statistics(self):
        engine = PluginEngine()
        await engine.start()
        api = PluginAPI(engine)
        stats = await api.statistics()
        assert "total_plugins" in stats


# ======================================================================
# Schemas
# ======================================================================

class TestSchemas:
    def test_plugin_response(self):
        r = PluginResponse(plugin_id="p1", name="P1")
        assert r.plugin_id == "p1"

    def test_plugin_list_response(self):
        r = PluginListResponse(total=5)
        assert r.total == 5

    def test_plugin_health_response(self):
        r = PluginHealthResponse(status="ok")
        assert r.status == "ok"

    def test_plugin_statistics_response(self):
        r = PluginStatisticsResponse(total_plugins=10)
        assert r.total_plugins == 10

    def test_plugin_execution_response(self):
        r = PluginExecutionResponse(success=True, result="ok")
        assert r.success is True

    def test_hook_list_response(self):
        r = HookListResponse(total=3)
        assert r.total == 3

    def test_register_request(self):
        r = RegisterPluginRequest(manifest={"plugin_id": "test"})
        assert r.manifest["plugin_id"] == "test"

    def test_execute_request(self):
        r = ExecutePluginRequest(operation="run", params={"a": 1})
        assert r.operation == "run"

    def test_sandbox_stats_response(self):
        r = SandboxStatsResponse(active_count=5)
        assert r.active_count == 5

    def test_plugin_config_response(self):
        r = PluginConfigResponse(plugin_id="p1", config={"k": "v"})
        assert r.config["k"] == "v"

    def test_plugin_events_response(self):
        r = PluginEventsResponse(total=10)
        assert r.total == 10

    def test_hook_statistics_response(self):
        r = HookStatisticsResponse(total_hooks=5)
        assert r.total_hooks == 5


# ======================================================================
# Exceptions
# ======================================================================

class TestExceptions:
    def test_plugin_error(self):
        e = PluginError("p1", "test")
        assert e.plugin_id == "p1"

    def test_not_found(self):
        e = PluginNotFoundError("p1")
        assert "not found" in str(e)

    def test_load_error(self):
        e = PluginLoadError("p1", "reason")
        assert "reason" in str(e)

    def test_init_error(self):
        e = PluginInitError("p1", "reason")
        assert "reason" in str(e)

    def test_validation_error(self):
        e = PluginValidationError("p1", ["err1", "err2"])
        assert len(e.errors) == 2

    def test_conflict_error(self):
        e = PluginConflictError("p1", "conflict")
        assert "conflict" in str(e)

    def test_timeout_error(self):
        e = PluginTimeoutError("p1", "op")
        assert "op" in str(e)

    def test_sandbox_error(self):
        e = PluginSandboxError("p1", "violation")
        assert "violation" in str(e)

    def test_dependency_error(self):
        e = PluginDependencyError("p1", "missing")
        assert "missing" in str(e)

    def test_version_error(self):
        e = PluginVersionError("p1", "2.0.0", "1.0.0")
        assert "2.0.0" in str(e)

    def test_hook_error(self):
        e = HookError("p1", "hook", "reason")
        assert "hook" in str(e)
