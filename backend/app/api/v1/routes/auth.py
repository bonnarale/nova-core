"""Auth API routes — clean endpoints for frontend authentication."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.security.engine import SecurityEngine

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


def _get_engine(request: Request) -> SecurityEngine:
    return request.app.state.security_engine


@router.post("/register")
async def register(body: RegisterRequest, request: Request) -> dict[str, Any]:
    engine = _get_engine(request)
    result = await engine.register_user(
        username=body.email,
        email=body.email,
        password=body.password,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Registration failed"))
    
    # Auto-login after registration
    login_result = await engine.authenticate(
        username=body.email,
        password=body.password,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    if not login_result["success"]:
        raise HTTPException(status_code=400, detail="Registration succeeded but login failed")
    
    return {
        "token": login_result["token"],
        "user": {
            "user_id": login_result["user"]["user_id"],
            "username": login_result["user"]["username"],
            "email": login_result["user"]["email"],
        },
    }


@router.post("/login")
async def login(body: LoginRequest, request: Request) -> dict[str, Any]:
    engine = _get_engine(request)
    result = await engine.authenticate(
        username=body.email,
        password=body.password,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result.get("error", "Authentication failed"))
    
    return {
        "token": result["token"],
        "user": {
            "user_id": result["user"]["user_id"],
            "username": result["user"]["username"],
            "email": result["user"]["email"],
        },
    }


@router.get("/me")
async def me(request: Request) -> dict[str, Any]:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    token_value = auth_header[7:]
    engine = _get_engine(request)
    token = engine.verify_token(token_value)
    if token is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Get user from repository
    user_data = await engine.repository.get(f"user:{token.user_id}")
    if user_data is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user_id": user_data["user_id"],
        "username": user_data["username"],
        "email": user_data["email"],
    }
