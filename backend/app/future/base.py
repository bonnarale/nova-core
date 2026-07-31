"""ABCs for the Future Roadmap subsystem."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class FeatureFlagProvider(ABC):
    @abstractmethod
    async def is_enabled(self, flag_name: str, user_id: str | None = None, context: dict[str, Any] | None = None) -> bool: ...

    @abstractmethod
    async def set_flag(self, flag_name: str, enabled: bool, scope: str = "global", **kwargs: Any) -> None: ...

    @abstractmethod
    async def get_flags(self) -> dict[str, bool]: ...

    @abstractmethod
    async def delete_flag(self, flag_name: str) -> bool: ...


class ExperimentProvider(ABC):
    @abstractmethod
    async def create_experiment(self, name: str, experiment_type: str, config: dict[str, Any] | None = None) -> dict[str, Any]: ...

    @abstractmethod
    async def start_experiment(self, experiment_id: str) -> bool: ...

    @abstractmethod
    async def stop_experiment(self, experiment_id: str) -> bool: ...

    @abstractmethod
    async def get_variant(self, experiment_id: str, user_id: str | None = None) -> str | None: ...

    @abstractmethod
    async def get_experiments(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_metrics(self, experiment_id: str) -> dict[str, Any]: ...


class CapabilityProvider(ABC):
    @abstractmethod
    async def register(self, name: str, version: str, metadata: dict[str, Any] | None = None) -> None: ...

    @abstractmethod
    async def get(self, name: str) -> dict[str, Any] | None: ...

    @abstractmethod
    async def list_capabilities(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def is_available(self, name: str) -> bool: ...

    @abstractmethod
    async def update_state(self, name: str, state: str) -> bool: ...


class CompatibilityProvider(ABC):
    @abstractmethod
    async def check_api_compatibility(self, from_version: str, to_version: str) -> dict[str, Any]: ...

    @abstractmethod
    async def check_model_compatibility(self, model_name: str, version: str) -> dict[str, Any]: ...

    @abstractmethod
    async def check_plugin_compatibility(self, plugin_name: str, version: str) -> dict[str, Any]: ...

    @abstractmethod
    async def get_compatibility_report(self) -> dict[str, Any]: ...


class ExtensionProvider(ABC):
    @abstractmethod
    async def register_extension(self, name: str, extension_type: str, provider: Any) -> None: ...

    @abstractmethod
    async def get_extension(self, name: str) -> Any | None: ...

    @abstractmethod
    async def list_extensions(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def remove_extension(self, name: str) -> bool: ...
