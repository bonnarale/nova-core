from __future__ import annotations

from collections import Counter

from .schemas import HistoryEntry


class HistoryManager:
    def __init__(self, max_entries: int = 1000) -> None:
        self.entries: list[HistoryEntry] = []
        self.max_entries = max_entries

    def record(self, action: str, details: dict | None = None) -> dict:
        entry = HistoryEntry(action=action, details=details if details is not None else {})
        self.entries.append(entry)
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]
        return entry.to_dict()

    def get_history(self, action: str | None = None, limit: int = 50) -> list[dict]:
        result = list(self.entries)
        if action:
            result = [e for e in result if e.action == action]
        return [e.to_dict() for e in result[-limit:]]

    def get_recent(self, limit: int = 10) -> list[dict]:
        return [e.to_dict() for e in self.entries[-limit:]]

    def clear(self) -> int:
        count = len(self.entries)
        self.entries.clear()
        return count

    def stats(self) -> dict:
        actions = Counter(e.action for e in self.entries)
        return {
            "total": len(self.entries),
            "max_entries": self.max_entries,
            "actions": dict(actions),
        }

    def to_dict(self) -> dict:
        return {
            "max_entries": self.max_entries,
            "entries": [e.to_dict() for e in self.entries],
        }
