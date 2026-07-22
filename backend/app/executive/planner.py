"""ExecutivePlanner — autonomous executive layer for NOVA CORE."""

from __future__ import annotations

import datetime
import logging
from typing import Any
from uuid import UUID

from app.agents.agent_manager import AgentManager
from app.executive.strategy import PlanningOutput, PlanningStrategy, RuleBasedStrategy, SuggestedTask
from app.memory.conversation_memory import ConversationMemory
from app.memory.goals import GoalManager
from app.memory.profile import UserProfileMemory
from app.orchestrator.event_bus import EventBus
from app.orchestrator.task_manager import TaskManager

logger = logging.getLogger(__name__)


class ExecutivePlanner:
    """Autonomous executive layer that continuously analyzes goals, tasks,
    user profile, and conversation memory to suggest and generate tasks.

    Uses a pluggable PlanningStrategy for analysis; emits lifecycle events
    for observability.
    """

    def __init__(
        self,
        goal_manager: GoalManager,
        task_manager: TaskManager,
        agent_manager: AgentManager,
        profile_memory: UserProfileMemory,
        conversation_memory: ConversationMemory,
        event_bus: EventBus,
        strategy: PlanningStrategy | None = None,
    ) -> None:
        self._goal_manager = goal_manager
        self._task_manager = task_manager
        self._agent_manager = agent_manager
        self._profile_memory = profile_memory
        self._conversation_memory = conversation_memory
        self._event_bus = event_bus
        self._strategy = strategy or RuleBasedStrategy()

    @property
    def strategy(self) -> PlanningStrategy:
        return self._strategy

    @strategy.setter
    def strategy(self, s: PlanningStrategy) -> None:
        self._strategy = s

    async def plan(
        self,
        user_id: str | UUID,
        session_id: str | UUID | None = None,
        max_tasks: int = 5,
    ) -> PlanningOutput:
        """Run a full planning cycle: analyze, generate tasks, assign agents.

        Returns a PlanningOutput with the results of the analysis.
        """
        uid = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        sid = UUID(str(session_id)) if session_id and isinstance(session_id, str) else session_id

        goals = await self._goal_manager.list_goals(uid)
        tasks = await self._task_manager.list_tasks(limit=100)

        profile = None
        try:
            profile = await self._profile_memory.get_profile(uid)
        except Exception:
            logger.debug("No profile found for user %s", uid)

        recent_messages: list[dict[str, str]] = []
        if sid:
            try:
                recent_messages = await self._conversation_memory.get_history(sid, limit=10)
            except Exception:
                logger.debug("No conversation history for session %s", sid)

        output = await self._strategy.analyze(
            goals=goals,
            tasks=tasks,
            profile=profile,
            recent_messages=recent_messages,
        )

        await self._event_bus.emit(
            "executive.goal_reviewed",
            {
                "user_id": str(uid),
                "reviewed_goal_ids": output.reviewed_goal_ids,
                "observations": output.observations,
                "timestamp": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
            },
        )

        created_count = 0
        for suggestion in output.suggested_tasks:
            if created_count >= max_tasks:
                output.observations.append(f"Reached max_tasks limit ({max_tasks}), skipping remaining suggestions.")
                break

            deps: list[UUID] = []
            for dep_str in suggestion.dependencies:
                try:
                    deps.append(UUID(dep_str))
                except Exception:
                    logger.warning("Invalid dependency UUID: %s", dep_str)

            task = await self._task_manager.create_task(
                goal=suggestion.title,
                plan={"source": "executive_planner", "goal_id": suggestion.goal_id},
                steps=[suggestion.description],
                dependencies=deps or None,
                assigned_agent=suggestion.suggested_agent,
            )

            task_id = task.get("id", "")
            await self._event_bus.emit(
                "executive.task_generated",
                {
                    "task_id": task_id,
                    "goal_id": suggestion.goal_id,
                    "goal_title": suggestion.goal_title,
                    "assigned_agent": suggestion.suggested_agent,
                    "timestamp": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
                },
            )

            if suggestion.suggested_agent:
                agent = self._agent_manager.get_runtime_agent(suggestion.suggested_agent)
                if agent:
                    context = {
                        "goal_id": suggestion.goal_id,
                        "task_id": task_id,
                        "goal": suggestion.goal_title,
                        "description": suggestion.description,
                    }
                    dispatch_result = await self._agent_manager.dispatch(
                        agent_id=suggestion.suggested_agent,
                        task=suggestion.title,
                        context=context,
                    )
                    await self._event_bus.emit(
                        "executive.task_assigned",
                        {
                            "task_id": task_id,
                            "agent_id": suggestion.suggested_agent,
                            "dispatch_status": dispatch_result.get("status", "unknown"),
                            "timestamp": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
                        },
                    )
                else:
                    logger.warning(
                        "Suggested agent '%s' not registered; task %s created without dispatch.",
                        suggestion.suggested_agent, task_id,
                    )

            created_count += 1

        return output

    async def review(
        self,
        user_id: str | UUID,
        session_id: str | UUID | None = None,
    ) -> PlanningOutput:
        """Analyze goals and state without generating tasks.

        Useful for previewing what the planner would suggest.
        """
        uid = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        sid = UUID(str(session_id)) if session_id and isinstance(session_id, str) else session_id

        goals = await self._goal_manager.list_goals(uid)
        tasks = await self._task_manager.list_tasks(limit=100)

        profile = None
        try:
            profile = await self._profile_memory.get_profile(uid)
        except Exception:
            pass

        recent_messages = []
        if sid:
            try:
                recent_messages = await self._conversation_memory.get_history(sid, limit=10)
            except Exception:
                pass

        return await self._strategy.analyze(
            goals=goals,
            tasks=tasks,
            profile=profile,
            recent_messages=recent_messages,
        )
