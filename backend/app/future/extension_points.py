"""Extension point system for plugging in future modules."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ExtensionPoint:
    name: str
    extension_type: str
    provider: Any = None
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "extension_type": self.extension_type,
            "registered_at": self.registered_at.isoformat(), "metadata": self.metadata,
        }


class ExtensionPointRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._extensions: dict[str, ExtensionPoint] = {}

    def register(self, name: str, extension_type: str, provider: Any = None, metadata: dict[str, Any] | None = None) -> ExtensionPoint:
        with self._lock:
            ep = ExtensionPoint(name=name, extension_type=extension_type, provider=provider, metadata=metadata or {})
            self._extensions[name] = ep
        return ep

    def get(self, name: str) -> ExtensionPoint | None:
        return self._extensions.get(name)

    def list_extensions(self) -> list[ExtensionPoint]:
        return list(self._extensions.values())

    def remove(self, name: str) -> bool:
        with self._lock:
            return self._extensions.pop(name, None) is not None

    def list_by_type(self, extension_type: str) -> list[ExtensionPoint]:
        return [e for e in self._extensions.values() if e.extension_type == extension_type]

    def has_extension(self, name: str) -> bool:
        return name in self._extensions

    def summary(self) -> dict[str, Any]:
        types: dict[str, int] = {}
        for ext in self._extensions.values():
            types[ext.extension_type] = types.get(ext.extension_type, 0) + 1
        return {"total": len(self._extensions), "by_type": types}
