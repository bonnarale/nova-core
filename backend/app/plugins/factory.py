"""Plugin factory — creates and wires all plugin components."""

from __future__ import annotations

import logging
from typing import Any

from app.plugins.config import PluginConfigManager
from app.plugins.discovery import PluginDiscoveryService
from app.plugins.engine import PluginEngine
from app.plugins.events import PluginEventBus
from app.plugins.hooks import HookManager, HookRegistry
from app.plugins.loader import PluginLoader
from app.plugins.manager import PluginManager
from app.plugins.metrics import PluginMetrics, get_plugin_metrics
from app.plugins.middleware import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    MiddlewareChain,
    TimingMiddleware,
)
from app.plugins.registry import PluginRegistry
from app.plugins.sandbox import PluginSandbox
from app.plugins.sandbox_manager import SandboxManager
from app.plugins.tracing import PluginTracer

logger = logging.getLogger(__name__)


class PluginFactory:
    """Factory that creates all plugin system components and wires them together."""

    @staticmethod
    def create_engine() -> PluginEngine:
        """Create a fully wired PluginEngine instance."""
        registry = PluginRegistry()
        loader = PluginLoader(registry)
        hook_registry = HookRegistry()
        hook_manager = HookManager(hook_registry)
        sandbox = PluginSandbox()
        metrics = get_plugin_metrics()
        tracer = PluginTracer()
        event_bus = PluginEventBus()
        config_manager = PluginConfigManager()
        discovery = PluginDiscoveryService()
        middleware_chain = MiddlewareChain()
        sandbox_manager = SandboxManager()

        middleware_chain.add(LoggingMiddleware())
        middleware_chain.add(TimingMiddleware())
        middleware_chain.add(ErrorHandlingMiddleware())

        manager = PluginManager(
            registry=registry,
            loader=loader,
            hook_manager=hook_manager,
            sandbox=sandbox,
            metrics=metrics,
            tracer=tracer,
            event_bus=event_bus,
            config_manager=config_manager,
            discovery=discovery,
            middleware_chain=middleware_chain,
            sandbox_manager=sandbox_manager,
        )

        engine = PluginEngine(manager=manager)
        logger.info("PluginFactory created engine")
        return engine

    @staticmethod
    def create_engine_with_components() -> dict[str, Any]:
        """Create engine and return all components."""
        engine = PluginFactory.create_engine()
        return {
            "engine": engine,
            "manager": engine.manager,
            "registry": engine.manager.registry,
            "loader": engine.manager.loader,
            "hook_manager": engine.manager.hooks,
            "sandbox": engine.manager.sandbox,
            "metrics": engine.manager.metrics,
            "tracer": engine.manager.tracer,
            "event_bus": engine.manager.event_bus,
            "config_manager": engine.manager.config_manager,
            "discovery": engine.manager.discovery,
            "middleware": engine.manager.middleware,
            "sandbox_manager": engine.manager.sandbox_manager,
        }
