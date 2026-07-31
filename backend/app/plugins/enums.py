"""Enums for the Plugin subsystem."""

from __future__ import annotations

from enum import Enum


class PluginState(str, Enum):
    REGISTERED = "registered"
    LOADING = "loading"
    LOADED = "loaded"
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    DISABLED = "disabled"


class PluginType(str, Enum):
    CORE = "core"
    EXTENSION = "extension"
    TOOL = "tool"
    AGENT = "agent"
    PROVIDER = "provider"
    MIDDLEWARE = "middleware"
    LISTENER = "listener"
    TRANSFORMER = "transformer"


class PluginPermission(str, Enum):
    NONE = "none"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    EXECUTE = "execute"
    NETWORK = "network"
    STORAGE = "storage"


class HookType(str, Enum):
    BEFORE = "before"
    AFTER = "after"
    AROUND = "around"
    ON_ERROR = "on_error"
    ON_START = "on_start"
    ON_STOP = "on_stop"
    ON_ENABLE = "on_enable"
    ON_DISABLE = "on_disable"


class HookPriority(int, Enum):
    LOWEST = 100
    LOW = 75
    NORMAL = 50
    HIGH = 25
    HIGHEST = 0


class PluginEventType(str, Enum):
    REGISTERED = "registered"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    STARTED = "started"
    STOPPED = "stopped"
    UNREGISTERED = "unregistered"
    ERROR = "error"
    ENABLED = "enabled"
    DISABLED = "disabled"
    HOOK_FIRED = "hook_fired"
