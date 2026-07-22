"""Registry for managing model providers."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.capabilities import ProviderCapabilities, ModelCapabilities
from app.models.lifecycle import ProviderLifecycle, ProviderState
from app.models.providers.base import ModelProvider

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry for managing model providers."""

    def __init__(self) -> None:
        self._providers: dict[str, ModelProvider] = {}
        self._lifecycles: dict[str, ProviderLifecycle] = {}
        self._capabilities: dict[str, ProviderCapabilities] = {}
        self._model_capabilities: dict[str, ModelCapabilities] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    @property
    def provider_count(self) -> int:
        return len(self._providers)

    @property
    def active_count(self) -> int:
        return sum(1 for lc in self._lifecycles.values() if lc.is_available)

    def register(
        self,
        provider_id: str,
        provider: ModelProvider,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        if provider_id in self._providers:
            raise ValueError(f"Provider {provider_id} already registered")
        self._providers[provider_id] = provider
        self._lifecycles[provider_id] = ProviderLifecycle(provider_id)
        self._capabilities[provider_id] = provider.get_capabilities()
        self._metadata[provider_id] = metadata or {}
        logger.info("Provider registered: %s", provider_id)

    def unregister(self, provider_id: str) -> None:
        if provider_id not in self._providers:
            raise KeyError(f"Provider {provider_id} not found")
        del self._providers[provider_id]
        del self._lifecycles[provider_id]
        del self._capabilities[provider_id]
        self._metadata.pop(provider_id, None)
        logger.info("Provider unregistered: %s", provider_id)

    def get(self, provider_id: str) -> Optional[ModelProvider]:
        return self._providers.get(provider_id)

    def get_lifecycle(self, provider_id: str) -> Optional[ProviderLifecycle]:
        return self._lifecycles.get(provider_id)

    def get_capabilities(self, provider_id: str) -> Optional[ProviderCapabilities]:
        return self._capabilities.get(provider_id)

    def get_metadata(self, provider_id: str) -> dict[str, Any]:
        return self._metadata.get(provider_id, {})

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())

    def list_active_providers(self) -> list[str]:
        return [
            pid for pid, lc in self._lifecycles.items()
            if lc.is_available
        ]

    def list_healthy_providers(self) -> list[str]:
        return [
            pid for pid, lc in self._lifecycles.items()
            if lc.is_healthy
        ]

    def find_providers_with_capability(self, capability: str) -> list[str]:
        result = []
        for pid, caps in self._capabilities.items():
            if hasattr(caps, 'supported'):
                cap_names = [c.value if hasattr(c, 'value') else str(c) for c in caps.supported]
                if capability in cap_names:
                    result.append(pid)
        return result

    def find_providers_for_model(self, model: str) -> list[str]:
        result = []
        for pid, model_caps in self._model_capabilities.items():
            if model_caps.model_id == model:
                result.append(pid)
        if not result:
            return list(self._providers.keys())
        return result

    def register_model_capabilities(self, capabilities: ModelCapabilities) -> None:
        key = f"{capabilities.provider}:{capabilities.model_id}"
        self._model_capabilities[key] = capabilities

    def get_model_capabilities(self, provider_id: str, model_id: str) -> Optional[ModelCapabilities]:
        key = f"{provider_id}:{model_id}"
        return self._model_capabilities.get(key)

    async def initialize_all(self) -> dict[str, bool]:
        results = {}
        for provider_id, lifecycle in self._lifecycles.items():
            try:
                lifecycle.initialize()
                provider = self._providers[provider_id]
                await provider.initialize()
                lifecycle.ready()
                results[provider_id] = True
            except Exception as e:
                lifecycle.error(str(e))
                results[provider_id] = False
                logger.error("Failed to initialize provider %s: %s", provider_id, e)
        return results

    async def shutdown_all(self) -> dict[str, bool]:
        results = {}
        for provider_id, lifecycle in self._lifecycles.items():
            try:
                lifecycle.shutting_down()
                provider = self._providers[provider_id]
                await provider.shutdown()
                lifecycle.shutdown()
                results[provider_id] = True
            except Exception as e:
                lifecycle.error(str(e))
                results[provider_id] = False
                logger.error("Failed to shutdown provider %s: %s", provider_id, e)
        return results

    async def health_check_all(self) -> dict[str, dict[str, Any]]:
        results = {}
        for provider_id, lifecycle in self._lifecycles.items():
            if not lifecycle.is_healthy:
                results[provider_id] = {"status": "unhealthy", "provider": provider_id}
                continue
            try:
                lifecycle.health_checking()
                provider = self._providers[provider_id]
                health = await provider.health()
                if health.get("status") == "healthy":
                    lifecycle.ready()
                else:
                    lifecycle.degraded(health.get("error", "Health check returned non-healthy status"))
                results[provider_id] = health
            except Exception as e:
                lifecycle.unhealthy(str(e))
                results[provider_id] = {"status": "unhealthy", "provider": provider_id, "error": str(e)}
        return results

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_count": self.provider_count,
            "active_count": self.active_count,
            "providers": {
                pid: {
                    "state": self._lifecycles[pid].state.value if pid in self._lifecycles else "unknown",
                    "is_healthy": self._lifecycles[pid].is_healthy if pid in self._lifecycles else False,
                    "is_available": self._lifecycles[pid].is_available if pid in self._lifecycles else False,
                }
                for pid in self._providers
            },
        }


def get_provider_registry() -> ProviderRegistry:
    return ProviderRegistry()
