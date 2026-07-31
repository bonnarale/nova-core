"""Plugin manager — orchestrates plugin lifecycle and execution."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.plugins.config import PluginConfigManager
from app.plugins.discovery import PluginDiscoveryService
from app.plugins.enums import HookType, PluginState, PluginType
from app.plugins.events import PluginEventBus
from app.plugins.exceptions import PluginInitError, PluginLoadError, PluginNotFoundError
from app.plugins.hooks import HookManager, HookRegistry
from app.plugins.lifecycle import PluginLifecycle
from app.plugins.loader import PluginLoader
from app.plugins.metrics import PluginMetrics, get_plugin_metrics
from app.plugins.middleware import MiddlewareChain
from app.plugins.models import (
    HookContext,
    HookRegistration,
    PluginInfo,
    PluginManifest,
)
from app.plugins.registry import PluginRegistry
from app.plugins.sandbox import PluginSandbox
from app.plugins.sandbox_manager import SandboxManager
from app.plugins.tracing import PluginTracer

logger = logging.getLogger(__name__)


class PluginManager:
    """Orchestrates plugin lifecycle and execution."""

    def __init__(
        self,
        registry: PluginRegistry | None = None,
        loader: PluginLoader | None = None,
        hook_manager: HookManager | None = None,
        sandbox: PluginSandbox | None = None,
        metrics: PluginMetrics | None = None,
        tracer: PluginTracer | None = None,
        event_bus: PluginEventBus | None = None,
        config_manager: PluginConfigManager | None = None,
        discovery: PluginDiscoveryService | None = None,
        middleware_chain: MiddlewareChain | None = None,
        sandbox_manager: SandboxManager | None = None,
    ) -> None:
        self._registry = registry or PluginRegistry()
        self._loader = loader or PluginLoader(self._registry)
        self._hook_manager = hook_manager or HookManager()
        self._sandbox = sandbox or PluginSandbox()
        self._metrics = metrics or get_plugin_metrics()
        self._tracer = tracer or PluginTracer()
        self._event_bus = event_bus or PluginEventBus()
        self._config_manager = config_manager or PluginConfigManager()
        self._discovery = discovery or PluginDiscoveryService()
        self._middleware = middleware_chain or MiddlewareChain()
        self._sandbox_manager = sandbox_manager or SandboxManager()
        self._execution_count = 0

    @property
    def registry(self) -> PluginRegistry:
        return self._registry

    @property
    def loader(self) -> PluginLoader:
        return self._loader

    @property
    def hooks(self) -> HookManager:
        return self._hook_manager

    @property
    def sandbox(self) -> PluginSandbox:
        return self._sandbox

    @property
    def metrics(self) -> PluginMetrics:
        return self._metrics

    @property
    def tracer(self) -> PluginTracer:
        return self._tracer

    @property
    def event_bus(self) -> PluginEventBus:
        return self._event_bus

    @property
    def config_manager(self) -> PluginConfigManager:
        return self._config_manager

    @property
    def discovery(self) -> PluginDiscoveryService:
        return self._discovery

    @property
    def middleware(self) -> MiddlewareChain:
        return self._middleware

    @property
    def sandbox_manager(self) -> SandboxManager:
        return self._sandbox_manager

    async def register_plugin(
        self,
        manifest: PluginManifest,
        config: dict[str, Any] | None = None,
    ) -> PluginInfo:
        info = await self._loader.load(manifest, config)
        if config:
            self._config_manager.set_config(manifest.plugin_id, config)
        self._event_bus.publish("plugin.registered", manifest.plugin_id)
        self._metrics.increment("plugins.registered")
        logger.info(f"Registered plugin: {manifest.plugin_id}")
        return info

    async def unregister_plugin(self, plugin_id: str) -> None:
        info = self._registry.get(plugin_id)
        lifecycle = self._registry.get_lifecycle(plugin_id)
        if lifecycle is not None and lifecycle.is_running():
            await self.stop_plugin(plugin_id)
        for hook_name in list(self._hook_manager.registry.list_hook_names()):
            self._hook_manager.registry.unregister(hook_name, plugin_id)
        self._registry.unregister(plugin_id)
        self._config_manager.remove_config(plugin_id)
        self._event_bus.publish("plugin.unregistered", plugin_id)
        self._metrics.increment("plugins.unregistered")
        logger.info(f"Unregistered plugin: {plugin_id}")

    async def start_plugin(self, plugin_id: str) -> None:
        info = self._registry.get(plugin_id)
        lifecycle = self._registry.get_lifecycle(plugin_id)
        if lifecycle is None:
            raise PluginInitError(plugin_id, "No lifecycle found")
        start = time.monotonic()
        try:
            if info.instance is not None and hasattr(info.instance, "initialize"):
                await info.instance.initialize()
            lifecycle.transition(PluginState.INITIALIZING)
            lifecycle.transition(PluginState.RUNNING)
            info.state = PluginState.RUNNING
            info.init_time_ms = (time.monotonic() - start) * 1000
            self._event_bus.publish("plugin.started", plugin_id)
            self._metrics.increment("plugins.started")
            self._metrics.record_timer("plugins.init_time_ms", info.init_time_ms)
            logger.info(f"Started plugin: {plugin_id} in {info.init_time_ms:.1f}ms")
        except Exception as exc:
            lifecycle.transition(PluginState.ERROR)
            info.state = PluginState.ERROR
            info.error_message = str(exc)
            self._event_bus.publish("plugin.error", plugin_id, {"error": str(exc)})
            self._metrics.increment("plugins.errors")
            raise PluginInitError(plugin_id, str(exc)) from exc

    async def stop_plugin(self, plugin_id: str) -> None:
        info = self._registry.get(plugin_id)
        lifecycle = self._registry.get_lifecycle(plugin_id)
        if lifecycle is not None and lifecycle.is_running():
            try:
                if info.instance is not None and hasattr(info.instance, "shutdown"):
                    await info.instance.shutdown()
                lifecycle.transition(PluginState.STOPPING)
                lifecycle.transition(PluginState.STOPPED)
                info.state = PluginState.STOPPED
                self._event_bus.publish("plugin.stopped", plugin_id)
                self._metrics.increment("plugins.stopped")
                logger.info(f"Stopped plugin: {plugin_id}")
            except Exception as exc:
                lifecycle.transition(PluginState.ERROR)
                info.state = PluginState.ERROR
                info.error_message = str(exc)
                raise

    async def enable_plugin(self, plugin_id: str) -> None:
        info = self._registry.get(plugin_id)
        info.manifest.enabled = True
        if info.instance is not None and hasattr(info.instance, "on_enable"):
            await info.instance.on_enable()
        self._event_bus.publish("plugin.enabled", plugin_id)

    async def disable_plugin(self, plugin_id: str) -> None:
        info = self._registry.get(plugin_id)
        if info.state == PluginState.RUNNING:
            await self.stop_plugin(plugin_id)
        info.manifest.enabled = False
        if info.instance is not None and hasattr(info.instance, "on_disable"):
            await info.instance.on_disable()
        self._event_bus.publish("plugin.disabled", plugin_id)

    async def execute_plugin(
        self,
        plugin_id: str,
        operation: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        info = self._registry.get(plugin_id)
        if info.state != PluginState.RUNNING:
            raise PluginLoadError(plugin_id, f"Plugin is in state {info.state.value}, expected RUNNING")
        context = {"operation": operation, "params": params or {}, "plugin_id": plugin_id}
        context = await self._middleware.execute_before(plugin_id, context)
        span = self._tracer.start_span(f"plugin.{plugin_id}.{operation}")
        start = time.monotonic()
        try:
            if info.instance is not None and hasattr(info.instance, operation):
                method = getattr(info.instance, operation)
                result = await method(**(params or {}))
            else:
                result = {"status": "no_operation", "operation": operation}
            elapsed = (time.monotonic() - start) * 1000
            self._metrics.record_timer(f"plugin.{plugin_id}.execution_ms", elapsed)
            self._execution_count += 1
            span.set_attribute("result", "success")
            self._tracer.end_span(span)
            result = await self._middleware.execute_after(plugin_id, context, result)
            return result
        except Exception as exc:
            span.set_error(str(exc))
            self._tracer.end_span(span)
            self._metrics.increment(f"plugin.{plugin_id}.errors")
            handled = await self._middleware.execute_on_error(plugin_id, context, exc)
            if not handled:
                raise
            return {"error": str(exc)}

    async def health_check(self) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for info in self._registry.list_all():
            try:
                if info.instance is not None and hasattr(info.instance, "health"):
                    results[info.manifest.plugin_id] = await info.instance.health()
                else:
                    results[info.manifest.plugin_id] = {"status": info.state.value}
            except Exception as exc:
                results[info.manifest.plugin_id] = {"status": "error", "error": str(exc)}
        return results

    def get_plugin(self, plugin_id: str) -> PluginInfo:
        return self._registry.get(plugin_id)

    def list_plugins(self) -> list[PluginInfo]:
        return self._registry.list_all()

    def list_by_type(self, plugin_type: PluginType) -> list[PluginInfo]:
        return self._registry.list_by_type(plugin_type)

    def list_by_capability(self, capability: str) -> list[PluginInfo]:
        return self._registry.list_by_capability(capability)

    def get_statistics(self) -> dict[str, Any]:
        return {
            "total_plugins": self._registry.count(),
            "active_plugins": len(self._registry.list_by_state(PluginState.RUNNING)),
            "failed_plugins": len(self._registry.list_by_state(PluginState.ERROR)),
            "total_hooks": self._hook_manager.registry.count(),
            "total_events": self._event_bus.get_statistics().get("total_events", 0),
            "total_executions": self._execution_count,
            "metrics": self._metrics.get_all(),
            "tracing": self._tracer.get_statistics(),
        }
