from __future__ import annotations

import sys
from typing import Any

from cli.config import CLIConfig


def resolve_auth(config: CLIConfig) -> dict[str, str]:
    headers: dict[str, str] = {}
    if config.bearer_token:
        headers["Authorization"] = f"Bearer {config.bearer_token}"
    elif config.api_key:
        headers["X-API-Key"] = config.api_key
    return headers
