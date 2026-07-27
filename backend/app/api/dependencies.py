"""Dependency injection helpers for the API Platform."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request

logger = logging.getLogger(__name__)


class DependencyContainer:
    """Simple dependency container for the API platform."""

    def __init__(self) -> None:
        self._singletons: dict[str, Any] = {}
        self._factories: dict[str, Any] = {}

    def register_singleton(self, name: str, instance: Any) -> None:
        self._singletons[name] = instance

    def register_factory(self, name: str, factory: Any) -> None:
        self._factories[name] = factory

    def resolve(self, name: str) -> Any:
        if name in self._singletons:
            return self._singletons[name]
        if name in self._factories:
            return self._factories[name]()
        raise KeyError(f"Dependency not registered: {name}")

    def has(self, name: str) -> bool:
        return name in self._singletons or name in self._factories

    def list_dependencies(self) -> list[str]:
        return sorted(set(list(self._singletons.keys()) + list(self._factories.keys())))


_container: DependencyContainer | None = None


def get_container() -> DependencyContainer:
    global _container
    if _container is None:
        _container = DependencyContainer()
    return _container


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def get_correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


def get_response_time(request: Request) -> float:
    return getattr(request.state, "response_time_ms", 0.0)
