"""Task routing for kernel operations."""

import logging
from typing import Any, Optional

from app.kernel.context import ExecutionContext
from app.kernel.events import EventType, KernelEvent, emit
from app.kernel.registry import get_agent, get_tool

logger = logging.getLogger(__name__)


async def route_task(
    task: str,
    agent_id: Optional[str] = None,
    tool_id: Optional[str] = None,
    context: Optional[ExecutionContext] = None,
) -> dict[str, Any]:
    """Route a task to an agent or tool.

    Args:
        task: The task description or input.
        agent_id: Optional agent ID to route to.
        tool_id: Optional tool ID to route to.
        context: Optional execution context.

    Returns:
        Task execution result.

    Raises:
        ValueError: If neither agent_id nor tool_id is provided.
    """
    if agent_id is None and tool_id is None:
        raise ValueError("Either agent_id or tool_id must be provided")

    task_id = context.task_id if context else None
    session_id = context.session_id if context else None

    if agent_id:
        agent = get_agent(agent_id)
        if agent is None:
            logger.error("Agent not found: %s", agent_id)
            raise ValueError(f"Agent not found: {agent_id}")

        logger.info("Routing task to agent: %s", agent_id)
        emit(
            KernelEvent.create(
                event_type=EventType.TASK_STARTED,
                session_id=session_id,
                task_id=task_id,
                agent_id=agent_id,
                payload={"task": task},
            )
        )

        try:
            result = await agent.execute(task, context.metadata if context else {})
            emit(
                KernelEvent.create(
                    event_type=EventType.TASK_COMPLETED,
                    session_id=session_id,
                    task_id=task_id,
                    agent_id=agent_id,
                    payload={"result": result},
                )
            )
            return result
        except Exception as e:
            logger.exception("Task failed for agent: %s", agent_id)
            emit(
                KernelEvent.create(
                    event_type=EventType.TASK_FAILED,
                    session_id=session_id,
                    task_id=task_id,
                    agent_id=agent_id,
                    payload={"error": str(e)},
                )
            )
            raise

    if tool_id:
        tool = get_tool(tool_id)
        if tool is None:
            logger.error("Tool not found: %s", tool_id)
            raise ValueError(f"Tool not found: {tool_id}")

        logger.info("Routing task to tool: %s", tool_id)
        emit(
            KernelEvent.create(
                event_type=EventType.TASK_STARTED,
                session_id=session_id,
                task_id=task_id,
                payload={"task": task, "tool_id": tool_id},
            )
        )

        try:
            result = await tool.run({"task": task})
            emit(
                KernelEvent.create(
                    event_type=EventType.TASK_COMPLETED,
                    session_id=session_id,
                    task_id=task_id,
                    payload={"result": result},
                )
            )
            return result
        except Exception as e:
            logger.exception("Task failed for tool: %s", tool_id)
            emit(
                KernelEvent.create(
                    event_type=EventType.TASK_FAILED,
                    session_id=session_id,
                    task_id=task_id,
                    payload={"error": str(e)},
                )
            )
            raise

    return {}