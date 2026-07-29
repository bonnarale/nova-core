"""Versioning system for semantic versioning and migration tracking."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.future.enums import VersionBumpType


@dataclass
class SemanticVersion:
    major: int = 0
    minor: int = 1
    patch: int = 0

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        return self.major == other.major and self.minor == other.minor and self.patch == other.patch

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __le__(self, other: object) -> bool:
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch) <= (other.major, other.minor, other.patch)

    def bump(self, bump_type: str) -> SemanticVersion:
        bt = VersionBumpType(bump_type)
        if bt == VersionBumpType.MAJOR:
            return SemanticVersion(self.major + 1, 0, 0)
        elif bt == VersionBumpType.MINOR:
            return SemanticVersion(self.major, self.minor + 1, 0)
        else:
            return SemanticVersion(self.major, self.minor, self.patch + 1)

    @staticmethod
    def parse(version_str: str) -> SemanticVersion:
        parts = version_str.strip().lstrip("v").split(".")
        try:
            return SemanticVersion(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            return SemanticVersion()

    def to_dict(self) -> dict[str, int]:
        return {"major": self.major, "minor": self.minor, "patch": self.patch}


@dataclass
class MigrationRecord:
    from_version: str
    to_version: str
    description: str = ""
    applied_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_version": self.from_version, "to_version": self.to_version,
            "description": self.description, "applied_at": self.applied_at.isoformat(),
            "success": self.success, "metadata": self.metadata,
        }


class VersionManager:
    def __init__(self, current_version: str = "0.1.0") -> None:
        self._lock = threading.Lock()
        self._current = SemanticVersion.parse(current_version)
        self._history: list[MigrationRecord] = []

    @property
    def current(self) -> SemanticVersion:
        return self._current

    def bump(self, bump_type: str) -> SemanticVersion:
        with self._lock:
            old = str(self._current)
            self._current = self._current.bump(bump_type)
            self._history.append(MigrationRecord(
                from_version=old, to_version=str(self._current),
                description=f"Bump {bump_type}",
            ))
        return self._current

    def set_version(self, version_str: str) -> SemanticVersion:
        with self._lock:
            old = str(self._current)
            self._current = SemanticVersion.parse(version_str)
            self._history.append(MigrationRecord(
                from_version=old, to_version=str(self._current), description="Manual set",
            ))
        return self._current

    def is_compatible(self, required: str) -> bool:
        req = SemanticVersion.parse(required)
        return self._current.major == req.major and self._current >= req

    def get_history(self) -> list[MigrationRecord]:
        return list(self._history)

    def record_migration(self, from_version: str, to_version: str, description: str = "", success: bool = True) -> MigrationRecord:
        record = MigrationRecord(from_version=from_version, to_version=to_version, description=description, success=success)
        with self._lock:
            self._history.append(record)
        return record

    def summary(self) -> dict[str, Any]:
        return {
            "current_version": str(self._current),
            "total_migrations": len(self._history),
            "successful": sum(1 for r in self._history if r.success),
            "failed": sum(1 for r in self._history if not r.success),
        }
