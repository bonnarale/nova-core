"""Workflow dispatcher — dispatches workflow nodes to appropriate handlers."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.workflows.node import NodeType, NodeStatus, WorkflowNode
from app.workflows.context import WorkflowContext

logger = logging.getLogger(__name__)

NodeHandler = Any


class WorkflowDispatcher:
    """Dispatches node execution to registered handlers based on node type."""

    def __init__(self, max_concurrency: int = 10) -> None:
        self._handlers: dict[str, NodeHandler] = {}
        self._type_handlers: dict[NodeType, NodeHandler] = {}
        self._max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._active_count = 0
        self._running = False

    @property
    def active_count(self) -> int:
        return self._active_count

    @property
    def is_running(self) -> bool:
        return self._running

    def register_handler(self, name: str, handler: NodeHandler) -> None:
        self._handlers[name] = handler

    def register_type_handler(self, node_type: NodeType, handler: NodeHandler) -> None:
        self._type_handlers[node_type] = handler

    def get_handler(self, name: str) -> NodeHandler | None:
        return self._handlers.get(name)

    def get_type_handler(self, node_type: NodeType) -> NodeHandler | None:
        return self._type_handlers.get(node_type)

    async def start(self) -> None:
        self._running = True
        logger.info("WorkflowDispatcher started (max_concurrency=%d)", self._max_concurrency)

    async def stop(self) -> None:
        self._running = False
        logger.info("WorkflowDispatcher stopped")

    async def dispatch(self, node: WorkflowNode, context: WorkflowContext) -> Any:
        handler = self._handlers.get(node.handler) or self._type_handlers.get(node.node_type)
        if handler is None:
            logger.warning("No handler for node %s (type=%s, handler=%s)", node.node_id, node.node_type.value, node.handler)
            return {"status": "skipped", "reason": "no_handler"}

        async with self._semaphore:
            self._active_count += 1
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(node, context)
                else:
                    result = handler(node, context)
                return result
            finally:
                self._active_count -= 1

    async def dispatch_batch(self, nodes: list[WorkflowNode], context: WorkflowContext) -> list[Any]:
        tasks = [self.dispatch(node, context) for node in nodes]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def list_handlers(self) -> list[str]:
        return list(self._handlers.keys())

    def list_type_handlers(self) -> list[str]:
        return [t.value for t in self._type_handlers.keys()]
