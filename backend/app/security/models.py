"""Domain models for the Security subsystem."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from app.security.enums import (
    AccountState,
    AuditAction,
    AuthMethod,
    PermissionLevel,
    SessionState,
    TokenType,
)


@dataclass
class Token:
    token_id: str = ""
    token_type: TokenType = TokenType.ACCESS
    user_id: str = ""
    subject: str = ""
    issued_at: float = 0.0
    expires_at: float = 0.0
    revoked: bool = False
    scopes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at if self.expires_at > 0 else False

    @property
    def is_valid(self) -> bool:
        return not self.revoked and not self.is_expired

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_id": self.token_id,
            "token_type": self.token_type.value,
            "user_id": self.user_id,
            "subject": self.subject,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "revoked": self.revoked,
            "scopes": list(self.scopes),
        }


@dataclass
class User:
    user_id: str = ""
    username: str = ""
    email: str = ""
    password_hash: str = ""
    salt: str = ""
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    state: AccountState = AccountState.ACTIVE
    failed_login_attempts: int = 0
    locked_until: float = 0.0
    mfa_enabled: bool = False
    mfa_secret: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
    last_login_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_locked(self) -> bool:
        return self.state == AccountState.LOCKED and time.time() < self.locked_until

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "roles": list(self.roles),
            "permissions": list(self.permissions),
            "state": self.state.value,
            "mfa_enabled": self.mfa_enabled,
            "created_at": self.created_at,
            "last_login_at": self.last_login_at,
        }


@dataclass
class Role:
    role_id: str = ""
    name: str = ""
    description: str = ""
    permissions: list[str] = field(default_factory=list)
    parent_roles: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "name": self.name,
            "description": self.description,
            "permissions": list(self.permissions),
            "parent_roles": list(self.parent_roles),
        }


@dataclass
class Permission:
    permission_id: str = ""
    resource: str = ""
    action: PermissionLevel = PermissionLevel.READ
    conditions: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "permission_id": self.permission_id,
            "resource": self.resource,
            "action": self.action.value,
            "conditions": dict(self.conditions),
            "description": self.description,
        }


@dataclass
class Session:
    session_id: str = ""
    user_id: str = ""
    token_id: str = ""
    state: SessionState = SessionState.ACTIVE
    created_at: float = 0.0
    expires_at: float = 0.0
    ip_address: str = ""
    user_agent: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at if self.expires_at > 0 else False

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "state": self.state.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }


@dataclass
class AuditEntry:
    entry_id: str = ""
    action: AuditAction = AuditAction.RESOURCE_ACCESS
    user_id: str = ""
    resource: str = ""
    detail: str = ""
    ip_address: str = ""
    user_agent: str = ""
    timestamp: float = 0.0
    success: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "action": self.action.value,
            "user_id": self.user_id,
            "resource": self.resource,
            "detail": self.detail,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp,
            "success": self.success,
        }


@dataclass
class APIKey:
    key_id: str = ""
    key_prefix: str = ""
    key_hash: str = ""
    salt: str = ""
    user_id: str = ""
    name: str = ""
    scopes: list[str] = field(default_factory=list)
    rate_limit: int = 100
    created_at: float = 0.0
    expires_at: float = 0.0
    revoked: bool = False
    last_used_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        if self.revoked:
            return False
        if self.expires_at > 0 and time.time() > self.expires_at:
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "key_id": self.key_id,
            "key_prefix": self.key_prefix,
            "user_id": self.user_id,
            "name": self.name,
            "scopes": list(self.scopes),
            "rate_limit": self.rate_limit,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "revoked": self.revoked,
        }


@dataclass
class RateLimitRule:
    rule_id: str = ""
    resource: str = ""
    max_requests: int = 100
    window_seconds: int = 60
    strategy: str = "fixed_window"
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "resource": self.resource,
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "strategy": self.strategy,
            "enabled": self.enabled,
        }


@dataclass
class SecurityPolicy:
    policy_id: str = ""
    name: str = ""
    description: str = ""
    rules: list[dict[str, Any]] = field(default_factory=list)
    enabled: bool = True
    priority: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "description": self.description,
            "rules": list(self.rules),
            "enabled": self.enabled,
            "priority": self.priority,
        }


@dataclass
class SecurityStatistics:
    total_users: int = 0
    active_sessions: int = 0
    total_api_keys: int = 0
    failed_logins_24h: int = 0
    total_audit_entries: int = 0
    rate_limit_blocks: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_users": self.total_users,
            "active_sessions": self.active_sessions,
            "total_api_keys": self.total_api_keys,
            "failed_logins_24h": self.failed_logins_24h,
            "total_audit_entries": self.total_audit_entries,
            "rate_limit_blocks": self.rate_limit_blocks,
        }
