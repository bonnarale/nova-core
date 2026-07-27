"""Pydantic schemas for the Database Architecture."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DatabaseHealthResponse(BaseModel):
    connected: bool = False
    latency_ms: float = 0.0
    pool_status: str = "healthy"
    active_connections: int = 0
    idle_connections: int = 0
    pool_size: int = 0
    migration_status: str = "unknown"


class DatabaseStatisticsResponse(BaseModel):
    total_queries: int = 0
    total_transactions: int = 0
    total_rollbacks: int = 0
    total_commits: int = 0
    average_query_latency_ms: float = 0.0
    uptime_seconds: float = 0.0


class MigrationStatusResponse(BaseModel):
    current_revision: str = ""
    head_revision: str = ""
    status: str = "unknown"
    total_migrations: int = 0
    pending: int = 0


class ConnectionPoolResponse(BaseModel):
    pool_size: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    overflow: int = 0
    max_overflow: int = 0
    status: str = "healthy"
    total_checked_out: int = 0
    total_checked_in: int = 0


class SchemaVersionResponse(BaseModel):
    version: str = ""
    dialect: str = "postgresql"
    tables: list[str] = Field(default_factory=list)


class TransactionRequest(BaseModel):
    operations: list[dict[str, Any]] = Field(default_factory=list)


class RepositoryCreateRequest(BaseModel):
    name: str
    domain: str = "general"
    data: dict[str, Any] = Field(default_factory=dict)


class RepositoryResponse(BaseModel):
    name: str = ""
    domain: str = ""
    operation_count: int = 0
