"""Response caching for model requests."""

import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A single cache entry."""

    key: str
    value: Any
    created_at: float
    ttl: float
    access_count: int = 0
    last_accessed: float = 0.0

    @property
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl

    def access(self) -> Any:
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value


class ResponseCache:
    """Cache for model responses."""

    def __init__(self, max_size: int = 1000, default_ttl: float = 300.0) -> None:
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            entry = self._cache[key]
            if entry.is_expired:
                del self._cache[key]
                self._misses += 1
                return None
            self._cache.move_to_end(key)
            self._hits += 1
            return entry.access()
        self._misses += 1
        return None

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        if key in self._cache:
            del self._cache[key]
        elif len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)
        self._cache[key] = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            ttl=ttl or self._default_ttl,
        )

    def invalidate(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> int:
        count = len(self._cache)
        self._cache.clear()
        return count

    def cleanup_expired(self) -> int:
        expired_keys = [k for k, v in self._cache.items() if v.is_expired]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        return {
            "size": self.size,
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
            "default_ttl": self._default_ttl,
        }

    @staticmethod
    def build_key(model: str, messages: list[dict[str, str]], **kwargs: Any) -> str:
        key_data = {"model": model, "messages": messages, **{k: v for k, v in kwargs.items() if isinstance(v, (str, int, float, bool, list, dict))}}
        return hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()


def get_response_cache(max_size: int = 1000, default_ttl: float = 300.0) -> ResponseCache:
    return ResponseCache(max_size=max_size, default_ttl=default_ttl)
