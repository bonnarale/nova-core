"""Enums for the Database Architecture subsystem."""

from __future__ import annotations

from enum import Enum


class LifecycleState(str, Enum):
    REGISTERED = "registered"
    INITIALIZED = "initialized"
    READY = "ready"
    RUNNING = "running"
    DEGRADED = "degraded"
    FAILED = "failed"
    SHUTDOWN = "shutdown"


class TransactionState(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class SessionScope(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    GLOBAL = "global"


class MigrationStatus(str, Enum):
    CURRENT = "current"
    OUTDATED = "outdated"
    PENDING = "pending"
    FAILED = "failed"
    UNKNOWN = "unknown"


class QueryOperation(str, Enum):
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    COUNT = "count"
    JOIN = "join"


class PoolStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    EXHAUSTED = "exhausted"
    CLOSED = "closed"


class DatabaseDialect(str, Enum):
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    MYSQL = "mysql"
