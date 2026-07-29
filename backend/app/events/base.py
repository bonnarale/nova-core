"""Event system abstractions — ABCs for the event-driven architecture."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.events.schemas import Event, EventFilter, ReplayRequest, ReplayResult


class EventBus(ABC):
    """Abstract event bus — publish, subscribe, and manage events."""

    @abstractmethod
    async def publish(self, event: Event) -> Event:
        ...

    @abstractmethod
    async def broadcast(self, event: Event) -> Event:
        ...

    @abstractmethod
    async def subscribe(
        self,
        event_type: str,
        handler: Any,
        filter_expr: EventFilter | None = None,
    ) -> str:
        ...

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        ...

    @abstractmethod
    async def request(self, event: Event, timeout: float = 30.0) -> Event:
        ...

    @abstractmethod
    async def reply(self, request_event: Event, reply_event: Event) -> Event:
        ...

    @abstractmethod
    async def publish_delayed(self, event: Event, delay_seconds: int) -> str:
        ...

    @abstractmethod
    async def schedule_event(
        self,
        event: Event,
        interval_seconds: int | None = None,
        max_runs: int | None = None,
    ) -> str:
        ...

    @abstractmethod
    async def replay(self, request: ReplayRequest) -> ReplayResult:
        ...

    @abstractmethod
    async def get_event(self, event_id: str) -> Event | None:
        ...

    @abstractmethod
    async def list_events(
        self,
        filter_expr: EventFilter | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Event]:
        ...

    @abstractmethod
    async def get_statistics(self) -> dict[str, Any]:
        ...

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        ...


class EventPublisher(ABC):
    """Publishes events to the bus."""

    @abstractmethod
    async def publish(self, event: Event) -> Event:
        ...

    @abstractmethod
    async def publish_many(self, events: list[Event]) -> list[Event]:
        ...


class EventSubscriber(ABC):
    """Subscribes to events from the bus."""

    @abstractmethod
    async def subscribe(
        self,
        event_type: str,
        handler: Any,
        filter_expr: EventFilter | None = None,
    ) -> str:
        ...

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        ...

    @abstractmethod
    async def get_subscriptions(self) -> list[dict[str, Any]]:
        ...


class EventHandler(ABC):
    """Handles a specific type of event."""

    @property
    @abstractmethod
    def event_type(self) -> str:
        ...

    @abstractmethod
    async def handle(self, event: Event) -> Event | None:
        ...

    @abstractmethod
    async def can_handle(self, event: Event) -> bool:
        ...


class EventMiddleware(ABC):
    """Middleware that intercepts events before/after dispatch."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def priority(self) -> int:
        ...

    @abstractmethod
    async def before_publish(self, event: Event) -> Event:
        ...

    @abstractmethod
    async def after_publish(self, event: Event, result: Event | None = None) -> None:
        ...

    @abstractmethod
    async def on_error(self, event: Event, error: Exception) -> bool:
        ...


class EventPersistence(ABC):
    """Persists events for replay and audit."""

    @abstractmethod
    async def store(self, event: Event) -> None:
        ...

    @abstractmethod
    async def get(self, event_id: str) -> Event | None:
        ...

    @abstractmethod
    async def list_events(
        self,
        filter_expr: EventFilter | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Event]:
        ...

    @abstractmethod
    async def count(self, filter_expr: EventFilter | None = None) -> int:
        ...

    @abstractmethod
    async def delete(self, event_id: str) -> bool:
        ...

    @abstractmethod
    async def clear(self) -> int:
        ...


class EventSerializer(ABC):
    """Serializes and deserializes events."""

    @abstractmethod
    def serialize(self, event: Event) -> str:
        ...

    @abstractmethod
    def deserialize(self, data: str) -> Event:
        ...

    @abstractmethod
    def serialize_bytes(self, event: Event) -> bytes:
        ...

    @abstractmethod
    def deserialize_bytes(self, data: bytes) -> Event:
        ...
