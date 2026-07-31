"""NOVA CORE Testing Helpers — Chapter 29."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncGenerator, Callable, Coroutine
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock


async def run_with_timeout(coro: Coroutine[Any, Any, Any], timeout: float = 5.0) -> Any:
    """Run a coroutine with a timeout, raise TimeoutError if exceeded."""
    return await asyncio.wait_for(coro, timeout=timeout)


async def gather_with_limit(*coros: Coroutine[Any, Any, Any], limit: int = 10) -> list[Any]:
    """Run coroutines concurrently with a semaphore limit."""
    sem = asyncio.Semaphore(limit)
    async def _limited(c: Coroutine[Any, Any, Any]) -> Any:
        async with sem:
            return await c
    return await asyncio.gather(*(_limited(c) for c in coros))


def make_event_payload(**kwargs: Any) -> dict[str, Any]:
    """Create a standard event payload with defaults."""
    defaults = {"id": str(uuid.uuid4()), "timestamp": datetime.now(timezone.utc).isoformat(), "source": "test"}
    defaults.update(kwargs)
    return defaults


def assert_datetime_close(dt1: datetime, dt2: datetime, tolerance_seconds: float = 1.0) -> bool:
    """Check if two datetimes are within tolerance."""
    return abs((dt2 - dt1).total_seconds()) <= tolerance_seconds


async def create_test_event_bus() -> Any:
    """Create a fresh InMemoryEventBus for testing."""
    from app.events.bus import InMemoryEventBus
    return InMemoryEventBus()


def make_mock_response(status_code: int = 200, data: Any = None, headers: dict[str, str] | None = None) -> MagicMock:
    """Create a mock HTTP response."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json = MagicMock(return_value=data or {})
    mock.headers = headers or {}
    mock.text = str(data)
    return mock


def create_test_app_state(**overrides: Any) -> MagicMock:
    """Create a mock FastAPI app.state with all subsystem references."""
    state = MagicMock()
    state.cognitive_engine = MagicMock()
    state.memory = MagicMock()
    state.event_bus = MagicMock()
    state.scheduler = MagicMock()
    state.tool_registry = MagicMock()
    state.plugin_manager = MagicMock()
    state.security_engine = MagicMock()
    state.observability = MagicMock()
    state.workflow_engine = MagicMock()
    state.knowledge_graph = MagicMock()
    state.learning_engine = MagicMock()
    state.rag_engine = MagicMock()
    state.vector_memory = MagicMock()
    state.scaling_engine = MagicMock()
    state.deployment_manager = MagicMock()
    state.database_manager = MagicMock()
    for k, v in overrides.items():
        setattr(state, k, v)
    return state


@asynccontextmanager
async def temporary_event_bus() -> AsyncGenerator[Any, None]:
    """Create a temporary event bus that is cleaned up after use."""
    from app.events.bus import InMemoryEventBus
    bus = InMemoryEventBus()
    try:
        yield bus
    finally:
        pass  # InMemoryEventBus has no cleanup needed


def timing(func: Callable[[], Any]) -> tuple[Any, float]:
    """Execute a function and return result + elapsed time in seconds."""
    start = time.perf_counter()
    result = func()
    elapsed = time.perf_counter() - start
    return result, elapsed


async def async_timing(func: Callable[[], Coroutine[Any, Any, Any]]) -> tuple[Any, float]:
    """Execute an async function and return result + elapsed time in seconds."""
    start = time.perf_counter()
    result = await func()
    elapsed = time.perf_counter() - start
    return result, elapsed
