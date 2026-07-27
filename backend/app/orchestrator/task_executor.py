"""TaskExecutor — event-driven executor that orchestrates task lifecycle transitions.

Subscribes to task.created and task.queued events via InMemoryEventBus.
On task.created, checks dependencies and queues or holds the task.
On task.queued, dispatches to the assigned agent via AgentManager.
On agent result, transitions task to COMPLETED or FAILED.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.agents.agent_manager import AgentManager
from app.db.task_repository import TaskRepository
from app.events.bus import InMemoryEventBus
from app.events.schemas import Event
from app.orchestrator.task_manager import TaskManager

logger = logging.getLogger(__name__)


class TaskExecutor:
    """Event-driven task executor.

    Orchestrates task lifecycle transitions (CREATED → QUEUED → RUNNING → COMPLETED/FAILED)
    by subscribing to events on InMemoryEventBus and dispatching to agents via AgentManager.
    """

    def __init__(
        self,
        event_bus: InMemoryEventBus,
        task_manager: TaskManager,
        agent_manager: AgentManager,
    ) -> None:
        self._bus = event_bus
        self._task_manager = task_manager
        self._agent_manager = agent_manager
        self._subscriptions: list[str] = []

    async def start(self) -> None:
        """Subscribe to task.created and task.queued events."""
        sub1 = await self._bus.subscribe("task.created", self._handle_task_created)
        sub2 = await self._bus.subscribe("task.queued", self._handle_task_queued)
        self._subscriptions.extend([sub1, sub2])
        logger.info("TaskExecutor: subscribed to task.created, task.queued")

    async def stop(self) -> None:
        """Unsubscribe from all events."""
        for sub_id in self._subscriptions:
            await self._bus.unsubscribe(sub_id)
        self._subscriptions.clear()
        logger.info("TaskExecutor: unsubscribed from all events")

    async def _handle_task_created(self, event: Event) -> None:
        """Handle task.created event — check deps and queue if satisfied."""
        try:
            task_id_str = event.aggregate_id
            if not task_id_str:
                logger.debug("TaskExecutor: task.created with no aggregate_id, skipping")
                return

            task_id = UUID(task_id_str)
            task = await self._task_manager.get_task(task_id)
            if task is None:
                logger.warning("TaskExecutor: task %s not found", task_id_str)
                return

            # Check if dependencies are satisfied
            dependencies = task.get("dependencies", [])
            if dependencies:
                deps_met = await self._check_dependencies(task_id_str, dependencies)
                if not deps_met:
                    logger.info(
                        "TaskExecutor: task %s held in CREATED (deps unmet)",
                        task_id_str,
                    )
                    return

            # Dependencies satisfied (or none) — transition to QUEUED
            logger.info(
                "TaskExecutor: task %s deps met, transitioning to QUEUED",
                task_id_str,
            )
            await self._task_manager.transition_task(task_id, "QUEUED")

            # Emit task.queued event for dispatch
            await self._bus.publish(Event(
                event_type="task.queued",
                aggregate_id=task_id_str,
                payload={
                    "task_id": task_id_str,
                    "goal": task.get("goal", ""),
                    "assigned_agent": task.get("assigned_agent"),
                },
                source="task_executor",
            ))
        except Exception:
            logger.exception(
                "TaskExecutor: error handling task.created for %s",
                event.aggregate_id,
            )

    async def _handle_task_queued(self, event: Event) -> None:
        """Handle task.queued event — dispatch to agent."""
        try:
            task_id_str = event.aggregate_id
            if not task_id_str:
                logger.debug("TaskExecutor: task.queued with no aggregate_id, skipping")
                return

            payload = event.payload if isinstance(event.payload, dict) else {}
            task_id = UUID(task_id_str)
            task = await self._task_manager.get_task(task_id)
            if task is None:
                logger.warning("TaskExecutor: task %s not found", task_id_str)
                return

            assigned_agent = task.get("assigned_agent")
            if not assigned_agent:
                logger.warning(
                    "TaskExecutor: task %s has no assigned_agent, skipping dispatch",
                    task_id_str,
                )
                return

            # Transition to RUNNING
            logger.info(
                "TaskExecutor: task %s dispatching to agent %s",
                task_id_str,
                assigned_agent,
            )
            await self._task_manager.transition_task(task_id, "RUNNING")

            # Dispatch to agent
            await self._dispatch_to_agent(task_id_str, task)
        except Exception:
            logger.exception(
                "TaskExecutor: error handling task.queued for %s",
                event.aggregate_id,
            )

    async def _dispatch_to_agent(self, task_id_str: str, task: dict) -> None:
        """Dispatch task to assigned agent via AgentManager."""
        assigned_agent = task.get("assigned_agent")
        if not assigned_agent:
            logger.warning(
                "TaskExecutor: no agent assigned for task %s", task_id_str
            )
            return

        try:
            result = await self._agent_manager.dispatch(
                agent_id=assigned_agent,
                task=task.get("goal", ""),
                context={
                    "task_id": task_id_str,
                    "task": task,
                },
            )
            await self._handle_agent_result(task_id_str, result or {}, task)
        except Exception as exc:
            logger.exception(
                "TaskExecutor: agent %s failed for task %s",
                assigned_agent,
                task_id_str,
            )
            await self._handle_agent_failure(task_id_str, str(exc), task)

    async def _handle_agent_result(
        self, task_id_str: str, result: dict, task: dict
    ) -> None:
        """Process agent result — transition to COMPLETED or FAILED."""
        task_id = UUID(task_id_str)
        status = result.get("status", "success")

        if status == "success" or status == "completed":
            logger.info("TaskExecutor: task %s completed successfully", task_id_str)
            await self._task_manager.transition_task(
                task_id, "COMPLETED", artifacts=result
            )
            await self._bus.publish(Event(
                event_type="task.completed",
                aggregate_id=task_id_str,
                payload={
                    "task_id": task_id_str,
                    "result": result,
                },
                source="task_executor",
            ))
        else:
            error_msg = result.get("error", "Agent returned non-success status")
            await self._handle_agent_failure(task_id_str, error_msg, task)

    async def _handle_agent_failure(
        self, task_id_str: str, error: str, task: dict
    ) -> None:
        """Handle agent failure — transition to FAILED."""
        task_id = UUID(task_id_str)
        logger.error("TaskExecutor: task %s failed: %s", task_id_str, error)

        await self._task_manager.transition_task(
            task_id, "FAILED", error=error
        )
        await self._bus.publish(Event(
            event_type="task.failed",
            aggregate_id=task_id_str,
            payload={
                "task_id": task_id_str,
                "error": error,
                "failure_reason": "agent_error",
            },
            source="task_executor",
        ))

    async def _check_dependencies(
        self, task_id_str: str, dependencies: list[str]
    ) -> bool:
        """Check if all dependencies are completed."""
        for dep_id_str in dependencies:
            try:
                dep_id = UUID(dep_id_str)
                dep_task = await self._task_manager.get_task(dep_id)
                if dep_task is None or dep_task.get("status") != "COMPLETED":
                    return False
            except Exception:
                return False
        return True
