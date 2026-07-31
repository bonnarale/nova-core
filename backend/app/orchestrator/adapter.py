"""EventBusAdapter — bridges InMemoryEventBus to orchestrator's on/off/emit interface.

The orchestrator modules (TaskManager, Worker, Planner) expect a simple event bus
with on(event_type, handler) where handler receives (event_type, data). The system's
InMemoryEventBus uses subscribe(event_type, handler) where handler receives an Event
object. This adapter bridges the gap so existing orchestrator code stays unchanged.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from app.events.bus import InMemoryEventBus
from app.events.schemas import Event

logger = logging.getLogger(__name__)

# Type alias matching the orchestrator's handler signature: (event_type: str, data: dict)
OrchestratorHandler = Callable[[str, dict[str, Any]], Any]


class EventBusAdapter:
    """Bridges InMemoryEventBus to orchestrator's on/off/emit interface.

    Exposes the simple `on(event_type, handler)` / `off(event_type, handler)` /
    `async emit(event_type, data)` interface that TaskManager and Worker expect,
    while delegating to InMemoryEventBus's subscribe/unsubscribe/publish methods.

    The handler signature adaptation works as follows:
    - Orchestrator handlers receive `(event_type: str, data: dict)`
    - InMemoryEventBus handlers receive `(event: Event)`
    - This adapter wraps each orchestrator handler to convert the signature
    """

    def __init__(self, bus: InMemoryEventBus) -> None:
        self._bus = bus
        # Maps orchestrator handler -> subscription_id for unsubscription
        self._handler_subscriptions: dict[int, str] = {}

    def on(self, event_type: str, handler: OrchestratorHandler) -> None:
        """Register a handler for an event type.

        The handler will receive (event_type: str, data: dict) matching the
        orchestrator's EventBus interface. Internally subscribes to InMemoryEventBus
        with an adapter wrapper.
        """
        subscription_id_holder: dict[str, str] = {}

        async def _adapted_handler(event: Event) -> None:
            try:
                data = event.payload if isinstance(event.payload, dict) else {"payload": event.payload}
                # Add event metadata to the data dict for richer payloads
                data.setdefault("task_id", event.aggregate_id)
                result = handler(event.event_type, data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception(
                    "EventBusAdapter: handler %s failed for '%s'",
                    handler.__name__ if hasattr(handler, "__name__") else str(handler),
                    event_type,
                )

        # Use asyncio.run_coroutine_threadsafe-friendly pattern
        # InMemoryEventBus.subscribe is async, but we need a sync API here
        # We'll schedule the subscription and store the holder
        self._schedule_subscribe(event_type, _adapted_handler, subscription_id_holder)

        # Store mapping for unsubscription
        self._handler_subscriptions[id(handler)] = subscription_id_holder.get("id", "")

    def _schedule_subscribe(
        self,
        event_type: str,
        handler: Callable,
        holder: dict[str, str],
    ) -> None:
        """Schedule subscribe on the event bus loop (best-effort for sync callers)."""
        try:
            loop = asyncio.get_running_loop()
            # We're inside an async context — can't block, so we fire-and-forget
            # This works because the orchestrator calls on() during lifespan setup
            # when the event loop is running
            task = loop.create_task(self._do_subscribe(event_type, handler, holder))
            # Don't await — let it complete in the background
        except RuntimeError:
            # No running loop — store placeholder; caller must ensure bus is started
            logger.debug("EventBusAdapter: no running loop, subscription deferred")

    async def _do_subscribe(
        self,
        event_type: str,
        handler: Callable,
        holder: dict[str, str],
    ) -> None:
        sub_id = await self._bus.subscribe(event_type, handler)
        holder["id"] = sub_id
        self._handler_subscriptions[id(handler)] = sub_id

    def off(self, event_type: str, handler: OrchestratorHandler) -> None:
        """Remove a handler for an event type."""
        sub_id = self._handler_subscriptions.pop(id(handler), None)
        if sub_id:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._bus.unsubscribe(sub_id))
            except RuntimeError:
                pass

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit an event with the given type and data payload.

        Creates an Event object and publishes it via InMemoryEventBus.
        """
        event = Event(
            event_type=event_type,
            aggregate_id=data.get("task_id", ""),
            payload=data,
            source="orchestrator",
        )
        await self._bus.publish(event)

    async def subscribe(self, event_type: str, handler: Callable) -> str:
        """Direct subscribe to InMemoryEventBus (for handlers that accept Event objects).

        This is used by the new handler modules (RetryHandler, TimeoutHandler, etc.)
        that are designed to work with InMemoryEventBus natively.
        """
        return await self._bus.subscribe(event_type, handler)

    async def publish_delayed(self, event: Event, delay_seconds: int) -> str:
        """Delegate delayed publish to the underlying InMemoryEventBus."""
        return await self._bus.publish_delayed(event, delay_seconds)
