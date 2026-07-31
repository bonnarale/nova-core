"""Fallback strategy management."""

from __future__ import annotations

import threading
from typing import Any, Callable, Coroutine, Awaitable

from app.resilience.enums import FallbackStrategy


class FallbackManager:
    """Manages fallback strategies for subsystem failures."""

    _SUBSYSTEM_FALLBACKS: dict[str, FallbackStrategy] = {
        "model_gateway": FallbackStrategy.CACHE,
        "tool_system": FallbackStrategy.DEFAULT,
        "rag": FallbackStrategy.STALE,
        "vector_memory": FallbackStrategy.CACHE,
        "knowledge_engine": FallbackStrategy.STALE,
        "scheduler": FallbackStrategy.SKIP,
        "workflow_engine": FallbackStrategy.DEGRADED,
        "plugins": FallbackStrategy.SKIP,
    }

    def __init__(self) -> None:
        self._strategies = dict(self._SUBSYSTEM_FALLBACKS)
        self._fallback_handlers: dict[str, Callable[..., Any]] = {}
        self._invocations: dict[str, int] = {}
        self._lock = threading.RLock()

    def set_strategy(self, subsystem: str, strategy: FallbackStrategy) -> None:
        with self._lock:
            self._strategies[subsystem] = strategy

    def get_strategy(self, subsystem: str) -> FallbackStrategy:
        with self._lock:
            return self._strategies.get(subsystem, FallbackStrategy.DEFAULT)

    def register_handler(self, subsystem: str, handler: Callable[..., Any]) -> None:
        with self._lock:
            self._fallback_handlers[subsystem] = handler

    async def execute(
        self,
        subsystem: str,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        try:
            return await func(*args, **kwargs)
        except Exception:
            with self._lock:
                self._invocations[subsystem] = self._invocations.get(subsystem, 0) + 1
            handler = self._fallback_handlers.get(subsystem)
            if handler:
                if callable(handler):
                    result = handler(*args, **kwargs) if not hasattr(handler, "__await__") else await handler(*args, **kwargs)
                    return result
            strategy = self.get_strategy(subsystem)
            if strategy == FallbackStrategy.SKIP:
                return None
            if strategy == FallbackStrategy.DEFAULT:
                return {"fallback": True, "subsystem": subsystem}
            return {"fallback": True, "subsystem": subsystem, "strategy": strategy.value}

    def get_invocations(self) -> dict[str, int]:
        with self._lock:
            return dict(self._invocations)

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "strategies": {k: v.value for k, v in self._strategies.items()},
                "invocations": dict(self._invocations),
                "total_invocations": sum(self._invocations.values()),
            }
