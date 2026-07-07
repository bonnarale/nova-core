"""NOVA CORE kernel module - the core execution engine.

This module provides:
- KernelEngine: The main orchestrator for AI agent execution
- Session management for tracking execution contexts
- Event system for kernel lifecycle events
- Registry for agents, tools, and providers
- Context management for task execution
- Configuration for kernel settings
"""

import logging

from app.kernel.config import KernelSettings, get_kernel_settings
from app.kernel.context import ExecutionContext, get_current_context, set_current_context
from app.kernel.engine import KernelEngine, get_kernel
from app.kernel.events import EventType, KernelEvent, emit, register_handler
from app.kernel.registry import (
    Agent,
    Tool,
    get_agent,
    get_provider,
    get_tool,
    list_agents,
    list_providers,
    list_tools,
    register_agent,
    register_provider,
    register_tool,
    unregister_agent,
    unregister_provider,
    unregister_tool,
)
from app.kernel.router import route_task
from app.kernel.session import (
    Session,
    create_session,
    end_session,
    get_active_sessions,
    get_session,
)

logger = logging.getLogger(__name__)

__all__ = [
    # Engine
    "KernelEngine",
    "get_kernel",
    # Config
    "KernelSettings",
    "get_kernel_settings",
    # Context
    "ExecutionContext",
    "get_current_context",
    "set_current_context",
    # Events
    "EventType",
    "KernelEvent",
    "emit",
    "register_handler",
    # Registry
    "Agent",
    "Tool",
    "register_agent",
    "get_agent",
    "list_agents",
    "unregister_agent",
    "register_tool",
    "get_tool",
    "list_tools",
    "unregister_tool",
    "register_provider",
    "get_provider",
    "list_providers",
    "unregister_provider",
    # Router
    "route_task",
    # Session
    "Session",
    "create_session",
    "get_session",
    "end_session",
    "get_active_sessions",
]