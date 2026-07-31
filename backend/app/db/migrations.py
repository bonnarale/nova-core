"""Migration management for the Database Architecture."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.db.base import MigrationProvider
from app.db.enums import MigrationStatus
from app.db.models import MigrationInfo

logger = logging.getLogger(__name__)


class InMemoryMigrationProvider(MigrationProvider):
    """In-memory migration provider for testing."""

    def __init__(self) -> None:
        self._current_revision = "001"
        self._head_revision = "001"
        self._migrations: list[MigrationInfo] = [
            MigrationInfo(
                revision="001",
                down_revision="",
                description="Initial schema",
                status=MigrationStatus.CURRENT.value,
                applied_at=time.time(),
            ),
        ]

    async def get_current_revision(self) -> str:
        return self._current_revision

    async def get_head_revision(self) -> str:
        return self._head_revision

    async def get_pending_migrations(self) -> list[dict[str, Any]]:
        pending: list[MigrationInfo] = []
        for m in self._migrations:
            if m.status in (MigrationStatus.PENDING.value, MigrationStatus.OUTDATED.value):
                pending.append(m)
        return [m.to_dict() for m in pending]

    async def get_migration_status(self) -> dict[str, Any]:
        current = await self.get_current_revision()
        head = await self.get_head_revision()
        is_current = current == head
        return {
            "current_revision": current,
            "head_revision": head,
            "status": MigrationStatus.CURRENT.value if is_current else MigrationStatus.OUTDATED.value,
            "total_migrations": len(self._migrations),
            "pending": len(await self.get_pending_migrations()),
            "migrations": [m.to_dict() for m in self._migrations],
        }

    async def validate_migrations(self) -> bool:
        return True

    def add_migration(self, info: MigrationInfo) -> None:
        self._migrations.append(info)
        self._head_revision = info.revision

    def set_current_revision(self, revision: str) -> None:
        self._current_revision = revision
