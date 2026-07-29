"""Abstract base classes for the Deployment subsystem."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DeploymentProvider(ABC):
    """Provider interface for deployment operations."""

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def shutdown(self) -> None: ...

    @abstractmethod
    async def health(self) -> dict[str, Any]: ...

    @abstractmethod
    async def readiness(self) -> bool: ...

    @abstractmethod
    async def liveness(self) -> bool: ...

    @abstractmethod
    def is_running(self) -> bool: ...


class EnvironmentProvider(ABC):
    """Provider interface for environment variable management."""

    @abstractmethod
    async def get(self, key: str, default: str = "") -> str: ...

    @abstractmethod
    async def get_all(self) -> dict[str, str]: ...

    @abstractmethod
    async def set(self, key: str, value: str) -> None: ...

    @abstractmethod
    async def validate(self, required: list[str]) -> dict[str, Any]: ...

    @abstractmethod
    async def get_filtered(self, prefix: str) -> dict[str, str]: ...


class ConfigurationProvider(ABC):
    """Provider interface for configuration management."""

    @abstractmethod
    async def get(self, key: str, default: Any = None) -> Any: ...

    @abstractmethod
    async def get_all(self) -> dict[str, Any]: ...

    @abstractmethod
    async def set(self, key: str, value: Any) -> None: ...

    @abstractmethod
    async def get_section(self, section: str) -> dict[str, Any]: ...

    @abstractmethod
    async def validate(self) -> dict[str, Any]: ...


class HealthProvider(ABC):
    """Provider interface for health checks."""

    @abstractmethod
    async def check_startup(self) -> dict[str, Any]: ...

    @abstractmethod
    async def check_readiness(self) -> dict[str, Any]: ...

    @abstractmethod
    async def check_liveness(self) -> dict[str, Any]: ...

    @abstractmethod
    async def check_all(self) -> dict[str, Any]: ...


class SecretProvider(ABC):
    """Provider interface for secret management."""

    @abstractmethod
    async def get_secret(self, key: str) -> str | None: ...

    @abstractmethod
    async def set_secret(self, key: str, value: str) -> None: ...

    @abstractmethod
    async def list_secrets(self) -> list[str]: ...

    @abstractmethod
    async def delete_secret(self, key: str) -> bool: ...

    @abstractmethod
    async def validate(self, required: list[str]) -> dict[str, Any]: ...
