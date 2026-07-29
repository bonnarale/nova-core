"""Input sanitization utilities."""

from __future__ import annotations

import html
import re
from typing import Any


class InputSanitizer:
    """Sanitizes user input for security."""

    _SQL_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|FETCH|DECLARE|TRUNCATE|COMMENT)\b)",
        r"(--|;|'|\")",
        r"(\b(OR|AND)\b\s+\d+\s*=\s*\d+)",
    ]

    _XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
    ]

    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 10000) -> str:
        value = value[:max_length]
        value = html.escape(value)
        return value.strip()

    @classmethod
    def sanitize_identifier(cls, value: str) -> str:
        value = re.sub(r"[^a-zA-Z0-9_\-]", "", value)
        return value[:255]

    @classmethod
    def strip_html(cls, value: str) -> str:
        return re.sub(r"<[^>]+>", "", value)

    @classmethod
    def detect_sql_injection(cls, value: str) -> bool:
        for pattern in cls._SQL_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    @classmethod
    def detect_xss(cls, value: str) -> bool:
        for pattern in cls._XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    @classmethod
    def sanitize_for_log(cls, value: str) -> str:
        value = value.replace("\n", " ").replace("\r", "")
        value = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", value)
        return value[:1000]

    @classmethod
    def sanitize_url(cls, url: str) -> str:
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        url = re.sub(r"[<>\s]", "", url)
        return url

    @classmethod
    def sanitize_email(cls, email: str) -> str:
        email = email.strip().lower()
        email = re.sub(r"[^a-z0-9@._+\-]", "", email)
        return email

    @classmethod
    def validate_input(cls, value: str, rules: dict[str, Any] | None = None) -> dict[str, Any]:
        errors: list[str] = []
        if rules:
            max_len = rules.get("max_length", 10000)
            if len(value) > max_len:
                errors.append(f"Exceeds max length {max_len}")
            if rules.get("no_html") and re.search(r"<[^>]+>", value):
                errors.append("HTML not allowed")
            if rules.get("no_sql") and cls.detect_sql_injection(value):
                errors.append("Possible SQL injection detected")
            if rules.get("no_xss") and cls.detect_xss(value):
                errors.append("Possible XSS detected")
            if rules.get("required") and not value.strip():
                errors.append("Value is required")
        return {"valid": len(errors) == 0, "errors": errors}
