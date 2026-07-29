"""Pluggable cache with LRU, TTL, and hit/miss tracking."""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from typing import Any

from app.scaling.base import CacheProvider
from app.scaling.enums import CacheStrategy
from app.scaling.models import CacheStats

logger = logging.getLogger(__name__)


class InMemoryCache(CacheProvider):
    """In-memory cache with LRU eviction and TTL expiration."""

    def __init__(
        self,
        max_size: int = 1000,
        strategy: CacheStrategy = CacheStrategy.LRU,
        default_ttl: float | None = None,
    ) -> None:
        self._max_size = max_size
        self._strategy = strategy
        self._default_ttl = default_ttl
        self._lock = threading.Lock()
        self._store: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._total_sets = 0
        self._total_deletes = 0

    async def get(self, key: str) -> Any | None:
        with self._lock:
            if key not in self._store:
                self._misses += 1
                return None
            value, expires_at = self._store[key]
            if expires_at > 0 and time.time() > expires_at:
                del self._store[key]
                self._misses += 1
                return None
            self._hits += 1
            self._store.move_to_end(key)
            return value

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = time.time() + effective_ttl if effective_ttl and effective_ttl > 0 else 0.0
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = (value, expires_at)
            self._total_sets += 1
            if len(self._store) > self._max_size:
                self._evict()

    async def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                self._total_deletes += 1
                return True
            return False

    async def exists(self, key: str) -> bool:
        with self._lock:
            if key not in self._store:
                return False
            _, expires_at = self._store[key]
            if expires_at > 0 and time.time() > expires_at:
                del self._store[key]
                return False
            return True

    async def clear(self) -> int:
        with self._lock:
            count = len(self._store)
            self._store.clear()
            return count

    async def size(self) -> int:
        with self._lock:
            return len(self._store)

    def get_stats(self) -> CacheStats:
        with self._lock:
            total = self._hits + self._misses
            hit_ratio = self._hits / total if total > 0 else 0.0
            return CacheStats(
                hits=self._hits,
                misses=self._misses,
                size=len(self._store),
                hit_ratio=round(hit_ratio, 4),
                total_sets=self._total_sets,
                total_deletes=self._total_deletes,
            )

    def _evict(self) -> None:
        if self._strategy == CacheStrategy.LRU:
            self._store.popitem(last=False)
        elif self._strategy == CacheStrategy.FIFO:
            self._store.popitem(last=False)
        else:
            self._store.popitem(last=False)


class LRUCache(InMemoryCache):
    """LRU cache (alias)."""

    def __init__(self, max_size: int = 1000, default_ttl: float | None = None) -> None:
        super().__init__(max_size=max_size, strategy=CacheStrategy.LRU, default_ttl=default_ttl)


class TTLCache(InMemoryCache):
    """TTL-only cache (alias)."""

    def __init__(self, max_size: int = 1000, default_ttl: float = 300.0) -> None:
        super().__init__(max_size=max_size, strategy=CacheStrategy.TTL, default_ttl=default_ttl)
