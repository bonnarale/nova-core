"""Rate control for request throttling."""

from __future__ import annotations

import threading
import time
from typing import Any


class RateController:
    """Token-bucket rate controller."""

    def __init__(self, rate: float = 100.0, burst: int = 100) -> None:
        self._rate = rate
        self._burst = burst
        self._tokens = float(burst)
        self._last_refill = time.time()
        self._total_allowed = 0
        self._total_denied = 0
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.time()
        elapsed = now - self._last_refill
        self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
        self._last_refill = now

    def allow(self, tokens: int = 1) -> bool:
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                self._total_allowed += 1
                return True
            self._total_denied += 1
            return False

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "rate": self._rate,
                "burst": self._burst,
                "available_tokens": self._tokens,
                "total_allowed": self._total_allowed,
                "total_denied": self._total_denied,
            }

    def reset(self) -> None:
        with self._lock:
            self._tokens = float(self._burst)
            self._last_refill = time.time()
