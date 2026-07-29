from __future__ import annotations

from .schemas import BacklogItem


class BacklogManager:
    def __init__(self) -> None:
        self.items: dict[str, BacklogItem] = {}

    def add(
        self,
        title: str,
        description: str = "",
        category: str = "general",
        priority: int = 3,
        source: str = "user",
    ) -> BacklogItem:
        item = BacklogItem(
            title=title,
            description=description,
            category=category,
            priority=priority,
            source=source,
        )
        self.items[item.id] = item
        return item

    def update(self, item_id: str, **kwargs: object) -> BacklogItem | None:
        item = self.items.get(item_id)
        if item is None:
            return None
        for key, value in kwargs.items():
            if hasattr(item, key):
                setattr(item, key, value)
        return item

    def approve(self, item_id: str) -> BacklogItem | None:
        item = self.items.get(item_id)
        if item is None:
            return None
        item.status = "approved"
        return item

    def reject(self, item_id: str) -> BacklogItem | None:
        item = self.items.get(item_id)
        if item is None:
            return None
        item.status = "rejected"
        return item

    def remove(self, item_id: str) -> bool:
        if item_id in self.items:
            del self.items[item_id]
            return True
        return False

    def get(self, item_id: str) -> BacklogItem | None:
        return self.items.get(item_id)

    def list_items(
        self, status: str | None = None, category: str | None = None
    ) -> list[BacklogItem]:
        items = list(self.items.values())
        if status:
            items = [i for i in items if i.status == status]
        if category:
            items = [i for i in items if i.category == category]
        return items

    def prioritize(self) -> list[BacklogItem]:
        return sorted(self.items.values(), key=lambda i: i.priority, reverse=True)

    def to_dict(self) -> dict:
        return {k: v.__dict__ for k, v in self.items.items()}
