"""Capability registry for future capabilities."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.future.enums import CapabilityState


@dataclass
class Capability:
    name: str
    version: str
    state: CapabilityState = CapabilityState.REGISTERED
    description: str = ""
    provider: str = ""
    dependencies: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "version": self.version, "state": self.state.value,
            "description": self.description, "provider": self.provider,
            "dependencies": self.dependencies,
            "created_at": self.created_at.isoformat(), "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


class CapabilityRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._capabilities: dict[str, Capability] = {}

    def register(self, name: str, version: str, metadata: dict[str, Any] | None = None) -> Capability:
        with self._lock:
            cap = Capability(name=name, version=version, metadata=metadata or {})
            self._capabilities[name] = cap
        return cap

    def get(self, name: str) -> Capability | None:
        return self._capabilities.get(name)

    def list_capabilities(self) -> list[Capability]:
        return list(self._capabilities.values())

    def is_available(self, name: str) -> bool:
        cap = self._capabilities.get(name)
        return cap is not None and cap.state in (CapabilityState.STABLE, CapabilityState.BETA)

    def update_state(self, name: str, state: str) -> bool:
        with self._lock:
            cap = self._capabilities.get(name)
            if not cap:
                return False
            cap.state = CapabilityState(state)
            cap.updated_at = datetime.now(timezone.utc)
            return True

    def remove(self, name: str) -> bool:
        with self._lock:
            return self._capabilities.pop(name, None) is not None

    def list_by_state(self, state: str) -> list[Capability]:
        return [c for c in self._capabilities.values() if c.state.value == state]

    def summary(self) -> dict[str, Any]:
        states: dict[str, int] = {}
        for cap in self._capabilities.values():
            states[cap.state.value] = states.get(cap.state.value, 0) + 1
        return {"total": len(self._capabilities), "by_state": states}

    @staticmethod
    def default_capabilities() -> list[dict[str, str]]:
        return [
            {"name": "multimodal_providers", "description": "Multimodal input/output providers"},
            {"name": "voice_interfaces", "description": "Voice input and output interfaces"},
            {"name": "vision_interfaces", "description": "Visual input and processing interfaces"},
            {"name": "autonomous_agents", "description": "Fully autonomous agent capabilities"},
            {"name": "distributed_cognition", "description": "Distributed cognitive processing"},
            {"name": "additional_reasoning", "description": "Additional reasoning strategy providers"},
            {"name": "external_knowledge", "description": "External knowledge source integration"},
        ]
