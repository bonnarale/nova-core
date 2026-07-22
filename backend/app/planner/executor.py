"""StepExecutor — executes individual plan steps via Agent Manager."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from app.planner.plan import Step, StepStatus, ToolCall

logger = logging.getLogger(__name__)


class StepExecutor(ABC):
    """Abstract strategy for executing a single plan Step."""

    @abstractmethod
    async def execute(self, step: Step, context: dict[str, Any] | None = None) -> Step:
        """Execute *step* and return it with updated status/result/error."""
        ...


class AgentStepExecutor(StepExecutor):
    """Executes steps by dispatching to the appropriate agent.

    Delegates tool calls to the Agent Manager's dispatch mechanism.
    """

    def __init__(self, agent_manager: Any) -> None:
        self._agent_manager = agent_manager

    async def execute(self, step: Step, context: dict[str, Any] | None = None) -> Step:
        ctx = dict(context or {})
        ctx["step_id"] = step.id
        ctx["step_title"] = step.title
        ctx["step_description"] = step.description

        step.status = StepStatus.RUNNING
        step.started_at = __import__("datetime").datetime.now(
            tz=__import__("datetime").timezone.utc
        ).isoformat()

        agent_id = step.assigned_agent or "executor"
        logger.info("Executing step '%s' via agent '%s'", step.title, agent_id)

        call = ToolCall(tool_name="agent_dispatch", params={"agent_id": agent_id, "task": step.description})

        try:
            runtime_agent = self._agent_manager.get_runtime_agent(agent_id)
            if runtime_agent is None:
                raise ValueError(f"Agent '{agent_id}' not registered")

            result = await self._agent_manager.dispatch(
                agent_id=agent_id,
                task=step.description,
                context=ctx,
            )

            call.success = True
            call.result = result
            step.tool_calls.append(call)

            output = result.get("result", result) if isinstance(result, dict) else result
            step.result = output if isinstance(output, dict) else {"output": str(output)}
            step.status = StepStatus.SUCCEEDED
            step.error = None

        except Exception as exc:
            logger.warning("Step '%s' failed: %s", step.title, exc)
            call.success = False
            call.error = str(exc)
            step.tool_calls.append(call)
            step.error = str(exc)
            step.status = StepStatus.FAILED

        step.completed_at = __import__("datetime").datetime.now(
            tz=__import__("datetime").timezone.utc
        ).isoformat()

        return step
