"""Database API routes for the Database Architecture."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["database"])

_db_architecture: Any = None
_db_health_checker: Any = None
_db_migration_provider: Any = None
_db_metrics: Any = None
_db_tracer: Any = None
_db_pool: Any = None
_db_registry: Any = None


def set_dependencies(
    architecture: Any = None,
    health_checker: Any = None,
    migration_provider: Any = None,
    metrics: Any = None,
    tracer: Any = None,
    pool: Any = None,
    registry: Any = None,
) -> None:
    global _db_architecture, _db_health_checker, _db_migration_provider
    global _db_metrics, _db_tracer, _db_pool, _db_registry
    _db_architecture = architecture
    _db_health_checker = health_checker
    _db_migration_provider = migration_provider
    _db_metrics = metrics
    _db_tracer = tracer
    _db_pool = pool
    _db_registry = registry


@router.get("/database/health", summary="Database health check")
async def database_health() -> dict[str, Any]:
    if _db_health_checker:
        return {"success": True, "data": await _db_health_checker.get_health()}
    return {"success": True, "data": {"connected": False, "status": "no health checker"}}


@router.get("/database/statistics", summary="Database statistics")
async def database_statistics() -> dict[str, Any]:
    stats: dict[str, Any] = {}
    if _db_metrics:
        stats = _db_metrics.get_statistics()
    if _db_pool:
        stats["pool"] = _db_pool.to_dict()
    if _db_registry:
        stats["repositories"] = _db_registry.get_statistics()
    return {"success": True, "data": stats}


@router.get("/database/migrations", summary="Migration status")
async def database_migrations() -> dict[str, Any]:
    if _db_migration_provider:
        status = await _db_migration_provider.get_migration_status()
        return {"success": True, "data": status}
    return {"success": True, "data": {"status": "no migration provider"}}


@router.get("/database/schema", summary="Schema information")
async def database_schema() -> dict[str, Any]:
    tables: list[str] = []
    if _db_registry:
        tables = _db_registry.list_all()
    return {
        "success": True,
        "data": {
            "dialect": "postgresql",
            "tables": tables,
            "version": "26.0.0",
        },
    }


@router.get("/database/metrics", summary="Database metrics")
async def database_metrics() -> dict[str, Any]:
    if _db_metrics:
        return {"success": True, "data": _db_metrics.get_statistics()}
    return {"success": True, "data": {}}


@router.get("/database/traces", summary="Recent database traces")
async def database_traces(limit: int = 100) -> dict[str, Any]:
    if _db_tracer:
        return {
            "success": True,
            "data": {
                "traces": _db_tracer.get_recent_traces(limit),
                "statistics": _db_tracer.get_statistics(),
            },
        }
    return {"success": True, "data": {"traces": [], "statistics": {}}}
