"""Enums for the Security subsystem."""

from __future__ import annotations

from enum import Enum


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    RESET_PASSWORD = "reset_password"
    EMAIL_VERIFY = "email_verify"
    MFA = "mfa"


class PermissionLevel(str, Enum):
    NONE = "none"
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class AuthMethod(str, Enum):
    PASSWORD = "password"
    TOKEN = "token"
    API_KEY = "api_key"
    OAUTH = "oauth"
    MFA = "mfa"
    MAGIC_LINK = "magic_link"


class AuditAction(str, Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_REVOKE = "token_revoke"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    PERMISSION_GRANT = "permission_grant"
    PERMISSION_REVOKE = "permission_revoke"
    ROLE_ASSIGN = "role_assign"
    ROLE_UNASSIGN = "role_unassign"
    API_KEY_CREATE = "api_key_create"
    API_KEY_REVOKE = "api_key_revoke"
    RESOURCE_ACCESS = "resource_access"
    RESOURCE_MODIFY = "resource_modify"
    RESOURCE_DELETE = "resource_delete"
    SETTINGS_CHANGE = "settings_change"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class SessionState(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class AccountState(str, Enum):
    ACTIVE = "active"
    LOCKED = "locked"
    DISABLED = "disabled"
    PENDING = "pending"


class RateLimitStrategy(str, Enum):
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


class IPFilterAction(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    CHALLENGE = "challenge"


class PasswordHashAlgorithm(str, Enum):
    PBKDF2 = "pbkdf2"
    SCRYPT = "scrypt"


class CipherMode(str, Enum):
    CBC = "cbc"
    CTR = "ctr"
