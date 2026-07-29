"""CPU and memory profiling."""

from __future__ import annotations

import threading
import time
import tracemalloc
import uuid
from typing import Any

from app.performance.enums import ProfileState, ProfileType


class CpuProfile:
    """CPU profiling snapshot."""

    __slots__ = ("function_calls", "total_time_ms", "top_functions")

    def __init__(self) -> None:
        self.function_calls: list[dict[str, Any]] = []
        self.total_time_ms: float = 0.0
        self.top_functions: list[dict[str, Any]] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "function_calls": self.function_calls,
            "total_time_ms": self.total_time_ms,
            "top_functions": self.top_functions,
        }


class MemoryProfile:
    """Memory profiling snapshot."""

    __slots__ = ("current_bytes", "peak_bytes", "allocations", "top_allocations")

    def __init__(self) -> None:
        self.current_bytes: int = 0
        self.peak_bytes: int = 0
        self.allocations: int = 0
        self.top_allocations: list[dict[str, Any]] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_bytes": self.current_bytes,
            "peak_bytes": self.peak_bytes,
            "allocations": self.allocations,
            "top_allocations": self.top_allocations,
        }


class ProfileSession:
    """An active profiling session."""

    __slots__ = ("session_id", "profile_type", "state", "start_time", "end_time", "results", "target")

    def __init__(self, session_id: str, profile_type: str, target: str | None = None) -> None:
        self.session_id = session_id
        self.profile_type = profile_type
        self.target = target
        self.state = ProfileState.COLLECTING
        self.start_time = time.time()
        self.end_time: float | None = None
        self.results: dict[str, Any] = {}

    def stop(self) -> None:
        self.end_time = time.time()
        self.state = ProfileState.ANALYZING

    def complete(self, results: dict[str, Any]) -> None:
        self.results = results
        self.state = ProfileState.COMPLETE

    def duration_ms(self) -> float:
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "profile_type": self.profile_type,
            "target": self.target,
            "state": self.state.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms(),
            "results": self.results,
        }


class Profiler:
    """CPU and memory profiler with async session management."""

    def __init__(self) -> None:
        self._sessions: dict[str, ProfileSession] = {}
        self._completed: list[ProfileSession] = []
        self._lock = threading.RLock()
        self._running = False

    def start(self) -> None:
        self._running = True

    def shutdown(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def start_session(self, profile_type: str = "comprehensive", target: str | None = None) -> str:
        session_id = str(uuid.uuid4())[:12]
        with self._lock:
            session = ProfileSession(session_id, profile_type, target)
            self._sessions[session_id] = session
        if profile_type in ("memory", "comprehensive"):
            tracemalloc.start()
        return session_id

    def stop_session(self, session_id: str) -> ProfileSession | None:
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if not session:
                return None
            session.stop()
        results: dict[str, Any] = {}
        if session.profile_type in ("memory", "comprehensive"):
            current, peak = tracemalloc.get_traced_memory()
            mem = MemoryProfile()
            mem.current_bytes = current
            mem.peak_bytes = peak
            try:
                snapshot = tracemalloc.take_snapshot()
                top = snapshot.statistics("lineno")[:10]
                mem.top_allocations = [
                    {"file": str(s.traceback), "size": s.size, "count": s.count}
                    for s in top
                ]
                mem.allocations = sum(s.count for s in snapshot.statistics("lineno"))
            except Exception:
                pass
            tracemalloc.stop()
            results["memory"] = mem.to_dict()
        if session.profile_type in ("cpu", "comprehensive"):
            cpu = CpuProfile()
            cpu.total_time_ms = session.duration_ms()
            results["cpu"] = cpu.to_dict()
        session.complete(results)
        with self._lock:
            self._completed.append(session)
        return session

    def get_session(self, session_id: str) -> ProfileSession | None:
        with self._lock:
            return self._sessions.get(session_id) or next(
                (s for s in self._completed if s.session_id == session_id), None
            )

    def get_active_sessions(self) -> list[dict[str, Any]]:
        with self._lock:
            return [s.to_dict() for s in self._sessions.values()]

    def get_completed_sessions(self) -> list[dict[str, Any]]:
        with self._lock:
            return [s.to_dict() for s in self._completed]
