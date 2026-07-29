"""Event types and event bus for workflow lifecycle events."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable
from uuid import uuid4

from app.workflows.models import WorkflowEvent, WorkflowEventType

logger = logging.getLogger(__name__)

EventHandler = Callable[[WorkflowEvent], Any]


class WorkflowEventBus:
    """Simple in-memory event bus for workflow lifecycle events."""

    def __init__(self) -> None:
        self._subscribers: dict[WorkflowEventType, list[EventHandler]] = {}
        self._events: list[WorkflowEvent] = []
        # SSE subscriber queues: execution_id -> list of asyncio.Queue
        self._sse_queues: dict[str, list[asyncio.Queue]] = {}

    def subscribe(self, event_type: WorkflowEventType, handler: EventHandler) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: WorkflowEventType, handler: EventHandler) -> None:
        handlers = self._subscribers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def publish(
        self,
        event_type: WorkflowEventType,
        execution_id: str,
        step_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> WorkflowEvent:
        event = WorkflowEvent(
            id=str(uuid4()),
            execution_id=execution_id,
            event_type=event_type,
            step_id=step_id,
            payload=payload or {},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._events.append(event)

        # Push to SSE subscriber queues
        for q in self._sse_queues.get(execution_id, []):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("SSE queue full for execution %s, dropping event", execution_id)

        for handler in self._subscribers.get(event_type, []):
            try:
                handler(event)
            except Exception:
                logger.exception("Event handler failed for %s", event_type.value)

        return event

    def subscribe_sse(self, execution_id: str) -> asyncio.Queue:
        """Subscribe to SSE events for a given execution. Returns a Queue."""
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._sse_queues.setdefault(execution_id, []).append(q)
        return q

    def unsubscribe_sse(self, execution_id: str, q: asyncio.Queue) -> None:
        """Remove an SSE subscriber queue."""
        queues = self._sse_queues.get(execution_id, [])
        if q in queues:
            queues.remove(q)
        if not queues and execution_id in self._sse_queues:
            del self._sse_queues[execution_id]

    async def sse_stream(self, execution_id: str) -> AsyncIterator[str]:
        """Async generator that yields SSE-formatted event strings."""
        q = self.subscribe_sse(execution_id)
        try:
            # Send already-existing events first
            for existing in self.get_events(execution_id):
                data = json.dumps(existing.to_dict())
                yield f"data: {data}\n\n"
            # Then stream new events
            while True:
                try:
                    event: WorkflowEvent = await asyncio.wait_for(q.get(), timeout=30.0)
                    data = json.dumps(event.to_dict())
                    yield f"data: {data}\n\n"
                    # End stream on terminal events
                    if event.event_type in (
                        WorkflowEventType.COMPLETED,
                        WorkflowEventType.FAILED,
                        WorkflowEventType.CANCELLED,
                        WorkflowEventType.ROLLED_BACK,
                    ):
                        break
                except asyncio.TimeoutError:
                    # Send keepalive comment
                    yield ": keepalive\n\n"
        finally:
            self.unsubscribe_sse(execution_id, q)

    def get_events(self, execution_id: str | None = None) -> list[WorkflowEvent]:
        if execution_id:
            return [e for e in self._events if e.execution_id == execution_id]
        return list(self._events)

    def clear(self) -> None:
        self._events.clear()
