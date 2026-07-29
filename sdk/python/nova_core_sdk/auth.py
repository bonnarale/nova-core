from __future__ import annotations

from nova_core_sdk.configuration import Configuration


class AuthProvider:
    def __init__(self, config: Configuration) -> None:
        self._config = config

    def get_headers(self) -> dict[str, str]:
        return self._config.get_auth_headers()


class APIKeyAuth(AuthProvider):
    def __init__(self, config: Configuration, api_key: str) -> None:
        super().__init__(config)
        self._api_key = api_key

    def get_headers(self) -> dict[str, str]:
        return {"X-API-Key": self._api_key}


class BearerTokenAuth(AuthProvider):
    def __init__(self, config: Configuration, token: str) -> None:
        super().__init__(config)
        self._token = token

    def get_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}


def create_auth(config: Configuration) -> AuthProvider:
    if config.bearer_token:
        return BearerTokenAuth(config, config.bearer_token)
    if config.api_key:
        return APIKeyAuth(config, config.api_key)
    return AuthProvider(config)
