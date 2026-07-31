from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .schemas import SelfImprovementItem


class SelfImprovementEngine:
    CATEGORIES = [
        "architectural",
        "performance",
        "workflow",
        "memory",
        "learning",
        "security",
        "optimization",
        "technical_debt",
        "roadmap",
    ]

    def __init__(self) -> None:
        self._items: dict[str, SelfImprovementItem] = {}

    def identify(
        self, category: str, title: str, description: str, priority: int = 3
    ) -> dict:
        item = SelfImprovementItem(
            category=category,
            title=title,
            description=description,
            priority=priority,
        )
        self._items[item.id] = item
        return self._item_to_dict(item)

    def propose(self, item_id: str) -> dict | None:
        item = self._items.get(item_id)
        if item is None or item.status != "identified":
            return None
        item.status = "proposed"
        item.updated_at = datetime.now(timezone.utc).isoformat()
        return self._item_to_dict(item)

    def approve(self, item_id: str) -> dict | None:
        item = self._items.get(item_id)
        if item is None or item.status != "proposed":
            return None
        item.status = "approved"
        item.updated_at = datetime.now(timezone.utc).isoformat()
        return self._item_to_dict(item)

    def start(self, item_id: str) -> dict | None:
        item = self._items.get(item_id)
        if item is None or item.status != "approved":
            return None
        item.status = "in_progress"
        item.updated_at = datetime.now(timezone.utc).isoformat()
        return self._item_to_dict(item)

    def complete(self, item_id: str) -> dict | None:
        item = self._items.get(item_id)
        if item is None or item.status != "in_progress":
            return None
        item.status = "completed"
        item.updated_at = datetime.now(timezone.utc).isoformat()
        return self._item_to_dict(item)

    def get_item(self, item_id: str) -> dict | None:
        item = self._items.get(item_id)
        if item is None:
            return None
        return self._item_to_dict(item)

    def list_items(
        self, status: str | None = None, category: str | None = None
    ) -> list[dict]:
        items = list(self._items.values())
        if status is not None:
            items = [i for i in items if i.status == status]
        if category is not None:
            items = [i for i in items if i.category == category]
        return [self._item_to_dict(i) for i in items]

    def get_improvement_opportunities(self) -> list[dict]:
        pending = [i for i in self._items.values() if i.status == "identified"]
        pending.sort(key=lambda i: i.priority, reverse=True)
        return [self._item_to_dict(i) for i in pending]

    def _item_to_dict(self, item: SelfImprovementItem) -> dict:
        return {
            "id": item.id,
            "category": item.category,
            "title": item.title,
            "description": item.description,
            "status": item.status,
            "priority": item.priority,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }

    def to_dict(self) -> dict:
        return {
            "items": {
                k: self._item_to_dict(v) for k, v in self._items.items()
            }
        }
