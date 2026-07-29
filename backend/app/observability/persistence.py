"""Observability persistence — in-memory persistence for observability state."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class InMemoryObservabilityPersistence:
    """In-memory persistence for observability state: counters, gauges, config."""

    def __init__(self) -> None:
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._config: dict[str, Any] = {}
        self._state: dict[str, Any] = {}

    async def store_counter(self, name: str, value: float) -> None:
        self._counters[name] = self._counters.get(name, 0.0) + value

    async def get_counter(self, name: str) -> float:
        return self._counters.get(name, 0.0)

    async def set_gauge(self, name: str, value: float) -> None:
        self._gauges[name] = value

    async def get_gauge(self, name: str) -> float:
        return self._gauges.get(name, 0.0)

    async def store_config(self, key: str, value: Any) -> None:
        self._config[key] = value

    async def get_config(self, key: str) -> Any:
        return self._config.get(key)

    async def delete_config(self, key: str) -> bool:
        return self._config.pop(key, None) is not None

    async def store_state(self, key: str, value: Any) -> None:
        self._state[key] = value

    async def get_state(self, key: str) -> Any:
        return self._state.get(key)

    async def list_counters(self) -> dict[str, float]:
        return dict(self._counters)

    async def list_gauges(self) -> dict[str, float]:
        return dict(self._gauges)

    async def clear(self) -> int:
        count = len(self._counters) + len(self._gauges) + len(self._config) + len(self._state)
        self._counters.clear()
        self._gauges.clear()
        self._config.clear()
        self._state.clear()
        return count
