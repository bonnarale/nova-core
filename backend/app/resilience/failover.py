"""Failover management."""

from __future__ import annotations

import threading
import time
from typing import Any


class FailoverManager:
    """Provider, model, database, and cache failover management."""

    def __init__(self) -> None:
        self._chains: dict[str, list[str]] = {}
        self._current: dict[str, str] = {}
        self._events: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def register_chain(self, name: str, providers: list[str]) -> None:
        with self._lock:
            self._chains[name] = list(providers)
            if providers:
                self._current[name] = providers[0]

    def get_current(self, name: str) -> str | None:
        with self._lock:
            return self._current.get(name)

    async def failover(self, name: str, reason: str = "") -> str | None:
        with self._lock:
            chain = self._chains.get(name, [])
            current = self._current.get(name)
            if not chain or not current:
                return None
            try:
                idx = chain.index(current)
                if idx + 1 < len(chain):
                    next_provider = chain[idx + 1]
                    self._current[name] = next_provider
                    self._events.append({
                        "name": name,
                        "from": current,
                        "to": next_provider,
                        "reason": reason,
                        "timestamp": time.time(),
                    })
                    return next_provider
            except ValueError:
                pass
        return None

    def reset(self, name: str) -> bool:
        with self._lock:
            chain = self._chains.get(name, [])
            if chain:
                self._current[name] = chain[0]
                return True
            return False

    def reset_all(self) -> None:
        with self._lock:
            for name, chain in self._chains.items():
                if chain:
                    self._current[name] = chain[0]

    def get_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._events[-limit:])

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_chains": len(self._chains),
                "total_failovers": len(self._events),
                "current": dict(self._current),
            }
