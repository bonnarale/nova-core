"""Password service — hashing, verification, and strength checking."""

from __future__ import annotations

import re
from typing import Any

from app.security.crypto import PasswordHasher, ScryptHasher


class PasswordService:
    """Manages password hashing, verification, and strength checking."""

    def __init__(self, algorithm: str = "pbkdf2", **kwargs: Any) -> None:
        if algorithm == "scrypt":
            self._hasher: PasswordHasher | ScryptHasher = ScryptHasher(**kwargs)
        else:
            self._hasher = PasswordHasher(**kwargs)

    def hash_password(self, password: str, salt: str | None = None) -> tuple[str, str]:
        return self._hasher.hash_password(password, salt)

    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        return self._hasher.verify_password(password, password_hash, salt)

    def check_strength(self, password: str) -> dict[str, Any]:
        score = 0
        issues: list[str] = []
        if len(password) >= 8:
            score += 1
        else:
            issues.append("Password must be at least 8 characters")
        if len(password) >= 12:
            score += 1
        if re.search(r"[A-Z]", password):
            score += 1
        else:
            issues.append("Password must contain uppercase letters")
        if re.search(r"[a-z]", password):
            score += 1
        else:
            issues.append("Password must contain lowercase letters")
        if re.search(r"\d", password):
            score += 1
        else:
            issues.append("Password must contain digits")
        if re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", password):
            score += 1
        else:
            issues.append("Password must contain special characters")
        if len(password) >= 16:
            score += 1
        strength = "weak"
        if score >= 6:
            strength = "very_strong"
        elif score >= 5:
            strength = "strong"
        elif score >= 4:
            strength = "medium"
        return {"score": score, "max_score": 7, "strength": strength, "issues": issues}

    def generate_password(self, length: int = 16) -> str:
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def needs_rehash(stored_algorithm: str) -> bool:
        return stored_algorithm == "md5" or stored_algorithm == "sha1"
