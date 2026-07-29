from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Configuration:
    base_url: str = "http://localhost:8000"
    api_key: str | None = None
    bearer_token: str | None = None
    timeout: float = 30.0
    max_retries: int = 3
    retry_base_delay: float = 0.5
    retry_max_delay: float = 30.0
    retry_backoff: float = 2.0
    verify_ssl: bool = True
    headers: dict[str, str] = field(default_factory=dict)
    user_agent: str = "nova-core-sdk-python/0.1.0"
    proxy: str | None = None
    telemetry_enabled: bool = False
    hooks: dict[str, list[Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")

    def get_auth_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        elif self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def get_default_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "User-Agent": self.user_agent}
        headers.update(self.get_auth_headers())
        headers.update(self.headers)
        return headers
