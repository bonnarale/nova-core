"""Unit of Work implementation for the Database Architecture."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.db.base import UnitOfWork
from app.db.enums import TransactionState
from app.db.models import TransactionRecord

logger = logging.getLogger(__name__)


class InMemoryUnitOfWork(UnitOfWork):
    """In-memory Unit of Work implementation."""

    def __init__(self) -> None:
        self._active = False
        self._record = TransactionRecord()
        self._pending_changes: list[dict[str, Any]] = []
        self._snapshots: list[dict[str, Any]] = []

    async def begin(self) -> None:
        if self._active:
            raise RuntimeError("Transaction already active")
        self._active = True
        self._record = TransactionRecord(state=TransactionState.ACTIVE)
        self._pending_changes.clear()
        logger.debug("Unit of Work begun: %s", self._record.transaction_id)

    async def commit(self) -> None:
        if not self._active:
            raise RuntimeError("No active transaction")
        self._record.finish(TransactionState.COMMITTED)
        self._active = False
        self._pending_changes.clear()
        logger.debug("Unit of Work committed: %s", self._record.transaction_id)

    async def rollback(self) -> None:
        if not self._active:
            raise RuntimeError("No active transaction")
        self._record.finish(TransactionState.ROLLED_BACK)
        self._active = False
        self._pending_changes.clear()
        logger.debug("Unit of Work rolled back: %s", self._record.transaction_id)

    async def flush(self) -> None:
        if not self._active:
            raise RuntimeError("No active transaction")

    async def close(self) -> None:
        if self._active:
            await self.rollback()
        self._pending_changes.clear()

    def is_active(self) -> bool:
        return self._active

    def add_change(self, change: dict[str, Any]) -> None:
        if not self._active:
            raise RuntimeError("No active transaction")
        self._pending_changes.append(change)

    def get_changes(self) -> list[dict[str, Any]]:
        return list(self._pending_changes)

    def get_record(self) -> TransactionRecord:
        return self._record

    def __enter__(self) -> InMemoryUnitOfWork:
        return self

    def __exit__(self, *args: Any) -> None:
        pass
