"""Token manager — manages token lifecycle (creation, storage, revocation)."""

from __future__ import annotations

import threading
import time
from typing import Any

from app.security.enums import TokenType
from app.security.models import Token
from app.security.token import TokenService


class TokenManager:
    """Manages token lifecycle and storage."""

    def __init__(self, token_service: TokenService | None = None) -> None:
        self._service = token_service or TokenService()
        self._tokens: dict[str, Token] = {}
        self._user_tokens: dict[str, set[str]] = {}
        self._lock = threading.Lock()

    @property
    def service(self) -> TokenService:
        return self._service

    def create_token(
        self,
        user_id: str,
        token_type: TokenType = TokenType.ACCESS,
        scopes: list[str] | None = None,
        expires_in_seconds: int = 3600,
    ) -> tuple[Token, str]:
        token, value = self._service.create_token(
            user_id, token_type, scopes, expires_in_seconds,
        )
        with self._lock:
            self._tokens[token.token_id] = token
            if user_id not in self._user_tokens:
                self._user_tokens[user_id] = set()
            self._user_tokens[user_id].add(token.token_id)
        return token, value

    def verify_token(self, token_value: str) -> Token | None:
        token = self._service.verify_token(token_value)
        if token is None:
            return None
        with self._lock:
            stored = self._tokens.get(token.token_id)
            if stored is not None and stored.revoked:
                return None
        return token

    def revoke_token(self, token_id: str) -> bool:
        with self._lock:
            token = self._tokens.get(token_id)
            if token is None:
                return False
            token.revoked = True
            return True

    def revoke_user_tokens(self, user_id: str) -> int:
        count = 0
        with self._lock:
            token_ids = self._user_tokens.get(user_id, set())
            for tid in token_ids:
                token = self._tokens.get(tid)
                if token and not token.revoked:
                    token.revoked = True
                    count += 1
        return count

    def get_user_tokens(self, user_id: str) -> list[Token]:
        with self._lock:
            token_ids = self._user_tokens.get(user_id, set())
            return [self._tokens[tid] for tid in token_ids if tid in self._tokens]

    def get_active_tokens(self, user_id: str) -> list[Token]:
        tokens = self.get_user_tokens(user_id)
        return [t for t in tokens if t.is_valid]

    def cleanup_expired(self) -> int:
        count = 0
        now = time.time()
        with self._lock:
            to_remove = []
            for tid, token in self._tokens.items():
                if token.is_expired:
                    to_remove.append(tid)
            for tid in to_remove:
                del self._tokens[tid]
                count += 1
        return count

    def count(self) -> int:
        with self._lock:
            return len(self._tokens)

    def count_active(self) -> int:
        with self._lock:
            return sum(1 for t in self._tokens.values() if t.is_valid)
