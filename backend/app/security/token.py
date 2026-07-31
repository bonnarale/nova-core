"""Token service — HMAC-based JWT-like token creation and verification."""

from __future__ import annotations

import base64
import json
import time
from typing import Any

from app.security.crypto import HMACSigner, TokenGenerator
from app.security.enums import TokenType
from app.security.models import Token


class TokenService:
    """Creates and verifies HMAC-signed tokens."""

    def __init__(self, secret_key: str | None = None, default_expiry: int = 3600) -> None:
        self._secret = secret_key or TokenGenerator.generate_hex(32)
        self._signer = HMACSigner(self._secret)
        self._default_expiry = default_expiry

    @property
    def secret_key(self) -> str:
        return self._secret

    def create_token(
        self,
        user_id: str,
        token_type: TokenType = TokenType.ACCESS,
        scopes: list[str] | None = None,
        expires_in_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[Token, str]:
        expiry = expires_in_seconds or self._default_expiry
        now = time.time()
        payload = {
            "sub": user_id,
            "type": token_type.value,
            "iat": now,
            "exp": now + expiry,
            "jti": TokenGenerator.generate_hex(16),
            "scopes": scopes or [],
        }
        if metadata:
            payload["meta"] = metadata

        header = {"alg": "HS256", "typ": "NOVA"}
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip("=")
        signing_input = f"{header_b64}.{payload_b64}"
        signature = self._signer.sign(signing_input)
        token_value = f"{signing_input}.{signature}"

        token = Token(
            token_id=payload["jti"],
            token_type=token_type,
            user_id=user_id,
            subject=user_id,
            issued_at=now,
            expires_at=now + expiry,
            scopes=scopes or [],
            metadata=metadata or {},
        )
        return token, token_value

    def verify_token(self, token_value: str) -> Token | None:
        parts = token_value.split(".")
        if len(parts) != 3:
            return None
        signing_input = f"{parts[0]}.{parts[1]}"
        if not self._signer.verify(signing_input, parts[2]):
            return None
        try:
            payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        except Exception:
            return None
        now = time.time()
        if payload.get("exp", 0) < now:
            return None
        token_type_str = payload.get("type", "access")
        try:
            token_type = TokenType(token_type_str)
        except ValueError:
            token_type = TokenType.ACCESS
        return Token(
            token_id=payload.get("jti", ""),
            token_type=token_type,
            user_id=payload.get("sub", ""),
            subject=payload.get("sub", ""),
            issued_at=payload.get("iat", 0),
            expires_at=payload.get("exp", 0),
            scopes=payload.get("scopes", []),
            metadata=payload.get("meta", {}),
        )

    def decode_payload(self, token_value: str) -> dict[str, Any] | None:
        parts = token_value.split(".")
        if len(parts) != 3:
            return None
        try:
            payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
            return json.loads(base64.urlsafe_b64decode(payload_b64))
        except Exception:
            return None
