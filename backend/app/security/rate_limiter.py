"""Rate limiting subsystem."""

from __future__ import annotations

import threading
import time
from typing import Any

from app.security.enums import RateLimitStrategy
from app.security.models import RateLimitRule


class RateLimiter:
    """In-memory rate limiter with multiple strategies."""

    def __init__(self) -> None:
        self._rules: dict[str, RateLimitRule] = {}
        self._windows: dict[str, list[float]] = {}
        self._tokens: dict[str, float] = {}
        self._block_count = 0
        self._lock = threading.Lock()

    def add_rule(self, rule: RateLimitRule) -> None:
        with self._lock:
            self._rules[rule.resource] = rule

    def remove_rule(self, resource: str) -> bool:
        with self._lock:
            if resource in self._rules:
                del self._rules[resource]
                return True
        return False

    def check(self, resource: str, client_id: str = "default") -> dict[str, Any]:
        rule = self._rules.get(resource)
        if rule is None or not rule.enabled:
            return {"allowed": True, "remaining": -1, "limit": -1}
        key = f"{resource}:{client_id}"
        if rule.strategy == RateLimitStrategy.FIXED_WINDOW.value:
            return self._check_fixed_window(key, rule)
        elif rule.strategy == RateLimitStrategy.SLIDING_WINDOW.value:
            return self._check_sliding_window(key, rule)
        elif rule.strategy == RateLimitStrategy.TOKEN_BUCKET.value:
            return self._check_token_bucket(key, rule)
        return {"allowed": True, "remaining": rule.max_requests, "limit": rule.max_requests}

    def _check_fixed_window(self, key: str, rule: RateLimitRule) -> dict[str, Any]:
        now = time.time()
        window_start = now - (now % rule.window_seconds)
        window_key = f"{key}:{int(window_start)}"
        with self._lock:
            count = len(self._windows.get(window_key, []))
            if count >= rule.max_requests:
                self._block_count += 1
                return {"allowed": False, "remaining": 0, "limit": rule.max_requests}
            self._windows.setdefault(window_key, []).append(now)
            return {"allowed": True, "remaining": rule.max_requests - count - 1, "limit": rule.max_requests}

    def _check_sliding_window(self, key: str, rule: RateLimitRule) -> dict[str, Any]:
        now = time.time()
        cutoff = now - rule.window_seconds
        with self._lock:
            requests = self._windows.get(key, [])
            self._windows[key] = [t for t in requests if t > cutoff]
            count = len(self._windows[key])
            if count >= rule.max_requests:
                self._block_count += 1
                return {"allowed": False, "remaining": 0, "limit": rule.max_requests}
            self._windows[key].append(now)
            return {"allowed": True, "remaining": rule.max_requests - count - 1, "limit": rule.max_requests}

    def _check_token_bucket(self, key: str, rule: RateLimitRule) -> dict[str, Any]:
        now = time.time()
        with self._lock:
            if key not in self._tokens:
                self._tokens[key] = float(rule.max_requests)
            tokens = self._tokens[key]
            refill = (rule.window_seconds / rule.max_requests)
            elapsed = now - (self._windows.get(f"{key}_last", [now])[0] if f"{key}_last" in self._windows else now)
            tokens = min(rule.max_requests, tokens + elapsed / refill)
            if tokens < 1:
                self._block_count += 1
                return {"allowed": False, "remaining": 0, "limit": rule.max_requests}
            self._tokens[key] = tokens - 1
            self._windows[f"{key}_last"] = [now]
            return {"allowed": True, "remaining": int(tokens - 1), "limit": rule.max_requests}

    def get_block_count(self) -> int:
        return self._block_count

    def list_rules(self) -> list[RateLimitRule]:
        return list(self._rules.values())

    def reset(self, resource: str | None = None) -> None:
        with self._lock:
            if resource:
                self._windows = {k: v for k, v in self._windows.items() if not k.startswith(resource)}
            else:
                self._windows.clear()
                self._tokens.clear()
