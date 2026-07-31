"""Observability collectors — collect metrics from all subsystems."""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from app.observability.models import CollectorType


class BaseCollector:
    """Base class for metric collectors."""

    def __init__(self, collector_type: CollectorType, name: str) -> None:
        self.collector_type = collector_type
        self.name = name
        self._collected_at: float = 0.0

    def collect(self) -> dict[str, Any]:
        self._collected_at = time.time()
        return {"collector": self.name, "type": self.collector_type.value, "timestamp": self._collected_at}


class SystemCollector(BaseCollector):
    """Collects system-level metrics: CPU, memory, threads."""

    def __init__(self) -> None:
        super().__init__(CollectorType.SYSTEM, "system")

    def collect(self) -> dict[str, Any]:
        base = super().collect()
        import os
        import platform
        import threading
        base.update({
            "pid": os.getpid(),
            "thread_count": threading.active_count(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
        })
        return base


class ApplicationCollector(BaseCollector):
    """Collects application-level metrics: requests, responses, errors."""

    def __init__(self) -> None:
        super().__init__(CollectorType.APPLICATION, "application")
        self._request_count = 0
        self._response_count = 0
        self._error_count = 0
        self._latencies: list[float] = []

    def record_request(self) -> None:
        self._request_count += 1

    def record_response(self, latency_ms: float) -> None:
        self._response_count += 1
        self._latencies.append(latency_ms)

    def record_error(self) -> None:
        self._error_count += 1

    def collect(self) -> dict[str, Any]:
        base = super().collect()
        avg_latency = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
        base.update({
            "request_count": self._request_count,
            "response_count": self._response_count,
            "error_count": self._error_count,
            "average_latency_ms": avg_latency,
        })
        return base


class AICollector(BaseCollector):
    """Collects AI-specific metrics: prompts, completions, tokens, latency."""

    def __init__(self) -> None:
        super().__init__(CollectorType.AI, "ai")
        self._prompt_count = 0
        self._completion_count = 0
        self._total_tokens = 0
        self._latencies: list[float] = []

    def record_prompt(self, tokens: int = 0, latency_ms: float = 0.0) -> None:
        self._prompt_count += 1
        self._total_tokens += tokens
        if latency_ms > 0:
            self._latencies.append(latency_ms)

    def record_completion(self, tokens: int = 0, latency_ms: float = 0.0) -> None:
        self._completion_count += 1
        self._total_tokens += tokens
        if latency_ms > 0:
            self._latencies.append(latency_ms)

    def collect(self) -> dict[str, Any]:
        base = super().collect()
        avg_latency = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
        base.update({
            "prompt_count": self._prompt_count,
            "completion_count": self._completion_count,
            "total_tokens": self._total_tokens,
            "average_latency_ms": avg_latency,
        })
        return base


class MemoryCollector(BaseCollector):
    """Collects memory-related metrics: cache hits, misses, memory usage."""

    def __init__(self) -> None:
        super().__init__(CollectorType.MEMORY, "memory")
        self._cache_hits = 0
        self._cache_misses = 0
        self._conversation_count = 0
        self._vector_count = 0

    def record_cache_hit(self) -> None:
        self._cache_hits += 1

    def record_cache_miss(self) -> None:
        self._cache_misses += 1

    def record_conversation(self) -> None:
        self._conversation_count += 1

    def record_vector(self) -> None:
        self._vector_count += 1

    def collect(self) -> dict[str, Any]:
        base = super().collect()
        total = self._cache_hits + self._cache_misses
        base.update({
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": self._cache_hits / total if total > 0 else 0.0,
            "conversation_count": self._conversation_count,
            "vector_count": self._vector_count,
        })
        return base


class ExecutionCollector(BaseCollector):
    """Collects execution metrics: goals, tasks, plans, workflows, agents, tools."""

    def __init__(self) -> None:
        super().__init__(CollectorType.EXECUTION, "execution")
        self._counts: dict[str, int] = {}

    def record(self, category: str) -> None:
        self._counts[category] = self._counts.get(category, 0) + 1

    def collect(self) -> dict[str, Any]:
        base = super().collect()
        base.update(dict(self._counts))
        return base


class CollectorRegistry:
    """Registry for all metric collectors."""

    def __init__(self) -> None:
        self._collectors: dict[str, BaseCollector] = {}

    def register(self, collector: BaseCollector) -> None:
        self._collectors[collector.name] = collector

    def unregister(self, name: str) -> bool:
        return self._collectors.pop(name, None) is not None

    def get(self, name: str) -> BaseCollector | None:
        return self._collectors.get(name)

    def list_collectors(self) -> list[str]:
        return list(self._collectors.keys())

    def collect_all(self) -> list[dict[str, Any]]:
        return [c.collect() for c in self._collectors.values()]

    def clear(self) -> int:
        count = len(self._collectors)
        self._collectors.clear()
        return count

    def to_dict(self) -> dict[str, Any]:
        return {
            "collectors": self.list_collectors(),
            "count": len(self._collectors),
        }
