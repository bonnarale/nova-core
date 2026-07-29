"""Abstract base classes for the Security subsystem."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.security.enums import AuditAction, PermissionLevel, TokenType
from app.security.models import AuditEntry, Token, User


class AuthProvider(ABC):
    """Provider interface for authentication."""

    @abstractmethod
    async def authenticate(self, credentials: dict[str, Any]) -> Token | None:
        ...

    @abstractmethod
    async def verify_token(self, token_value: str) -> Token | None:
        ...

    @abstractmethod
    async def revoke_token(self, token_id: str) -> bool:
        ...


class TokenProvider(ABC):
    """Provider interface for token management."""

    @abstractmethod
    def create_token(
        self,
        user_id: str,
        token_type: TokenType = TokenType.ACCESS,
        scopes: list[str] | None = None,
        expires_in_seconds: int = 3600,
    ) -> Token:
        ...

    @abstractmethod
    def verify_token(self, token_value: str) -> Token | None:
        ...

    @abstractmethod
    def revoke_token(self, token_id: str) -> bool:
        ...

    @abstractmethod
    def get_active_tokens(self, user_id: str) -> list[Token]:
        ...


class CryptoProvider(ABC):
    """Provider interface for cryptographic operations."""

    @abstractmethod
    def hash_password(self, password: str, salt: str | None = None) -> tuple[str, str]:
        ...

    @abstractmethod
    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        ...

    @abstractmethod
    def sign(self, data: str, key: str) -> str:
        ...

    @abstractmethod
    def verify_signature(self, data: str, signature: str, key: str) -> bool:
        ...

    @abstractmethod
    def encrypt(self, plaintext: str, key: str) -> str:
        ...

    @abstractmethod
    def decrypt(self, ciphertext: str, key: str) -> str:
        ...


class PermissionProvider(ABC):
    """Provider interface for permission checking."""

    @abstractmethod
    async def check_permission(
        self,
        user: User,
        resource: str,
        action: PermissionLevel,
    ) -> bool:
        ...

    @abstractmethod
    async def grant_permission(self, user_id: str, permission: str) -> bool:
        ...

    @abstractmethod
    async def revoke_permission(self, user_id: str, permission: str) -> bool:
        ...

    @abstractmethod
    async def list_permissions(self, user_id: str) -> list[str]:
        ...


class AuditProvider(ABC):
    """Provider interface for audit logging."""

    @abstractmethod
    async def log(self, entry: AuditEntry) -> None:
        ...

    @abstractmethod
    async def query(
        self,
        user_id: str | None = None,
        action: AuditAction | None = None,
        resource: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        ...

    @abstractmethod
    async def count(self, user_id: str | None = None) -> int:
        ...


class SessionProvider(ABC):
    """Provider interface for session management."""

    @abstractmethod
    async def create_session(self, user_id: str, metadata: dict[str, Any] | None = None) -> str:
        ...

    @abstractmethod
    async def validate_session(self, session_id: str) -> bool:
        ...

    @abstractmethod
    async def destroy_session(self, session_id: str) -> bool:
        ...

    @abstractmethod
    async def destroy_all_sessions(self, user_id: str) -> int:
        ...
