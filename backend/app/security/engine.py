"""Security engine — top-level orchestrator for the Security subsystem."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.security.api_keys import APIKeyManager
from app.security.audit import AuditLogger
from app.security.enums import (
    AuditAction,
    AuthMethod,
    PermissionLevel,
    TokenType,
)
from app.security.headers import SecurityConfig, SecurityHeaders
from app.security.ip_filter import IPFilter
from app.security.models import (
    AuditEntry,
    SecurityStatistics,
    Token,
    User,
)
from app.security.password import PasswordService
from app.security.policy import PolicyEngine
from app.security.rbac import RBACEngine
from app.security.rate_limiter import RateLimiter
from app.security.repository import InMemorySecurityRepository
from app.security.sanitize import InputSanitizer
from app.security.sessions import SessionManager
from app.security.token import TokenService
from app.security.token_manager import TokenManager

logger = logging.getLogger(__name__)


class SecurityEngine:
    """Top-level orchestrator for the Security subsystem."""

    def __init__(
        self,
        config: SecurityConfig | None = None,
        repository: InMemorySecurityRepository | None = None,
    ) -> None:
        self._config = config or SecurityConfig()
        self._repository = repository or InMemorySecurityRepository()
        self._token_service = TokenService(
            secret_key=self._config.token_secret or None,
            default_expiry=self._config.token_expiry,
        )
        self._token_manager = TokenManager(self._token_service)
        self._password_service = PasswordService(
            algorithm=self._config.password_hash_algorithm,
        )
        self._rbac = RBACEngine()
        self._session_manager = SessionManager(self._config.session_expiry)
        self._audit = AuditLogger()
        self._api_key_manager = APIKeyManager()
        self._rate_limiter = RateLimiter()
        self._ip_filter = IPFilter()
        self._security_headers = SecurityHeaders(self._config)
        self._policy_engine = PolicyEngine()
        self._running = False
        self._started_at: float = 0.0

    @property
    def config(self) -> SecurityConfig:
        return self._config

    @property
    def tokens(self) -> TokenManager:
        return self._token_manager

    @property
    def passwords(self) -> PasswordService:
        return self._password_service

    @property
    def rbac(self) -> RBACEngine:
        return self._rbac

    @property
    def sessions(self) -> SessionManager:
        return self._session_manager

    @property
    def audit(self) -> AuditLogger:
        return self._audit

    @property
    def api_keys(self) -> APIKeyManager:
        return self._api_key_manager

    @property
    def rate_limiter(self) -> RateLimiter:
        return self._rate_limiter

    @property
    def ip_filter(self) -> IPFilter:
        return self._ip_filter

    @property
    def headers(self) -> SecurityHeaders:
        return self._security_headers

    @property
    def policy_engine(self) -> PolicyEngine:
        return self._policy_engine

    @property
    def repository(self) -> InMemorySecurityRepository:
        return self._repository

    async def start(self) -> None:
        self._started_at = time.time()
        self._running = True
        logger.info("SecurityEngine started")

    async def shutdown(self) -> None:
        self._running = False
        logger.info("SecurityEngine shutdown")

    async def authenticate(
        self,
        username: str,
        password: str,
        ip_address: str = "",
        user_agent: str = "",
    ) -> dict[str, Any]:
        if self._ip_filter.is_blocked(ip_address):
            self._audit.log_event(
                AuditAction.LOGIN_FAILED, user_id=username,
                detail="IP blocked", ip_address=ip_address,
            )
            return {"success": False, "error": "Access denied"}

        user_data = await self._repository.get(f"user:{username}")
        if user_data is None:
            self._audit.log_event(
                AuditAction.LOGIN_FAILED, user_id=username,
                detail="User not found", ip_address=ip_address,
            )
            return {"success": False, "error": "Invalid credentials"}

        password_hash = user_data.get("password_hash", "")
        salt = user_data.get("salt", "")
        if not self._password_service.verify_password(password, password_hash, salt):
            self._audit.log_event(
                AuditAction.LOGIN_FAILED, user_id=username,
                detail="Invalid password", ip_address=ip_address,
            )
            return {"success": False, "error": "Invalid credentials"}

        token, token_value = self._token_manager.create_token(
            user_id=user_data.get("user_id", username),
            token_type=TokenType.ACCESS,
            expires_in_seconds=self._config.token_expiry,
        )
        session = self._session_manager.create_session(
            user_id=user_data.get("user_id", username),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._audit.log_event(
            AuditAction.LOGIN, user_id=user_data.get("user_id", username),
            ip_address=ip_address,
        )
        return {
            "success": True,
            "token": token_value,
            "session_id": session.session_id,
            "user": user_data,
        }

    async def register_user(
        self,
        username: str,
        email: str,
        password: str,
    ) -> dict[str, Any]:
        existing = await self._repository.get(f"user:{username}")
        if existing:
            return {"success": False, "error": "Username already exists"}

        strength = self._password_service.check_strength(password)
        if strength["strength"] in ("weak",):
            return {"success": False, "error": "Password too weak", "strength": strength}

        password_hash, salt = self._password_service.hash_password(password)
        now = time.time()
        user_data = {
            "user_id": username,
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "salt": salt,
            "roles": [],
            "permissions": [],
            "state": "active",
            "created_at": now,
            "updated_at": now,
        }
        await self._repository.store(f"user:{username}", user_data)
        self._audit.log_event(AuditAction.LOGIN, user_id=username, detail="Registered")
        return {"success": True, "user": user_data}

    def verify_token(self, token_value: str) -> Token | None:
        return self._token_manager.verify_token(token_value)

    def get_security_headers(self) -> dict[str, str]:
        return self._security_headers.get_headers()

    def get_statistics(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "active_tokens": self._token_manager.count_active(),
            "active_sessions": self._session_manager.count_active(),
            "total_api_keys": self._api_key_manager.count(),
            "audit_entries": self._audit.count(),
            "rate_limit_blocks": self._rate_limiter.get_block_count(),
            "ip_blocked": len(self._ip_filter.list_blocked()),
            "policies": self._policy_engine.count(),
        }
