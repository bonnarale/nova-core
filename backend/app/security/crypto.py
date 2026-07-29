"""Cryptographic utilities — password hashing, HMAC, signing, encryption.

All operations use Python stdlib only (hashlib, hmac, secrets, base64).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
import time
from typing import Any


class PasswordHasher:
    """PBKDF2-based password hashing."""

    def __init__(self, algorithm: str = "pbkdf2_sha256", iterations: int = 260000) -> None:
        self._algorithm = algorithm
        self._iterations = iterations

    def hash_password(self, password: str, salt: str | None = None) -> tuple[str, str]:
        if salt is None:
            salt = secrets.token_hex(32)
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            self._iterations,
        )
        return dk.hex(), salt

    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            self._iterations,
        )
        return hmac.compare_digest(dk.hex(), password_hash)

    @staticmethod
    def generate_salt() -> str:
        return secrets.token_hex(32)


class ScryptHasher:
    """Scrypt-based password hashing."""

    def __init__(self, n: int = 16384, r: int = 8, p: int = 1) -> None:
        self._n = n
        self._r = r
        self._p = p

    def hash_password(self, password: str, salt: str | None = None) -> tuple[str, str]:
        if salt is None:
            salt = secrets.token_hex(32)
        dk = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt),
            n=self._n,
            r=self._r,
            p=self._p,
            dklen=64,
        )
        return dk.hex(), salt

    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        dk = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt),
            n=self._n,
            r=self._r,
            p=self._p,
            dklen=64,
        )
        return hmac.compare_digest(dk.hex(), password_hash)


class HMACSigner:
    """HMAC-based message signing."""

    def __init__(self, default_key: str | None = None) -> None:
        self._default_key = default_key or secrets.token_hex(32)

    def sign(self, data: str, key: str | None = None) -> str:
        effective_key = key or self._default_key
        sig = hmac.new(
            effective_key.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return sig

    def verify(self, data: str, signature: str, key: str | None = None) -> bool:
        effective_key = key or self._default_key
        expected = hmac.new(
            effective_key.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def sign_json(self, obj: dict[str, Any], key: str | None = None) -> str:
        data = json.dumps(obj, sort_keys=True, separators=(",", ":"))
        return self.sign(data, key)

    def verify_json(self, obj: dict[str, Any], signature: str, key: str | None = None) -> bool:
        data = json.dumps(obj, sort_keys=True, separators=(",", ":"))
        return self.verify(data, signature, key)


class SimpleCipher:
    """Simple XOR-based cipher for basic encryption/decryption.

    For production use, this should be replaced with AES from a crypto library.
    This implementation provides basic obfuscation using Python stdlib only.
    """

    @staticmethod
    def encrypt(plaintext: str, key: str) -> str:
        key_bytes = hashlib.sha256(key.encode("utf-8")).digest()
        plain_bytes = plaintext.encode("utf-8")
        encrypted = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(plain_bytes))
        return base64.b64encode(encrypted).decode("ascii")

    @staticmethod
    def decrypt(ciphertext: str, key: str) -> str:
        key_bytes = hashlib.sha256(key.encode("utf-8")).digest()
        cipher_bytes = base64.b64decode(ciphertext)
        decrypted = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(cipher_bytes))
        return decrypted.decode("utf-8")


class TokenGenerator:
    """Generates cryptographically secure random tokens."""

    @staticmethod
    def generate(length: int = 32) -> str:
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_hex(length: int = 32) -> str:
        return secrets.token_hex(length)

    @staticmethod
    def generate_numeric(length: int = 6) -> str:
        return "".join(secrets.choice("0123456789") for _ in range(length))

    @staticmethod
    def generate_alphanumeric(length: int = 32) -> str:
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return "".join(secrets.choice(alphabet) for _ in range(length))
