"""Pydantic response schemas for the Plugin subsystem API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PluginResponse(BaseModel):
    plugin_id: str = ""
    name: str = ""
    version: str = ""
    type: str = ""
    state: str = ""
    enabled: bool = True
    description: str = ""
    author: str = ""
    permissions: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    error_message: str = ""
    load_time_ms: float = 0.0
    init_time_ms: float = 0.0


class PluginListResponse(BaseModel):
    total: int = 0
    plugins: list[PluginResponse] = Field(default_factory=list)


class PluginHealthResponse(BaseModel):
    status: str = "ok"
    uptime_seconds: float = 0.0
    plugins: dict[str, Any] = Field(default_factory=dict)


class PluginStatisticsResponse(BaseModel):
    total_plugins: int = 0
    active_plugins: int = 0
    failed_plugins: int = 0
    total_hooks: int = 0
    total_events: int = 0
    total_executions: int = 0
    running: bool = False
    metrics: dict[str, Any] = Field(default_factory=dict)
    tracing: dict[str, Any] = Field(default_factory=dict)


class PluginExecutionResponse(BaseModel):
    success: bool = True
    plugin_id: str = ""
    operation: str = ""
    result: Any = None
    error: str = ""
    duration_ms: float = 0.0


class HookListResponse(BaseModel):
    total: int = 0
    hooks: list[dict[str, Any]] = Field(default_factory=list)


class HookStatisticsResponse(BaseModel):
    total_hooks: int = 0
    total_executions: int = 0
    hook_names: list[str] = Field(default_factory=list)


class PluginEventsResponse(BaseModel):
    total: int = 0
    events: list[dict[str, Any]] = Field(default_factory=list)


class PluginConfigResponse(BaseModel):
    plugin_id: str = ""
    config: dict[str, Any] = Field(default_factory=dict)


class RegisterPluginRequest(BaseModel):
    manifest: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)


class ExecutePluginRequest(BaseModel):
    operation: str = ""
    params: dict[str, Any] = Field(default_factory=dict)


class SandboxStatsResponse(BaseModel):
    active_count: int = 0
    total_executions: int = 0
    violations_count: int = 0
    config: dict[str, Any] = Field(default_factory=dict)
