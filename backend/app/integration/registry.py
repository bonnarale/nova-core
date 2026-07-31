"""Component registry for system integration."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from app.integration.enums import ComponentState

logger = logging.getLogger(__name__)


class ComponentInfo:
    """Stores metadata about a registered component."""

    __slots__ = (
        "name",
        "component",
        "component_type",
        "version",
        "dependencies",
        "state",
        "config",
        "registered_at",
        "initialized_at",
        "error",
    )

    def __init__(
        self,
        name: str,
        component: Any,
        component_type: str = "service",
        version: str = "0.1.0",
        dependencies: list[str] | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.component = component
        self.component_type = component_type
        self.version = version
        self.dependencies = dependencies or []
        self.state = ComponentState.REGISTERED
        self.config = config or {}
        self.registered_at = time.time()
        self.initialized_at: float | None = None
        self.error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "component_type": self.component_type,
            "version": self.version,
            "dependencies": self.dependencies,
            "state": self.state.value,
            "config": self.config,
            "registered_at": self.registered_at,
            "initialized_at": self.initialized_at,
            "error": self.error,
        }


class IntegrationRegistry:
    """Thread-safe registry for all system components."""

    def __init__(self) -> None:
        self._components: dict[str, ComponentInfo] = {}
        self._lock = threading.RLock()

    @property
    def components(self) -> dict[str, ComponentInfo]:
        with self._lock:
            return dict(self._components)

    def register(
        self,
        name: str,
        component: Any,
        component_type: str = "service",
        version: str = "0.1.0",
        dependencies: list[str] | None = None,
        config: dict[str, Any] | None = None,
    ) -> ComponentInfo:
        with self._lock:
            info = ComponentInfo(
                name=name,
                component=component,
                component_type=component_type,
                version=version,
                dependencies=dependencies,
                config=config,
            )
            self._components[name] = info
            logger.info("Registered component: %s (%s)", name, component_type)
            return info

    def unregister(self, name: str) -> bool:
        with self._lock:
            if name in self._components:
                del self._components[name]
                logger.info("Unregistered component: %s", name)
                return True
            return False

    def get(self, name: str) -> ComponentInfo | None:
        with self._lock:
            return self._components.get(name)

    def get_component(self, name: str) -> Any | None:
        with self._lock:
            info = self._components.get(name)
            return info.component if info else None

    def list_all(self) -> list[ComponentInfo]:
        with self._lock:
            return list(self._components.values())

    def list_by_type(self, component_type: str) -> list[ComponentInfo]:
        with self._lock:
            return [
                info
                for info in self._components.values()
                if info.component_type == component_type
            ]

    def list_by_state(self, state: ComponentState) -> list[ComponentInfo]:
        with self._lock:
            return [
                info for info in self._components.values() if info.state == state
            ]

    def update_state(self, name: str, state: ComponentState, error: str | None = None) -> bool:
        with self._lock:
            info = self._components.get(name)
            if info:
                info.state = state
                if state == ComponentState.READY or state == ComponentState.RUNNING:
                    info.initialized_at = time.time()
                if error:
                    info.error = error
                return True
            return False

    def count(self) -> int:
        with self._lock:
            return len(self._components)

    def clear(self) -> None:
        with self._lock:
            self._components.clear()
