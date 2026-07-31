"""Data partitioning strategies."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class Partition:
    """A single data partition."""

    __slots__ = ("partition_id", "name", "size", "created_at")

    def __init__(self, partition_id: int, name: str = "") -> None:
        self.partition_id = partition_id
        self.name = name or f"partition-{partition_id}"
        self.size = 0
        self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "partition_id": self.partition_id,
            "name": self.name,
            "size": self.size,
            "created_at": self.created_at,
        }


class TimePartitioning:
    """Time-based partitioning (daily, hourly)."""

    def __init__(self, interval: str = "daily", max_partitions: int = 30) -> None:
        self._interval = interval
        self._max_partitions = max_partitions
        self._partitions: dict[str, Partition] = {}
        self._counter = 0

    def get_partition_key(self, timestamp: float | None = None) -> str:
        ts = timestamp or time.time()
        if self._interval == "hourly":
            return time.strftime("%Y%m%d%H", time.gmtime(ts))
        return time.strftime("%Y%m%d", time.gmtime(ts))

    def get_or_create_partition(self, key: str) -> Partition:
        if key not in self._partitions:
            self._partitions[key] = Partition(self._counter, key)
            self._counter += 1
            if len(self._partitions) > self._max_partitions:
                oldest = min(self._partitions, key=lambda k: self._partitions[k].created_at)
                del self._partitions[oldest]
        return self._partitions[key]

    def add_item(self, key: str) -> int:
        p = self.get_or_create_partition(key)
        p.size += 1
        return p.partition_id

    def get_statistics(self) -> dict[str, Any]:
        return {
            "interval": self._interval,
            "total_partitions": len(self._partitions),
            "max_partitions": self._max_partitions,
            "total_items": sum(p.size for p in self._partitions.values()),
        }

    def list_partitions(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._partitions.values()]


class HashPartitioning:
    """Hash-based partitioning."""

    def __init__(self, num_partitions: int = 8) -> None:
        self._num_partitions = num_partitions
        self._partitions = [Partition(i) for i in range(num_partitions)]

    def get_partition(self, key: str) -> int:
        import hashlib
        h = int(hashlib.md5(key.encode()).hexdigest(), 16)
        return h % self._num_partitions

    def add_item(self, key: str) -> int:
        pid = self.get_partition(key)
        self._partitions[pid].size += 1
        return pid

    def get_statistics(self) -> dict[str, Any]:
        sizes = [p.size for p in self._partitions]
        return {
            "num_partitions": self._num_partitions,
            "total_items": sum(sizes),
            "partition_sizes": sizes,
        }
