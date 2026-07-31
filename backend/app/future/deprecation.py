"""Deprecation management for the Future subsystem."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.future.enums import DeprecationSeverity


@dataclass
class DeprecationEntry:
    feature: str
    severity: DeprecationSeverity
    message: str = ""
    deprecated_in: str = ""
    remove_in: str = ""
    migration_guide: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sunset_date: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature": self.feature, "severity": self.severity.value,
            "message": self.message, "deprecated_in": self.deprecated_in,
            "remove_in": self.remove_in, "migration_guide": self.migration_guide,
            "created_at": self.created_at.isoformat(),
            "sunset_date": self.sunset_date.isoformat() if self.sunset_date else None,
            "metadata": self.metadata,
        }


class DeprecationManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, DeprecationEntry] = {}
        self._usage: dict[str, int] = {}

    def register(self, feature: str, severity: str, message: str = "", deprecated_in: str = "", remove_in: str = "", migration_guide: str = "", sunset_date: datetime | None = None) -> DeprecationEntry:
        entry = DeprecationEntry(
            feature=feature, severity=DeprecationSeverity(severity), message=message,
            deprecated_in=deprecated_in, remove_in=remove_in, migration_guide=migration_guide,
            sunset_date=sunset_date,
        )
        with self._lock:
            self._entries[feature] = entry
        return entry

    def is_deprecated(self, feature: str) -> bool:
        return feature in self._entries

    def get_entry(self, feature: str) -> DeprecationEntry | None:
        return self._entries.get(feature)

    def get_entries(self) -> list[DeprecationEntry]:
        return list(self._entries.values())

    def check_feature(self, feature: str) -> dict[str, Any] | None:
        entry = self._entries.get(feature)
        if not entry:
            return None
        with self._lock:
            self._usage[feature] = self._usage.get(feature, 0) + 1
        return entry.to_dict()

    def remove_entry(self, feature: str) -> bool:
        with self._lock:
            return self._entries.pop(feature, None) is not None

    def get_usage(self) -> dict[str, int]:
        return dict(self._usage)

    def get_warnings(self) -> list[DeprecationEntry]:
        return [e for e in self._entries.values() if e.severity in (DeprecationSeverity.WARNING, DeprecationSeverity.ERROR)]

    def summary(self) -> dict[str, Any]:
        severities: dict[str, int] = {}
        for e in self._entries.values():
            severities[e.severity.value] = severities.get(e.severity.value, 0) + 1
        return {"total": len(self._entries), "by_severity": severities, "total_usage": sum(self._usage.values())}
