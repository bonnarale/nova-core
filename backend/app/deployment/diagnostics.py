"""Diagnostics for the Deployment subsystem."""

from __future__ import annotations

import logging
import platform
import sys
import time
from typing import Any

logger = logging.getLogger(__name__)


class DeploymentDiagnostics:
    """Collects system and runtime diagnostics."""

    def __init__(self) -> None:
        self._start_time = time.time()
        self._custom_checks: dict[str, dict[str, Any]] = {}

    async def collect(self) -> dict[str, Any]:
        return {
            "python": self._get_python_info(),
            "platform": self._get_platform_info(),
            "runtime": self._get_runtime_info(),
            "checks": dict(self._custom_checks),
        }

    def _get_python_info(self) -> dict[str, Any]:
        return {
            "version": sys.version,
            "version_info": list(sys.version_info[:3]),
            "implementation": sys.implementation.name,
        }

    def _get_platform_info(self) -> dict[str, Any]:
        return {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_build": platform.python_build(),
        }

    def _get_runtime_info(self) -> dict[str, Any]:
        return {
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "pid": _get_pid(),
            "executable": sys.executable,
            "prefix": sys.prefix,
        }

    def add_check(self, name: str, passed: bool, details: dict[str, Any] | None = None) -> None:
        self._custom_checks[name] = {
            "passed": passed,
            "details": details or {},
            "timestamp": time.time(),
        }

    def remove_check(self, name: str) -> bool:
        if name in self._custom_checks:
            del self._custom_checks[name]
            return True
        return False

    def get_checks(self) -> dict[str, Any]:
        return dict(self._custom_checks)

    def get_summary(self) -> dict[str, Any]:
        total = len(self._custom_checks)
        passed = sum(1 for c in self._custom_checks.values() if c["passed"])
        return {
            "total_checks": total,
            "passed": passed,
            "failed": total - passed,
            "uptime_seconds": round(time.time() - self._start_time, 2),
        }


def _get_pid() -> int:
    try:
        import os
        return os.getpid()
    except Exception:
        return 0
