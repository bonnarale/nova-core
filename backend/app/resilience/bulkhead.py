"""Bulkhead isolation for subsystem protection."""

from __future__ import annotations

import asyncio
import threading
from typing import Any


class Bulkhead:
    """Isolation bulkhead with concurrency limits."""

    __slots__ = ("name", "max_concurrent", "_current", "_total", "_rejected", "_lock")

    def __init__(self, name: str, max_concurrent: int = 10) -> None:
        self.name = name
        self.max_concurrent = max_concurrent
        self._current = 0
        self._total = 0
        self._rejected = 0
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        with self._lock:
            if self._current < self.max_concurrent:
                self._current += 1
                self._total += 1
                return True
            self._rejected += 1
            return False

    def release(self) -> None:
        with self._lock:
            if self._current > 0:
                self._current -= 1

    @property
    def available(self) -> int:
        with self._lock:
            return self.max_concurrent - self._current

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "max_concurrent": self.max_concurrent,
                "current": self._current,
                "available": self.max_concurrent - self._current,
                "total_acquired": self._total,
                "total_rejected": self._rejected,
            }


class BulkheadManager:
    """Manages multiple isolation bulkheads."""

    _DEFAULT_BULKHEADS: dict[str, int] = {
        "agents": 20,
        "workflows": 10,
        "tools": 15,
        "model_providers": 5,
        "scheduler_workers": 8,
    }

    def __init__(self) -> None:
        self._bulkheads: dict[str, Bulkhead] = {}
        for name, limit in self._DEFAULT_BULKHEADS.items():
            self._bulkheads[name] = Bulkhead(name, limit)

    def get_or_create(self, name: str, max_concurrent: int = 10) -> Bulkhead:
        if name not in self._bulkheads:
            self._bulkheads[name] = Bulkhead(name, max_concurrent)
        return self._bulkheads[name]

    def get(self, name: str) -> Bulkhead | None:
        return self._bulkheads.get(name)

    def get_all(self) -> dict[str, Bulkhead]:
        return dict(self._bulkheads)

    def get_summary(self) -> dict[str, Any]:
        summary: dict[str, Any] = {}
        for name, b in self._bulkheads.items():
            summary[name] = b.get_stats()
        return summary
