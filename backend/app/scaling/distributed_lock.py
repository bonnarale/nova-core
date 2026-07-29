"""In-memory distributed lock with timeout and lease renewal."""

from __future__ import annotations

import logging
import threading
import time
import uuid

from app.scaling.base import DistributedLockProvider
from app.scaling.enums import LockState

logger = logging.getLogger(__name__)


class _LockEntry:
    __slots__ = ("key", "owner", "state", "acquired_at", "expires_at", "lease")

    def __init__(self, key: str, owner: str, lease: float) -> None:
        self.key = key
        self.owner = owner
        self.state = LockState.HELD.value
        self.acquired_at = time.time()
        self.expires_at = time.time() + lease if lease > 0 else 0.0
        self.lease = lease


class InMemoryDistributedLock(DistributedLockProvider):
    """In-memory distributed lock with timeout, lease renewal."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._locks: dict[str, _LockEntry] = {}

    async def acquire(self, key: str, timeout: float = 30.0, lease: float = 60.0) -> bool:
        start = time.time()
        owner = str(uuid.uuid4())
        while True:
            with self._lock:
                entry = self._locks.get(key)
                if entry is None or entry.state == LockState.EXPIRED.value:
                    self._locks[key] = _LockEntry(key, owner, lease)
                    logger.debug("Lock acquired: %s by %s", key, owner)
                    return True
                if entry.expires_at > 0 and time.time() > entry.expires_at:
                    entry.state = LockState.EXPIRED.value
                    self._locks[key] = _LockEntry(key, owner, lease)
                    return True
            elapsed = time.time() - start
            if elapsed >= timeout:
                return False
            await _async_sleep(0.01)

    async def release(self, key: str) -> bool:
        with self._lock:
            if key in self._locks:
                del self._locks[key]
                logger.debug("Lock released: %s", key)
                return True
            return False

    async def is_locked(self, key: str) -> bool:
        with self._lock:
            entry = self._locks.get(key)
            if entry is None:
                return False
            if entry.expires_at > 0 and time.time() > entry.expires_at:
                entry.state = LockState.EXPIRED.value
                return False
            return entry.state == LockState.HELD.value

    async def extend(self, key: str, lease: float = 60.0) -> bool:
        with self._lock:
            entry = self._locks.get(key)
            if entry and entry.state == LockState.HELD.value:
                entry.expires_at = time.time() + lease
                entry.lease = lease
                return True
            return False

    def get_lock_info(self, key: str) -> dict[str, str] | None:
        with self._lock:
            entry = self._locks.get(key)
            if entry:
                return {
                    "key": entry.key,
                    "owner": entry.owner,
                    "state": entry.state,
                }
            return None


async def _async_sleep(duration: float) -> None:
    import asyncio
    await asyncio.sleep(duration)
