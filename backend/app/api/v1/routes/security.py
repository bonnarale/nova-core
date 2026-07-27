"""Security API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.security.engine import SecurityEngine
from app.security.factory import SecurityFactory
from app.security.headers import SecurityConfig

router = APIRouter(prefix="/security", tags=["security"])

_engine: SecurityEngine | None = None


def _get_engine() -> SecurityEngine:
    global _engine
    if _engine is None:
        _engine = SecurityFactory.create_engine()
    return _engine


@router.on_event("startup")
async def _startup() -> None:
    engine = _get_engine()
    await engine.start()


@router.get("/health")
async def health() -> dict[str, Any]:
    engine = _get_engine()
    return {"status": "ok", "running": engine._running}


@router.get("/headers")
async def security_headers() -> dict[str, str]:
    engine = _get_engine()
    return engine.get_security_headers()


@router.get("/statistics")
async def statistics() -> dict[str, Any]:
    engine = _get_engine()
    return engine.get_statistics()


@router.post("/auth/register")
async def register(body: dict[str, Any]) -> dict[str, Any]:
    engine = _get_engine()
    result = await engine.register_user(
        username=body.get("username", ""),
        email=body.get("email", ""),
        password=body.get("password", ""),
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Registration failed"))
    return result


@router.post("/auth/login")
async def login(body: dict[str, Any]) -> dict[str, Any]:
    engine = _get_engine()
    result = await engine.authenticate(
        username=body.get("username", ""),
        password=body.get("password", ""),
        ip_address=body.get("ip_address", ""),
        user_agent=body.get("user_agent", ""),
    )
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result.get("error", "Authentication failed"))
    return result


@router.post("/auth/token/verify")
async def verify_token(body: dict[str, Any]) -> dict[str, Any]:
    engine = _get_engine()
    token = engine.verify_token(body.get("token", ""))
    if token is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"valid": True, "token": token.to_dict()}


@router.post("/auth/token/revoke")
async def revoke_token(body: dict[str, Any]) -> dict[str, str]:
    engine = _get_engine()
    token_id = body.get("token_id", "")
    success = engine.tokens.revoke_token(token_id)
    if not success:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"status": "revoked"}


@router.post("/api-keys")
async def create_api_key(body: dict[str, Any]) -> dict[str, Any]:
    engine = _get_engine()
    api_key, raw_key = engine.api_keys.create_key(
        user_id=body.get("user_id", ""),
        name=body.get("name", ""),
        scopes=body.get("scopes", []),
    )
    return {"key": api_key.to_dict(), "raw_key": raw_key}


@router.get("/api-keys/{user_id}")
async def list_api_keys(user_id: str) -> dict[str, Any]:
    engine = _get_engine()
    keys = engine.api_keys.get_user_keys(user_id)
    return {"keys": [k.to_dict() for k in keys]}


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: str) -> dict[str, str]:
    engine = _get_engine()
    success = engine.api_keys.revoke_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"status": "revoked"}


@router.get("/audit")
async def audit_log(
    user_id: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    engine = _get_engine()
    entries = engine.audit.query(user_id=user_id, limit=limit)
    return {"entries": [e.to_dict() for e in entries], "total": engine.audit.count(user_id)}


@router.get("/rbac/roles")
async def list_roles() -> dict[str, Any]:
    engine = _get_engine()
    roles = engine.rbac.list_roles()
    return {"roles": [r.to_dict() for r in roles]}


@router.post("/rbac/check")
async def check_permission(body: dict[str, Any]) -> dict[str, Any]:
    engine = _get_engine()
    user_id = body.get("user_id", "")
    resource = body.get("resource", "")
    action_str = body.get("action", "read")
    try:
        from app.security.enums import PermissionLevel
        action = PermissionLevel(action_str)
    except ValueError:
        action = PermissionLevel.READ
    allowed = engine.rbac.check_resource_access(user_id, resource, action)
    return {"allowed": allowed, "user_id": user_id, "resource": resource, "action": action.value}
