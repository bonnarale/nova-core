"""Enterprise API routes for the Enterprise Features subsystem."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.enterprise.enums import PolicyType

router = APIRouter(tags=["enterprise"])

_engine: Any = None


def set_dependencies(engine: Any = None) -> None:
    global _engine
    _engine = engine


@router.get("/enterprise/status", summary="Enterprise status")
async def enterprise_status() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": _engine.get_status()}
    return {"success": True, "data": {"state": "unknown"}}


@router.get("/enterprise/organizations", summary="List organizations")
async def enterprise_organizations() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": await _engine.list_organizations()}
    return {"success": True, "data": []}


@router.get("/enterprise/tenants", summary="List tenants")
async def enterprise_tenants(org_id: str | None = None) -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": await _engine.list_tenants(org_id=org_id)}
    return {"success": True, "data": []}


@router.get("/enterprise/workspaces", summary="List workspaces")
async def enterprise_workspaces(org_id: str | None = None) -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": await _engine.list_workspaces(org_id=org_id)}
    return {"success": True, "data": []}


@router.get("/enterprise/teams", summary="List teams")
async def enterprise_teams(org_id: str | None = None) -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": await _engine.list_teams(org_id=org_id)}
    return {"success": True, "data": []}


@router.get("/enterprise/roles", summary="List roles")
async def enterprise_roles() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": await _engine.list_roles()}
    return {"success": True, "data": []}


@router.get("/enterprise/permissions", summary="List permissions")
async def enterprise_permissions() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": await _engine.list_permissions()}
    return {"success": True, "data": []}


@router.get("/enterprise/policies", summary="List policies")
async def enterprise_policies() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": await _engine.list_policies()}
    return {"success": True, "data": []}


@router.get("/enterprise/licenses", summary="License info")
async def enterprise_licenses() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": await _engine.get_license()}
    return {"success": True, "data": {}}


@router.get("/enterprise/quotas", summary="Quota info")
async def enterprise_quotas() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": await _engine.get_quotas()}
    return {"success": True, "data": {}}


@router.get("/enterprise/audit", summary="Audit events")
async def enterprise_audit(limit: int = 100) -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": await _engine.get_audit_events(limit=limit)}
    return {"success": True, "data": []}


@router.get("/enterprise/metrics", summary="Enterprise metrics")
async def enterprise_metrics() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": _engine.get_metrics()}
    return {"success": True, "data": {}}


@router.get("/enterprise/traces", summary="Enterprise traces")
async def enterprise_traces(limit: int = 50) -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": _engine.get_traces(limit=limit)}
    return {"success": True, "data": []}


@router.post("/enterprise/organizations", summary="Create organization")
async def enterprise_create_organization(name: str, owner_id: str = "") -> dict[str, Any]:
    if _engine:
        result = await _engine.create_organization(name=name, owner_id=owner_id)
        return {"success": True, "data": result}
    return {"success": False, "data": {"error": "engine not initialized"}}


@router.post("/enterprise/workspaces", summary="Create workspace")
async def enterprise_create_workspace(name: str, org_id: str = "") -> dict[str, Any]:
    if _engine:
        result = await _engine.create_workspace(org_id=org_id, name=name)
        return {"success": True, "data": result}
    return {"success": False, "data": {"error": "engine not initialized"}}


@router.post("/enterprise/teams", summary="Create team")
async def enterprise_create_team(name: str, org_id: str = "") -> dict[str, Any]:
    if _engine:
        result = await _engine.create_team(org_id=org_id, name=name)
        return {"success": True, "data": result}
    return {"success": False, "data": {"error": "engine not initialized"}}


@router.post("/enterprise/roles", summary="Create role")
async def enterprise_create_role(name: str) -> dict[str, Any]:
    if _engine:
        result = await _engine.create_role(name=name)
        return {"success": True, "data": result}
    return {"success": False, "data": {"error": "engine not initialized"}}


@router.post("/enterprise/policies", summary="Create policy")
async def enterprise_create_policy(name: str, policy_type: str = "access") -> dict[str, Any]:
    if _engine:
        result = await _engine.create_policy(name=name, policy_type=policy_type)
        return {"success": True, "data": result}
    return {"success": False, "data": {"error": "engine not initialized"}}
