from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CLIConfig:
    base_url: str = "http://localhost:8000"
    api_key: str | None = None
    bearer_token: str | None = None
    timeout: float = 30.0
    verify_ssl: bool = True
    output_json: bool = False


def get_config_path() -> Path:
    return Path.home() / ".config" / "nova" / "config.json"


def load_config() -> CLIConfig:
    config = CLIConfig()
    env_url = os.environ.get("NOVA_BASE_URL")
    if env_url:
        config.base_url = env_url
    env_key = os.environ.get("NOVA_API_KEY")
    if env_key:
        config.api_key = env_key
    env_token = os.environ.get("NOVA_BEARER_TOKEN")
    if env_token:
        config.bearer_token = env_token

    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path) as f:
                data = json.load(f)
            config.base_url = data.get("base_url", config.base_url)
            config.api_key = data.get("api_key", config.api_key)
            config.bearer_token = data.get("bearer_token", config.bearer_token)
            config.timeout = data.get("timeout", config.timeout)
            config.verify_ssl = data.get("verify_ssl", config.verify_ssl)
        except (json.JSONDecodeError, OSError):
            pass
    return config


def save_config(config: CLIConfig) -> None:
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "base_url": config.base_url,
        "api_key": config.api_key,
        "bearer_token": config.bearer_token,
        "timeout": config.timeout,
        "verify_ssl": config.verify_ssl,
    }
    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)
