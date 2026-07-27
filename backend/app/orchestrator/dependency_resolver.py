"""DependencyResolver — gates task start on prerequisite completion.

Subscribes to task.created and task.completed events via InMemoryEventBus.
On creation, checks if all dependencies are COMPLETED; if not, the task
stays in CREATED state. On completion of any task, re-evaluates all
CREATED tasks to see if their dependencies are now satisfied.

Dependencies are stored as a list of task ID strings in the task's
`dependencies` field. A task can only be queued when ALL dependencies
are in COMPLETED status.
"""

from __future__ import annotations

import logging
from typing import Any

from app.db.task_repository import TaskRepository
from app.events.bus import InMemoryEventBus
from app.events.schemas import Event

logger = logging.getLogger(__name__)


class DependencyResolver:
    """Resolves task dependencies and gates task queuing.

    When a task is created with dependencies, checks if all are satisfied.
    When any task completes, re-evaluates held tasks.
    """

    def __init__(self, bus: InMemoryEventBus, task_repo: TaskRepository) -> None:
        self._bus = bus
        self._repo = task_repo

    async def subscribe_to(self) -> None:
        """Register as event listener on the bus."""
        await self._bus.subscribe("task.created", self._handle_created)
        await self._bus.subscribe("task.completed", self._handle_completed)
        logger.info("DependencyResolver: subscribed to task.created, task.completed")

    async def _handle_created(self, event: Event) -> None:
        """Handle task.created event — check dependencies before queuing."""
        try:
            await self.check_dependencies(event)
        except Exception:
            logger.exception(
                "DependencyResolver: error checking deps for %s", event.aggregate_id
            )

    async def _handle_completed(self, event: Event) -> None:
        """Handle task.completed event — re-evaluate CREATED tasks."""
        try:
            await self.re_evaluate_created()
        except Exception:
            logger.exception(
                "DependencyResolver: error re-evaluating tasks after %s completed",
                event.aggregate_id,
            )

    async def has_cycle(self, task_id_str: str, dependencies: list[str]) -> bool:
        """Detect if adding these dependencies would create a cycle.

        Uses DFS traversal: if any dependency (or its transitive dependencies)
        eventually points back to task_id_str, it's a cycle.
        """
        from uuid import UUID

        visited: set[str] = set()
        stack = list(dependencies)

        while stack:
            dep_id_str = stack.pop()
            if dep_id_str == task_id_str:
                return True  # Cycle detected
            if dep_id_str in visited:
                continue
            visited.add(dep_id_str)
            try:
                dep_id = UUID(dep_id_str) if isinstance(dep_id_str, str) else dep_id_str
                dep_task = await self._repo.get(dep_id)
                if dep_task and dep_task.dependencies:
                    stack.extend(dep_task.dependencies)
            except Exception:
                pass

        return False

    async def check_dependencies(self, event: Event) -> bool:
        """Check if a task's dependencies are all satisfied.

        Args:
            event: The task.created event

        Returns:
            True if all dependencies are met (or no dependencies), False otherwise
        """
        task_id_str = event.aggregate_id
        if not task_id_str:
            return True

        from uuid import UUID

        task_id = UUID(task_id_str)
        task = await self._repo.get(task_id)
        if task is None:
            return True

        dependencies = task.dependencies or []
        if not dependencies:
            # No dependencies — task can proceed
            logger.debug("DependencyResolver: task %s has no dependencies", task_id_str)
            return True

        # Check for circular dependencies
        if await self.has_cycle(task_id_str, dependencies):
            logger.warning(
                "DependencyResolver: task %s has circular dependencies: %s",
                task_id_str, dependencies,
            )
            await self._bus.publish(Event(
                event_type="task.dependency_cycle",
                aggregate_id=task_id_str,
                payload={
                    "task_id": task_id_str,
                    "dependencies": dependencies,
                },
                source="dependency_resolver",
            ))
            return False

        # Check each dependency
        unmet = []
        for dep_id_str in dependencies:
            try:
                dep_id = UUID(dep_id_str) if isinstance(dep_id_str, str) else dep_id_str
                dep_task = await self._repo.get(dep_id)
                if dep_task is None:
                    unmet.append(dep_id_str)
                    continue
                if dep_task.status != "COMPLETED":
                    unmet.append(dep_id_str)
            except Exception:
                unmet.append(dep_id_str)

        if unmet:
            logger.info(
                "DependencyResolver: task %s has unmet dependencies: %s",
                task_id_str, unmet,
            )
            # Emit dependency_unmet event
            await self._bus.publish(Event(
                event_type="task.dependency_unmet",
                aggregate_id=task_id_str,
                payload={
                    "task_id": task_id_str,
                    "unmet_dependencies": unmet,
                    "total_dependencies": len(dependencies),
                },
                source="dependency_resolver",
            ))
            return False

        logger.info(
            "DependencyResolver: task %s all dependencies met", task_id_str
        )

        # Emit task.queued event when dependencies are satisfied
        await self._bus.publish(Event(
            event_type="task.queued",
            aggregate_id=task_id_str,
            payload={
                "task_id": task_id_str,
                "deps_resolved": True,
            },
            source="dependency_resolver",
        ))

        return True

    async def re_evaluate_created(self) -> None:
        """Re-evaluate all CREATED tasks with dependencies.

        When a task completes, check if any CREATED tasks now have all
        dependencies satisfied and should be queued.
        """
        # Get all CREATED tasks
        created_tasks = await self._repo.list(status="CREATED", limit=100)

        for task in created_tasks:
            dependencies = task.dependencies or []
            if not dependencies:
                continue

            # Check if all dependencies are now completed
            all_met = True
            for dep_id_str in dependencies:
                try:
                    from uuid import UUID
                    dep_id = UUID(dep_id_str) if isinstance(dep_id_str, str) else dep_id_str
                    dep_task = await self._repo.get(dep_id)
                    if dep_task is None or dep_task.status != "COMPLETED":
                        all_met = False
                        break
                except Exception:
                    all_met = False
                    break

            if all_met:
                task_id_str = str(task.id)
                logger.info(
                    "DependencyResolver: task %s dependencies now met, re-queuing",
                    task_id_str,
                )
                # Emit task.created with retry flag to trigger queuing
                await self._bus.publish(Event(
                    event_type="task.created",
                    aggregate_id=task_id_str,
                    payload={
                        "task_id": task_id_str,
                        "deps_resolved": True,
                    },
                    source="dependency_resolver",
                ))
