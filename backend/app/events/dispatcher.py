"""Event dispatcher — sync, async, parallel, ordered, and priority dispatch."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.events.schemas import Event, EventPriority, EventStatus

logger = logging.getLogger(__name__)

Handler = Any


class EventDispatcher:
    """Dispatches events to handlers using various strategies."""

    def __init__(self, max_concurrency: int = 10) -> None:
        self._max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._priority_queue: asyncio.PriorityQueue[tuple[int, Event]] = asyncio.PriorityQueue()

    async def dispatch_sync(self, event: Event, handlers: list[Handler]) -> Event:
        event.status = EventStatus.PROCESSING
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                event.status = EventStatus.FAILED
                logger.error("Sync dispatch failed for %s: %s", event.event_id, e)
                raise
        event.status = EventStatus.COMPLETED
        return event

    async def dispatch_async(self, event: Event, handlers: list[Handler]) -> Event:
        event.status = EventStatus.PROCESSING
        tasks = []
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                tasks.append(handler(event))
            else:
                loop = asyncio.get_event_loop()
                tasks.append(loop.run_in_executor(None, handler, event))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                event.status = EventStatus.FAILED
                logger.error("Async dispatch failed for %s: %s", event.event_id, result)
                raise result
        event.status = EventStatus.COMPLETED
        return event

    async def dispatch_parallel(self, event: Event, handlers: list[Handler]) -> Event:
        event.status = EventStatus.PROCESSING

        async def _limited(h: Handler) -> Any:
            async with self._semaphore:
                if asyncio.iscoroutinefunction(h):
                    return await h(event)
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, h, event)

        tasks = [_limited(h) for h in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                event.status = EventStatus.FAILED
                logger.error("Parallel dispatch failed for %s: %s", event.event_id, result)
                raise result
        event.status = EventStatus.COMPLETED
        return event

    async def dispatch_ordered(self, event: Event, handlers: list[Handler]) -> Event:
        event.status = EventStatus.PROCESSING
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                event.status = EventStatus.FAILED
                logger.error("Ordered dispatch failed for %s: %s", event.event_id, e)
                raise
        event.status = EventStatus.COMPLETED
        return event

    async def dispatch_priority(self, event: Event, handlers: list[Handler]) -> Event:
        priority_map = {
            EventPriority.CRITICAL: 0,
            EventPriority.HIGH: 1,
            EventPriority.NORMAL: 2,
            EventPriority.LOW: 3,
        }
        priority = priority_map.get(event.priority, 2)
        await self._priority_queue.put((priority, event))
        return await self._process_priority_queue(handlers)

    async def _process_priority_queue(self, handlers: list[Handler]) -> Event:
        processed_events: list[Event] = []
        while not self._priority_queue.empty():
            priority, event = await self._priority_queue.get()
            event.status = EventStatus.PROCESSING
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    event.status = EventStatus.FAILED
                    logger.error("Priority dispatch failed for %s: %s", event.event_id, e)
                    raise
            event.status = EventStatus.COMPLETED
            processed_events.append(event)
        return processed_events[-1] if processed_events else Event()

    @property
    def queue_size(self) -> int:
        return self._priority_queue.qsize()

    @property
    def max_concurrency(self) -> int:
        return self._max_concurrency
