"""Security configuration and headers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SecurityConfig:
    """Global security configuration."""

    token_secret: str = ""
    token_expiry: int = 3600
    refresh_token_expiry: int = 86400 * 30
    password_min_length: int = 8
    password_hash_algorithm: str = "pbkdf2"
    password_hash_iterations: int = 260000
    max_failed_logins: int = 5
    lockout_duration: int = 900
    session_expiry: int = 3600
    max_sessions_per_user: int = 10
    rate_limit_enabled: bool = True
    rate_limit_default: int = 100
    rate_limit_window: int = 60
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    cors_methods: list[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])
    cors_headers: list[str] = field(default_factory=list)
    csp_enabled: bool = True
    hsts_enabled: bool = True
    hsts_max_age: int = 31536000
    xss_protection: bool = True
    content_type_nosniff: bool = True
    frame_deny: bool = True
    referrer_policy: str = "strict-origin-when-cross-origin"

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_expiry": self.token_expiry,
            "refresh_token_expiry": self.refresh_token_expiry,
            "password_min_length": self.password_min_length,
            "password_hash_algorithm": self.password_hash_algorithm,
            "max_failed_logins": self.max_failed_logins,
            "lockout_duration": self.lockout_duration,
            "session_expiry": self.session_expiry,
            "rate_limit_enabled": self.rate_limit_enabled,
            "cors_origins": list(self.cors_origins),
            "csp_enabled": self.csp_enabled,
            "hsts_enabled": self.hsts_enabled,
            "xss_protection": self.xss_protection,
            "content_type_nosniff": self.content_type_nosniff,
            "frame_deny": self.frame_deny,
        }


class SecurityHeaders:
    """Generates security headers for HTTP responses."""

    def __init__(self, config: SecurityConfig | None = None) -> None:
        self._config = config or SecurityConfig()

    def get_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._config.hsts_enabled:
            headers["Strict-Transport-Security"] = f"max-age={self._config.hsts_max_age}; includeSubDomains"
        if self._config.xss_protection:
            headers["X-XSS-Protection"] = "1; mode=block"
        if self._config.content_type_nosniff:
            headers["X-Content-Type-Options"] = "nosniff"
        if self._config.frame_deny:
            headers["X-Frame-Options"] = "DENY"
        headers["Referrer-Policy"] = self._config.referrer_policy
        if self._config.csp_enabled:
            headers["Content-Security-Policy"] = "default-src 'self'"
        headers["X-Permitted-Cross-Domain-Policies"] = "none"
        return headers

    def get_cors_headers(self, origin: str = "*") -> dict[str, str]:
        allowed = origin in self._config.cors_origins or "*" in self._config.cors_origins
        headers: dict[str, str] = {}
        if allowed:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Methods"] = ", ".join(self._config.cors_methods)
            if self._config.cors_headers:
                headers["Access-Control-Allow-Headers"] = ", ".join(self._config.cors_headers)
            headers["Access-Control-Max-Age"] = "3600"
        return headers
