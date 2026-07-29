"""IP filtering and blocking."""

from __future__ import annotations

import re
import threading
from typing import Any

from app.security.enums import IPFilterAction


class IPFilter:
    """IP-based access filtering."""

    def __init__(self) -> None:
        self._rules: list[dict[str, Any]] = []
        self._blocked: set[str] = set()
        self._allowed: set[str] = set()
        self._lock = threading.Lock()

    def add_rule(
        self,
        pattern: str,
        action: IPFilterAction = IPFilterAction.DENY,
        priority: int = 0,
    ) -> None:
        with self._lock:
            self._rules.append({"pattern": pattern, "action": action, "priority": priority})
            self._rules.sort(key=lambda r: r["priority"], reverse=True)

    def block_ip(self, ip: str) -> None:
        with self._lock:
            self._blocked.add(ip)

    def allow_ip(self, ip: str) -> None:
        with self._lock:
            self._allowed.add(ip)

    def unblock_ip(self, ip: str) -> bool:
        with self._lock:
            if ip in self._blocked:
                self._blocked.discard(ip)
                return True
        return False

    def is_blocked(self, ip: str) -> bool:
        with self._lock:
            if ip in self._allowed:
                return False
            if ip in self._blocked:
                return True
        for rule in self._rules:
            if self._match(ip, rule["pattern"]):
                return rule["action"] == IPFilterAction.DENY
        return False

    def check(self, ip: str) -> dict[str, Any]:
        blocked = self.is_blocked(ip)
        return {"ip": ip, "allowed": not blocked, "action": "deny" if blocked else "allow"}

    def _match(self, ip: str, pattern: str) -> bool:
        if "/" in pattern:
            return self._match_cidr(ip, pattern)
        if "*" in pattern:
            regex = pattern.replace(".", r"\.").replace("*", ".*")
            return bool(re.fullmatch(regex, ip))
        return ip == pattern

    def _match_cidr(self, ip: str, cidr: str) -> bool:
        try:
            network, prefix_str = cidr.split("/")
            prefix = int(prefix_str)
            ip_int = self._ip_to_int(ip)
            net_int = self._ip_to_int(network)
            mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
            return (ip_int & mask) == (net_int & mask)
        except Exception:
            return False

    @staticmethod
    def _ip_to_int(ip: str) -> int:
        parts = ip.split(".")
        return (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])

    def list_blocked(self) -> list[str]:
        with self._lock:
            return list(self._blocked)

    def list_allowed(self) -> list[str]:
        with self._lock:
            return list(self._allowed)

    def list_rules(self) -> list[dict[str, Any]]:
        return list(self._rules)

    def clear(self) -> None:
        with self._lock:
            self._rules.clear()
            self._blocked.clear()
            self._allowed.clear()
