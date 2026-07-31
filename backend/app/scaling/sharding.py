"""Sharding with configurable shard counts and key-based routing."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from app.scaling.enums import ShardKey

logger = logging.getLogger(__name__)


class Shard:
    """Represents a single shard."""

    __slots__ = ("shard_id", "name", "size", "metadata")

    def __init__(self, shard_id: int, name: str = "") -> None:
        self.shard_id = shard_id
        self.name = name or f"shard-{shard_id}"
        self.size = 0
        self.metadata: dict[str, Any] = {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "shard_id": self.shard_id,
            "name": self.name,
            "size": self.size,
            "metadata": dict(self.metadata),
        }


class ShardingStrategy:
    """Hash-based sharding with consistent routing."""

    def __init__(self, num_shards: int = 8) -> None:
        self._num_shards = num_shards
        self._shards = [Shard(i) for i in range(num_shards)]
        self._routing_table: dict[str, int] = {}

    @property
    def num_shards(self) -> int:
        return self._num_shards

    def get_shard(self, key: str) -> int:
        if key in self._routing_table:
            return self._routing_table[key]
        h = int(hashlib.md5(key.encode()).hexdigest(), 16)
        shard_id = h % self._num_shards
        self._routing_table[key] = shard_id
        return shard_id

    def get_shard_info(self, shard_id: int) -> Shard | None:
        if 0 <= shard_id < self._num_shards:
            return self._shards[shard_id]
        return None

    def increment_size(self, shard_id: int) -> None:
        if 0 <= shard_id < self._num_shards:
            self._shards[shard_id].size += 1

    def get_statistics(self) -> dict[str, Any]:
        sizes = [s.size for s in self._shards]
        return {
            "num_shards": self._num_shards,
            "total_items": sum(sizes),
            "shard_sizes": sizes,
            "min_size": min(sizes) if sizes else 0,
            "max_size": max(sizes) if sizes else 0,
            "avg_size": round(sum(sizes) / len(sizes), 2) if sizes else 0,
            "routing_entries": len(self._routing_table),
        }


class DomainSharding:
    """Multi-domain sharding for different subsystems."""

    def __init__(self, domains: dict[str, int] | None = None) -> None:
        if domains is None:
            domains = {
                ShardKey.CONVERSATION.value: 8,
                ShardKey.VECTOR_MEMORY.value: 16,
                ShardKey.KNOWLEDGE.value: 8,
                ShardKey.EVENTS.value: 4,
                ShardKey.USER.value: 4,
            }
        self._strategies: dict[str, ShardingStrategy] = {
            domain: ShardingStrategy(num_shards)
            for domain, num_shards in domains.items()
        }

    def get_shard(self, domain: str, key: str) -> int:
        strategy = self._strategies.get(domain)
        if strategy is None:
            return 0
        return strategy.get_shard(key)

    def get_domain_statistics(self) -> dict[str, Any]:
        return {
            domain: strategy.get_statistics()
            for domain, strategy in self._strategies.items()
        }

    def add_domain(self, domain: str, num_shards: int = 8) -> None:
        if domain not in self._strategies:
            self._strategies[domain] = ShardingStrategy(num_shards)
