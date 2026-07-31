"""Transaction manager implementation for the Database Architecture."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.db.base import TransactionManager
from app.db.enums import TransactionState
from app.db.models import TransactionRecord

logger = logging.getLogger(__name__)


class InMemoryTransactionManager(TransactionManager):
    """In-memory transaction manager with savepoint support."""

    def __init__(self) -> None:
        self._active = False
        self._savepoints: list[str] = []
        self._records: list[TransactionRecord] = []
        self._current_record = TransactionRecord()

    async def begin(self) -> None:
        if self._active:
            raise RuntimeError("Transaction already active")
        self._active = True
        self._current_record = TransactionRecord(state=TransactionState.ACTIVE)
        self._savepoints.clear()

    async def commit(self) -> None:
        if not self._active:
            raise RuntimeError("No active transaction")
        self._current_record.finish(TransactionState.COMMITTED)
        self._records.append(self._current_record)
        self._active = False
        self._savepoints.clear()

    async def rollback(self) -> None:
        if not self._active:
            raise RuntimeError("No active transaction")
        self._current_record.finish(TransactionState.ROLLED_BACK)
        self._records.append(self._current_record)
        self._active = False
        self._savepoints.clear()

    async def savepoint(self) -> str:
        if not self._active:
            raise RuntimeError("No active transaction")
        sp_id = f"sp-{uuid.uuid4().hex[:8]}"
        self._savepoints.append(sp_id)
        self._current_record.savepoints.append(sp_id)
        return sp_id

    async def release_savepoint(self, savepoint_id: str) -> None:
        if savepoint_id in self._savepoints:
            self._savepoints.remove(savepoint_id)

    async def rollback_to_savepoint(self, savepoint_id: str) -> None:
        if savepoint_id in self._savepoints:
            idx = self._savepoints.index(savepoint_id)
            self._savepoints = self._savepoints[:idx]

    def is_active(self) -> bool:
        return self._active

    def get_records(self) -> list[TransactionRecord]:
        return list(self._records)

    def get_current_record(self) -> TransactionRecord:
        return self._current_record

    def get_statistics(self) -> dict[str, Any]:
        total = len(self._records)
        committed = sum(1 for r in self._records if r.state == TransactionState.COMMITTED.value)
        rolled_back = sum(1 for r in self._records if r.state == TransactionState.ROLLED_BACK.value)
        return {
            "total": total,
            "committed": committed,
            "rolled_back": rolled_back,
            "active": self._active,
        }
