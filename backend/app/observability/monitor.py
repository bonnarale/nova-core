"""Observability monitor — system and application monitoring."""

from __future__ import annotations

import os
import platform
import threading
import time
from typing import Any


class SystemMonitor:
    """System resource monitor — CPU, memory, threads, process info."""

    def __init__(self) -> None:
        self._started_at = time.monotonic()

    def get_system_info(self) -> dict[str, Any]:
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
            "pid": os.getpid(),
            "thread_count": threading.active_count(),
        }

    def get_process_info(self) -> dict[str, Any]:
        return {
            "pid": os.getpid(),
            "thread_count": threading.active_count(),
            "uptime_seconds": time.monotonic() - self._started_at,
        }

    def get_memory_info(self) -> dict[str, Any]:
        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            return {
                "max_rss_kb": getattr(usage, "ru_maxrss", 0),
                "user_time": getattr(usage, "ru_utime", 0.0),
                "system_time": getattr(usage, "ru_stime", 0.0),
            }
        except (ImportError, AttributeError):
            return {"max_rss_kb": 0, "user_time": 0.0, "system_time": 0.0}

    def get_thread_info(self) -> dict[str, Any]:
        threads = threading.enumerate()
        return {
            "active_count": len(threads),
            "names": [t.name for t in threads],
            "daemon_count": sum(1 for t in threads if t.daemon),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "system": self.get_system_info(),
            "process": self.get_process_info(),
            "memory": self.get_memory_info(),
            "threads": self.get_thread_info(),
        }


class ApplicationMonitor:
    """Application-level metrics collector."""

    def __init__(self) -> None:
        self._request_count = 0
        self._response_count = 0
        self._error_count = 0
        self._latencies: list[float] = []
        self._lock = threading.Lock()

    def record_request(self) -> None:
        with self._lock:
            self._request_count += 1

    def record_response(self, latency_ms: float) -> None:
        with self._lock:
            self._response_count += 1
            self._latencies.append(latency_ms)

    def record_error(self) -> None:
        with self._lock:
            self._error_count += 1

    @property
    def request_count(self) -> int:
        return self._request_count

    @property
    def response_count(self) -> int:
        return self._response_count

    @property
    def error_count(self) -> int:
        return self._error_count

    @property
    def average_latency_ms(self) -> float:
        with self._lock:
            if not self._latencies:
                return 0.0
            return sum(self._latencies) / len(self._latencies)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_count": self._request_count,
            "response_count": self._response_count,
            "error_count": self._error_count,
            "average_latency_ms": self.average_latency_ms,
            "latency_count": len(self._latencies),
        }

    def reset(self) -> None:
        with self._lock:
            self._request_count = 0
            self._response_count = 0
            self._error_count = 0
            self._latencies.clear()
