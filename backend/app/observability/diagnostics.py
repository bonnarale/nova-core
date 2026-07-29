"""Observability diagnostics — runtime, dependency, and performance inspection."""

from __future__ import annotations

import os
import platform
import sys
import threading
import time
from typing import Any
from uuid import uuid4


class DiagnosticsEngine:
    """Diagnostics engine — inspect dependencies, configuration, runtime state."""

    def __init__(self) -> None:
        self._started_at = time.monotonic()
        self._custom_checks: dict[str, Any] = {}

    def register_check(self, name: str, check_fn: Any) -> None:
        self._custom_checks[name] = check_fn

    def unregister_check(self, name: str) -> bool:
        return self._custom_checks.pop(name, None) is not None

    async def inspect_dependencies(self) -> dict[str, Any]:
        deps: dict[str, Any] = {}
        deps["python"] = {"version": sys.version, "executable": sys.executable}
        deps["platform"] = {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        }
        for name, check_fn in self._custom_checks.items():
            try:
                result = check_fn()
                deps[name] = {"status": "ok", "data": result}
            except Exception as e:
                deps[name] = {"status": "error", "error": str(e)}
        return deps

    async def inspect_configuration(self) -> dict[str, Any]:
        return {
            "pid": os.getpid(),
            "cwd": os.getcwd(),
            "python_path": sys.path[:5],
            "thread_count": threading.active_count(),
        }

    async def inspect_runtime(self) -> dict[str, Any]:
        return {
            "uptime_seconds": time.monotonic() - self._started_at,
            "thread_count": threading.active_count(),
            "modules_loaded": len(sys.modules),
            "recursion_limit": sys.getrecursionlimit(),
        }

    async def inspect_threads(self) -> dict[str, Any]:
        threads = threading.enumerate()
        return {
            "active_count": len(threads),
            "threads": [
                {
                    "name": t.name,
                    "daemon": t.daemon,
                    "is_alive": t.is_alive(),
                }
                for t in threads
            ],
        }

    async def get_performance_report(self) -> dict[str, Any]:
        return {
            "uptime_seconds": time.monotonic() - self._started_at,
            "thread_count": threading.active_count(),
            "modules_loaded": len(sys.modules),
        }

    async def get_execution_report(self) -> dict[str, Any]:
        return {
            "pid": os.getpid(),
            "uptime_seconds": time.monotonic() - self._started_at,
            "thread_count": threading.active_count(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "uptime_seconds": time.monotonic() - self._started_at,
            "custom_checks": list(self._custom_checks.keys()),
        }
