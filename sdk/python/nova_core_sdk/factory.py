from __future__ import annotations

from nova_core_sdk.async_client import AsyncNovaClient
from nova_core_sdk.client import NovaClient
from nova_core_sdk.configuration import Configuration


def create_client(
    base_url: str = "http://localhost:8000",
    api_key: str | None = None,
    bearer_token: str | None = None,
    timeout: float = 30.0,
    max_retries: int = 3,
    **kwargs: object,
) -> AsyncNovaClient:
    config = Configuration(
        base_url=base_url,
        api_key=api_key,
        bearer_token=bearer_token,
        timeout=timeout,
        max_retries=max_retries,
        **kwargs,  # type: ignore[arg-type]
    )
    return AsyncNovaClient(config)


def create_async_client(
    base_url: str = "http://localhost:8000",
    api_key: str | None = None,
    bearer_token: str | None = None,
    timeout: float = 30.0,
    max_retries: int = 3,
    **kwargs: object,
) -> AsyncNovaClient:
    return create_client(
        base_url=base_url,
        api_key=api_key,
        bearer_token=bearer_token,
        timeout=timeout,
        max_retries=max_retries,
        **kwargs,
    )
