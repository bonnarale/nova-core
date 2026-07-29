from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock


class MockLLMProvider:
    """Mock LLM provider for testing."""

    def __init__(self) -> None:
        self._mock = MagicMock()
        self._mock.generate = AsyncMock(return_value="Test LLM response")
        self._mock.chat = AsyncMock(return_value="Test chat response")
        self._mock.embed = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4])
        self._mock.embed_batch = AsyncMock(return_value=[[0.1, 0.2, 0.3, 0.4]])

    @property
    def mock(self) -> MagicMock:
        return self._mock

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        return await self._mock.generate(prompt, **kwargs)

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        return await self._mock.chat(messages, **kwargs)

    async def embed(self, text: str) -> list[float]:
        return await self._mock.embed(text)


class MockEmbeddingProvider:
    """Mock embedding provider for testing."""

    def __init__(self, dimension: int = 4) -> None:
        self._mock = MagicMock()
        self._dimension = dimension
        self._mock.embed = AsyncMock(return_value=[0.1] * dimension)
        self._mock.embed_batch = AsyncMock(
            return_value=[[0.1] * dimension, [0.2] * dimension]
        )

    @property
    def mock(self) -> MagicMock:
        return self._mock

    async def embed(self, text: str) -> list[float]:
        return await self._mock.embed(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return await self._mock.embed_batch(texts)


class MockVectorStore:
    """Mock vector store for testing."""

    def __init__(self) -> None:
        self._mock = MagicMock()
        self._mock.add = AsyncMock(return_value=True)
        self._mock.search = AsyncMock(return_value=[])
        self._mock.delete = AsyncMock(return_value=True)
        self._mock.count = AsyncMock(return_value=0)
        self._mock.update = AsyncMock(return_value=True)
        self._mock.get = AsyncMock(return_value=None)

    @property
    def mock(self) -> MagicMock:
        return self._mock

    async def add(
        self, id: str, embedding: list[float], metadata: dict[str, Any] | None = None
    ) -> bool:
        return await self._mock.add(id, embedding, metadata)

    async def search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[dict[str, Any]]:
        return await self._mock.search(query_embedding, top_k)

    async def delete(self, id: str) -> bool:
        return await self._mock.delete(id)

    async def count(self) -> int:
        return await self._mock.count()


class MockDatabase:
    """Mock database session for testing."""

    def __init__(self) -> None:
        self._mock = MagicMock()
        self._mock.execute = AsyncMock()
        self._mock.commit = AsyncMock()
        self._mock.rollback = AsyncMock()
        self._mock.close = AsyncMock()
        self._mock.add = MagicMock()
        self._mock.get = AsyncMock(return_value=None)
        self._mock.query = MagicMock()

    @property
    def mock(self) -> MagicMock:
        return self._mock

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        return await self._mock.execute(*args, **kwargs)

    async def commit(self) -> None:
        await self._mock.commit()

    async def rollback(self) -> None:
        await self._mock.rollback()


class MockEventBus:
    """Mock event bus for testing."""

    def __init__(self) -> None:
        self._mock = MagicMock()
        self._published_events: list[dict[str, Any]] = []
        self._subscriptions: dict[str, list[Any]] = {}
        self._mock.publish = AsyncMock(side_effect=self._on_publish)
        self._mock.subscribe = MagicMock(side_effect=self._on_subscribe)
        self._mock.unsubscribe = MagicMock(side_effect=self._on_unsubscribe)

    def _on_publish(self, event: Any) -> Any:
        self._published_events.append(event)
        return None

    def _on_subscribe(self, event_type: str, handler: Any) -> None:
        self._subscriptions.setdefault(event_type, []).append(handler)

    def _on_unsubscribe(self, event_type: str, handler: Any) -> None:
        if event_type in self._subscriptions:
            self._subscriptions[event_type] = [
                h for h in self._subscriptions[event_type] if h is not handler
            ]

    @property
    def mock(self) -> MagicMock:
        return self._mock

    @property
    def published_events(self) -> list[dict[str, Any]]:
        return self._published_events

    async def publish(self, event: Any) -> None:
        await self._mock.publish(event)


class MockExternalAPI:
    """Mock external API client for testing."""

    def __init__(self, base_url: str = "https://api.test.com") -> None:
        self._mock = MagicMock()
        self._base_url = base_url
        self._mock.get = AsyncMock(return_value={"status": "ok", "data": {}})
        self._mock.post = AsyncMock(return_value={"status": "created", "id": "123"})
        self._mock.put = AsyncMock(return_value={"status": "updated"})
        self._mock.delete = AsyncMock(return_value={"status": "deleted"})

    @property
    def mock(self) -> MagicMock:
        return self._mock

    async def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return await self._mock.get(path, **kwargs)

    async def post(self, path: str, data: Any = None, **kwargs: Any) -> dict[str, Any]:
        return await self._mock.post(path, data, **kwargs)

    async def put(self, path: str, data: Any = None, **kwargs: Any) -> dict[str, Any]:
        return await self._mock.put(path, data, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return await self._mock.delete(path, **kwargs)


class MockScheduler:
    """Mock scheduler for testing."""

    def __init__(self) -> None:
        self._mock = MagicMock()
        self._jobs: list[dict[str, Any]] = []
        self._mock.schedule = AsyncMock(side_effect=self._on_schedule)
        self._mock.cancel = AsyncMock(side_effect=self._on_cancel)
        self._mock.get_jobs = MagicMock(return_value=[])

    def _on_schedule(self, **kwargs: Any) -> str:
        job_id = f"job_{len(self._jobs)}"
        self._jobs.append({"id": job_id, **kwargs})
        return job_id

    def _on_cancel(self, job_id: str) -> bool:
        self._jobs = [j for j in self._jobs if j.get("id") != job_id]
        return True

    @property
    def mock(self) -> MagicMock:
        return self._mock

    async def schedule(self, **kwargs: Any) -> str:
        return await self._mock.schedule(**kwargs)

    async def cancel(self, job_id: str) -> bool:
        return await self._mock.cancel(job_id)


class MockTool:
    """Mock tool for testing."""

    def __init__(self, name: str = "test_tool", description: str = "A test tool") -> None:
        self._mock = MagicMock()
        self._name = name
        self._description = description
        self._mock.execute = AsyncMock(return_value={"result": "success"})
        self._mock.validate = MagicMock(return_value=True)

    @property
    def mock(self) -> MagicMock:
        return self._mock

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        return await self._mock.execute(**kwargs)


class MockPlugin:
    """Mock plugin for testing."""

    def __init__(self, name: str = "test_plugin", version: str = "1.0.0") -> None:
        self._mock = MagicMock()
        self._name = name
        self._version = version
        self._mock.initialize = AsyncMock()
        self._mock.start = AsyncMock()
        self._mock.stop = AsyncMock()
        self._mock.health_check = AsyncMock(return_value=True)

    @property
    def mock(self) -> MagicMock:
        return self._mock

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    async def initialize(self) -> None:
        await self._mock.initialize()

    async def start(self) -> None:
        await self._mock.start()

    async def stop(self) -> None:
        await self._mock.stop()

    async def health_check(self) -> bool:
        return await self._mock.health_check()
