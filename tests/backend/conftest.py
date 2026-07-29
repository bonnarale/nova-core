"""NOVA CORE — Central pytest configuration and shared fixtures.

Chapter 29: Testing Infrastructure

Provides session-scoped and function-scoped fixtures for every subsystem,
custom markers, async test support, and standardized configuration.
"""

from __future__ import annotations

import asyncio
import gc
import logging
import time
import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pytest markers
# ---------------------------------------------------------------------------

def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers for NOVA CORE test suites."""
    config.addinivalue_line("markers", "unit: Pure unit tests (no I/O)")
    config.addinivalue_line("markers", "integration: Integration tests (multi-component)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (full pipeline)")
    config.addinivalue_line("markers", "regression: Regression tests")
    config.addinivalue_line("markers", "performance: Performance benchmarks")
    config.addinivalue_line("markers", "load: Load tests")
    config.addinivalue_line("markers", "stress: Stress tests")
    config.addinivalue_line("markers", "concurrency: Concurrency tests")
    config.addinivalue_line("markers", "slow: Slow tests (>1s)")
    config.addinivalue_line("markers", "security: Security tests")


# ---------------------------------------------------------------------------
# Event loop fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop]:
    """Create a session-scoped event loop for all async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Time fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


@pytest.fixture
def frozen_time() -> Generator[float]:
    """Provide a deterministic time value for testing."""
    return 1700000000.0


# ---------------------------------------------------------------------------
# ID / identifier fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_id() -> str:
    """Return a deterministic UUID string for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_ids() -> list[str]:
    """Return 5 deterministic UUID strings for testing."""
    return [str(uuid.uuid4()) for _ in range(5)]


# ---------------------------------------------------------------------------
# Generic data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_text() -> str:
    """Return sample text content for testing."""
    return "The quick brown fox jumps over the lazy dog. This is a test sentence."


@pytest.fixture
def sample_embedding() -> list[float]:
    """Return a sample 4-dimensional embedding vector."""
    return [0.1, 0.2, 0.3, 0.4]


@pytest.fixture
def sample_embeddings() -> list[list[float]]:
    """Return 5 sample 4-dimensional embedding vectors."""
    return [
        [0.1, 0.2, 0.3, 0.4],
        [0.4, 0.3, 0.2, 0.1],
        [0.5, 0.5, 0.0, 0.0],
        [0.0, 0.0, 0.5, 0.5],
        [0.25, 0.25, 0.25, 0.25],
    ]


@pytest.fixture
def sample_metadata() -> dict[str, Any]:
    """Return sample metadata dictionary."""
    return {
        "source": "test",
        "version": "1.0",
        "tags": ["unit", "test"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Mock / stub fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm_provider() -> MagicMock:
    """Return a mock LLM provider with async generate."""
    mock = MagicMock()
    mock.generate = AsyncMock(return_value="Test response from LLM")
    mock.chat = AsyncMock(return_value="Test chat response")
    mock.embed = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4])
    return mock


@pytest.fixture
def mock_embedding_provider() -> MagicMock:
    """Return a mock embedding provider."""
    mock = MagicMock()
    mock.embed = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4])
    mock.embed_batch = AsyncMock(
        return_value=[[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]]
    )
    return mock


@pytest.fixture
def mock_vector_store() -> MagicMock:
    """Return a mock vector store."""
    mock = MagicMock()
    mock.add = AsyncMock(return_value=True)
    mock.search = AsyncMock(return_value=[])
    mock.delete = AsyncMock(return_value=True)
    mock.count = AsyncMock(return_value=0)
    return mock


@pytest.fixture
def mock_database() -> MagicMock:
    """Return a mock database session."""
    mock = MagicMock()
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_event_bus() -> MagicMock:
    """Return a mock event bus."""
    mock = MagicMock()
    mock.publish = AsyncMock()
    mock.subscribe = AsyncMock()
    mock.unsubscribe = AsyncMock()
    mock.get_events = MagicMock(return_value=[])
    return mock


@pytest.fixture
def mock_external_api() -> MagicMock:
    """Return a mock external API client."""
    mock = MagicMock()
    mock.get = AsyncMock(return_value={"status": "ok", "data": {}})
    mock.post = AsyncMock(return_value={"status": "created", "id": "123"})
    mock.put = AsyncMock(return_value={"status": "updated"})
    mock.delete = AsyncMock(return_value={"status": "deleted"})
    return mock


@pytest.fixture
def mock_scheduler() -> MagicMock:
    """Return a mock scheduler."""
    mock = MagicMock()
    mock.schedule = AsyncMock(return_value="job-123")
    mock.cancel = AsyncMock(return_value=True)
    mock.get_jobs = MagicMock(return_value=[])
    return mock


@pytest.fixture
def mock_tool() -> MagicMock:
    """Return a mock tool."""
    mock = MagicMock()
    mock.name = "test_tool"
    mock.description = "A test tool"
    mock.execute = AsyncMock(return_value={"result": "success"})
    return mock


@pytest.fixture
def mock_plugin() -> MagicMock:
    """Return a mock plugin."""
    mock = MagicMock()
    mock.name = "test_plugin"
    mock.version = "1.0.0"
    mock.initialize = AsyncMock()
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    mock.health_check = AsyncMock(return_value=True)
    return mock


# ---------------------------------------------------------------------------
# App-state fixtures (for API route tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_app_state() -> MagicMock:
    """Return a mock FastAPI app.state with all subsystem references."""
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
    return state


# ---------------------------------------------------------------------------
# Async helper fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def async_context() -> AsyncGenerator[dict[str, Any], None]:
    """Provide an async context dict for multi-subsystem tests."""
    ctx: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc),
        "request_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4()),
    }
    yield ctx
    ctx.clear()


# ---------------------------------------------------------------------------
# Cleanup fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _cleanup() -> Generator[None, None, None]:
    """Auto-cleanup after each test to prevent cross-test contamination."""
    yield
    gc.collect()
