"""Roadmap and item tracking for the Future subsystem."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class RoadmapItem:
    id: str
    name: str
    description: str
    state: str  # FeatureState value
    version: str = "0.1.0"
    priority: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "state": self.state, "version": self.version, "priority": self.priority,
            "created_at": self.created_at.isoformat(), "updated_at": self.updated_at.isoformat(),
            "tags": self.tags, "metadata": self.metadata,
        }


class Roadmap:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, RoadmapItem] = {}

    def add(self, item: RoadmapItem) -> None:
        with self._lock:
            self._items[item.id] = item

    def get(self, item_id: str) -> RoadmapItem | None:
        return self._items.get(item_id)

    def list_items(self, state: str | None = None) -> list[RoadmapItem]:
        items = list(self._items.values())
        if state:
            items = [i for i in items if i.state == state]
        return sorted(items, key=lambda x: x.priority, reverse=True)

    def update_state(self, item_id: str, new_state: str) -> bool:
        with self._lock:
            item = self._items.get(item_id)
            if not item:
                return False
            item.state = new_state
            item.updated_at = datetime.now(timezone.utc)
            return True

    def remove(self, item_id: str) -> bool:
        with self._lock:
            return self._items.pop(item_id, None) is not None

    def summary(self) -> dict[str, Any]:
        states: dict[str, int] = {}
        for item in self._items.values():
            states[item.state] = states.get(item.state, 0) + 1
        return {"total": len(self._items), "by_state": states}
