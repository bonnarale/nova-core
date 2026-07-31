"""API key management."""

from __future__ import annotations

import threading
import time
from typing import Any

from app.security.crypto import PasswordHasher, TokenGenerator
from app.security.models import APIKey


class APIKeyManager:
    """Manages API keys for programmatic access."""

    def __init__(self) -> None:
        self._keys: dict[str, APIKey] = {}
        self._hasher = PasswordHasher()
        self._lock = threading.Lock()

    def create_key(
        self,
        user_id: str,
        name: str,
        scopes: list[str] | None = None,
        rate_limit: int = 100,
        expires_in_seconds: int | None = None,
    ) -> tuple[APIKey, str]:
        raw_key = TokenGenerator.generate(32)
        key_hash, salt = self._hasher.hash_password(raw_key)
        key_prefix = raw_key[:8]
        now = time.time()
        api_key = APIKey(
            key_id=TokenGenerator.generate_hex(16),
            key_prefix=key_prefix,
            key_hash=key_hash,
            salt=salt,
            user_id=user_id,
            name=name,
            scopes=scopes or [],
            rate_limit=rate_limit,
            created_at=now,
            expires_at=now + expires_in_seconds if expires_in_seconds else 0.0,
        )
        with self._lock:
            self._keys[api_key.key_id] = api_key
        return api_key, raw_key

    def verify_key(self, raw_key: str) -> APIKey | None:
        with self._lock:
            for key in self._keys.values():
                if key.revoked:
                    continue
                if key.is_valid and self._hasher.verify_password(raw_key, key.key_hash, key.salt):
                    key.last_used_at = time.time()
                    return key
        return None

    def revoke_key(self, key_id: str) -> bool:
        with self._lock:
            key = self._keys.get(key_id)
            if key:
                key.revoked = True
                return True
        return False

    def get_key(self, key_id: str) -> APIKey | None:
        return self._keys.get(key_id)

    def get_user_keys(self, user_id: str) -> list[APIKey]:
        return [k for k in self._keys.values() if k.user_id == user_id]

    def list_keys(self) -> list[APIKey]:
        return list(self._keys.values())

    def count(self) -> int:
        with self._lock:
            return len(self._keys)

    def count_active(self) -> int:
        with self._lock:
            return sum(1 for k in self._keys.values() if k.is_valid)
