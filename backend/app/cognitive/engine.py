"""CognitiveEngine — the brain of NOVA CORE.

Receives every ExecuteRequest before the Kernel, analyzes intent, loads
a unified CognitiveContext, decides the best action, and returns a
CognitiveDecision for the Kernel to execute.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.agents.agent_manager import AgentManager
from app.cognitive.context import CognitiveContext, IntentType
from app.cognitive.decision import (
    CognitiveDecision,
    DecisionAction,
    DecisionHandler,
    default_handler_registry,
)
from app.cognitive.router import CognitiveRouter, IntentDetector, RuleBasedIntentDetector
from app.cognitive.state import CognitiveState
from app.memory.conversation_memory import ConversationMemory
from app.memory.goals import GoalManager
from app.memory.profile import UserProfileMemory
from app.memory.semantic import SemanticMemory
from app.orchestrator.task_manager import TaskManager

logger = logging.getLogger(__name__)


class CognitiveEngine:
    """Main cognitive engine — analyzes, decides, and returns a decision.

    Pluggable via:
    - detector (IntentDetector strategy)
    - handlers (dict[IntentType, DecisionHandler])
    """

    def __init__(
        self,
        goal_manager: GoalManager,
        task_manager: TaskManager,
        agent_manager: AgentManager,
        profile_memory: UserProfileMemory,
        conversation_memory: ConversationMemory,
        detector: IntentDetector | None = None,
        handlers: dict[IntentType, DecisionHandler] | None = None,
        semantic_memory: SemanticMemory | None = None,
        planner: Any | None = None,
        long_term_memory: Any | None = None,
        reasoning_engine: Any | None = None,
        workflow_engine: Any | None = None,
        knowledge_graph_engine: Any | None = None,
        learning_engine: Any | None = None,
        vector_memory_engine: Any | None = None,
        event_publisher: Any | None = None,
        approvals_manager: Any | None = None,
        evolution_engine: Any | None = None,
    ) -> None:
        self._goal_manager = goal_manager
        self._task_manager = task_manager
        self._agent_manager = agent_manager
        self._profile_memory = profile_memory
        self._conversation_memory = conversation_memory
        self._semantic_memory = semantic_memory
        self._planner = planner
        self._approvals_manager = approvals_manager
        self._long_term_memory = long_term_memory
        self._reasoning_engine = reasoning_engine
        self._workflow_engine = workflow_engine
        self._knowledge_graph_engine = knowledge_graph_engine
        self._learning_engine = learning_engine
        self._vector_memory_engine = vector_memory_engine
        self._event_publisher = event_publisher
        self._evolution_engine = evolution_engine
        self._router = CognitiveRouter(
            detector=detector or RuleBasedIntentDetector(),
            handlers=handlers or default_handler_registry(),
        )
        self._state: CognitiveState | None = None

    @property
    def router(self) -> CognitiveRouter:
        return self._router

    @property
    def state(self) -> CognitiveState | None:
        return self._state

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def process(
        self,
        raw_input: str,
        user_id: str | None = None,
        session_id: str | None = None,
        skip_approval_check: bool = False,
    ) -> CognitiveState:
        """Full cognitive cycle: load context → detect intent → decide.

        Returns a CognitiveState containing the context, decision, and
        optional execution result.
        """
        state = CognitiveState()

        try:
            context = await self._load_context(raw_input, user_id, session_id)
            state.context = context

            decision = await self._router.route(context)
            state.decision = decision

            result = await self._execute_decision(
                decision, context, skip_approval_check=skip_approval_check
            )
            state.execution_result = result

            await self._publish_event(
                "system.event",
                payload={
                    "action": decision.action.value if hasattr(decision.action, "value") else str(decision.action),
                    "confidence": decision.confidence,
                    "raw_input": raw_input[:200],
                },
                session_id=session_id,
                user_id=user_id,
            )

        except Exception as exc:
            logger.exception("CognitiveEngine.process failed: %s", exc)
            state.error = str(exc)
            await self._publish_event(
                "system.event",
                payload={"error": str(exc), "raw_input": raw_input[:200]},
                session_id=session_id,
                user_id=user_id,
            )
            if state.decision is None:
                state.decision = CognitiveDecision(
                    action=DecisionAction.FALLBACK,
                    handler_name="engine_error",
                    payload={"task": raw_input},
                    confidence=0.0,
                    reasoning=f"Engine error: {exc}",
                )

        self._state = state
        return state

    # ------------------------------------------------------------------
    # Context loader
    # ------------------------------------------------------------------

    async def _load_context(
        self,
        raw_input: str,
        user_id: str | None,
        session_id: str | None,
    ) -> CognitiveContext:
        ctx = CognitiveContext(
            raw_input=raw_input,
            user_id=user_id,
            session_id=session_id,
        )

        ctx.agent_registry = [a.agent_id for a in self._agent_manager.list_runtime_agents()]

        if session_id:
            try:
                sid = UUID(session_id) if isinstance(session_id, str) else session_id
                ctx.conversation_history = await self._conversation_memory.get_history(sid, limit=10)
            except Exception:
                logger.debug("Could not load conversation history for %s", session_id)

        if user_id:
            uid = UUID(user_id) if isinstance(user_id, str) else user_id
            try:
                profile = await self._profile_memory.get_profile(uid)
                ctx.user_profile = profile
            except Exception:
                logger.debug("Could not load profile for %s", user_id)

            try:
                ctx.goals = await self._goal_manager.list_goals(uid)
            except Exception:
                logger.debug("Could not load goals for %s", user_id)

        try:
            all_tasks = await self._task_manager.list_tasks(limit=100)
            ctx.pending_tasks = [t for t in all_tasks if t.get("status") in ("CREATED", "QUEUED")]
            ctx.running_tasks = [t for t in all_tasks if t.get("status") in ("RUNNING", "WAITING")]
        except Exception:
            logger.debug("Could not load tasks")

        # 5. Semantic memory search — enrich context with relevant past knowledge
        if self._semantic_memory is not None:
            try:
                results = await self._semantic_memory.search(raw_input, top_k=5)
                ctx.semantic_memories = results
            except Exception:
                logger.debug("Could not search semantic memory")

        ctx.extra["raw_input"] = raw_input

        return ctx

    # ------------------------------------------------------------------
    # Decision executor
    # ------------------------------------------------------------------

    async def _execute_decision(
        self,
        decision: CognitiveDecision,
        context: CognitiveContext,
        skip_approval_check: bool = False,
    ) -> dict[str, Any] | None:
        """Execute side effects for a decision where appropriate.

        Some decisions (like ROUTE_TO_KERNEL) are left for the caller;
        others like CREATE_GOAL or CREATE_TASK are executed here.
        """
        action = decision.action

        # --- Approval gate: intercept risky/impactful actions before executing ---
        if not skip_approval_check:
            approval_gated_actions = (
                DecisionAction.CREATE_PLAN,
                DecisionAction.DELEGATE_TO_PLANNER,
                DecisionAction.DELEGATE_TO_RESEARCHER,
                DecisionAction.DELEGATE_TO_CODER,
                DecisionAction.DELEGATE_TO_EXECUTOR,
                DecisionAction.DELEGATE_TO_REVIEWER,
                DecisionAction.EXECUTE_WORKFLOW,
                DecisionAction.DELEGATE_TO_OPENCODE,
            )
            if self._approvals_manager is not None and action in approval_gated_actions:
                task_description = (
                    decision.payload.get("objective")
                    or decision.payload.get("task")
                    or decision.payload.get("query")
                    or context.raw_input
                )
                mandatory_category = self._approvals_manager.requires_mandatory_approval(task_description)
                if mandatory_category:
                    approval = self._approvals_manager.request(
                        action_type=action.value if hasattr(action, "value") else str(action),
                        description=task_description,
                        requester="cognitive_engine",
                        metadata={"reasoning": decision.reasoning, "payload": decision.payload},
                    )
                    return {
                        "approval_required": True,
                        "approval_id": approval.id,
                        "approval_category": mandatory_category,
                        "message": f"This action requires your approval before execution ({mandatory_category}).",
                    }

        if action == DecisionAction.CREATE_GOAL:
            return await self._execute_create_goal(decision, context)

        if action == DecisionAction.CREATE_TASK:
            return await self._execute_create_task(decision, context)

        if action == DecisionAction.CREATE_PLAN:
            return await self._execute_create_plan(decision, context)

        if action == DecisionAction.REASON:
            return await self._execute_reason(decision, context)

        if action == DecisionAction.EXECUTE_WORKFLOW:
            return await self._execute_workflow(decision, context)

        if action == DecisionAction.QUERY_KNOWLEDGE_GRAPH:
            return await self._execute_knowledge_graph(decision, context)

        if action == DecisionAction.RUN_META_CYCLE:
            return await self._execute_meta_cycle(decision, context)

        if action in (
            DecisionAction.DELEGATE_TO_PLANNER,
            DecisionAction.DELEGATE_TO_RESEARCHER,
            DecisionAction.DELEGATE_TO_CODER,
            DecisionAction.DELEGATE_TO_MEMORY,
            DecisionAction.DELEGATE_TO_EXECUTOR,
            DecisionAction.DELEGATE_TO_REVIEWER,
            DecisionAction.DELEGATE_TO_OPENCODE,
        ):
            return await self._execute_delegate(decision)

        if action == DecisionAction.UPDATE_PROFILE:
            return await self._execute_profile_update(decision, context)

        return None

    async def _execute_create_plan(
        self, decision: CognitiveDecision, context: CognitiveContext
    ) -> dict[str, Any]:
        objective = decision.payload.get("objective", context.raw_input)
        return {"error": "Planner not available", "objective": objective}

    async def _execute_reason(
        self, decision: CognitiveDecision, context: CognitiveContext
    ) -> dict[str, Any]:
        query = decision.payload.get("query", context.raw_input)
        return {"error": "ReasoningEngine not available", "query": query}

    async def _execute_workflow(
        self, decision: CognitiveDecision, context: CognitiveContext
    ) -> dict[str, Any]:
        task = decision.payload.get("task", context.raw_input)
        return {"error": "WorkflowEngine not available", "task": task}

    async def _execute_knowledge_graph(
        self, decision: CognitiveDecision, context: CognitiveContext
    ) -> dict[str, Any]:
        query = decision.payload.get("query", context.raw_input)
        return {"error": "KnowledgeGraphEngine not available", "query": query}

    async def _execute_meta_cycle(
        self, decision: CognitiveDecision, context: CognitiveContext
    ) -> dict[str, Any]:
        """Execute a meta-improvement cycle via the EvolutionEngine."""
        evolution_engine = getattr(self, "_evolution_engine", None)
        if evolution_engine is None:
            return {"error": "EvolutionEngine not available"}

        try:
            result = await evolution_engine.run_evolution_cycle()
            return {
                "evolution_cycle": result,
                "task": decision.payload.get("task", context.raw_input),
            }
        except Exception as exc:
            return {"error": f"Evolution cycle failed: {exc}"}

    async def _execute_create_goal(
        self, decision: CognitiveDecision, context: CognitiveContext
    ) -> dict[str, Any]:
        uid = self._resolve_uid(context)
        if uid is None:
            return {"error": "No user_id available to create goal"}
        title = decision.payload.get("title", context.raw_input)
        goal = await self._goal_manager.create_goal(uid, title=title, priority=3)
        delegate_to = decision.payload.get("delegate_to")
        if delegate_to and self._agent_manager.get_runtime_agent(delegate_to):
            await self._agent_manager.dispatch(
                agent_id=delegate_to,
                task=title,
                context={"user_id": str(uid), "goal_id": goal.get("id", "")},
            )
        await self._publish_event(
            "goal.created",
            payload={"goal_id": goal.get("id", ""), "title": title},
            aggregate_id=goal.get("id", ""),
            aggregate_type="goal",
            session_id=context.session_id,
            user_id=context.user_id,
        )
        return {"created_goal": goal, "delegated_to": delegate_to}

    async def _execute_create_task(
        self, decision: CognitiveDecision, context: CognitiveContext
    ) -> dict[str, Any]:
        """Create a task and return result with task_id for async execution.

        Returns:
            dict with keys: created_task, assigned_agent, task_id
        """
        goal_text = decision.payload.get("goal", context.raw_input)
        agent = decision.payload.get("assigned_agent")
        task = await self._task_manager.create_task(
            goal=goal_text,
            assigned_agent=agent,
        )
        task_id = task.get("id", "")
        result = {
            "created_task": task,
            "assigned_agent": agent,
            "task_id": task_id,
        }

        await self._publish_event(
            "task.created",
            payload={"task_id": task_id, "goal": goal_text, "agent": agent},
            aggregate_id=task_id,
            aggregate_type="task",
            session_id=context.session_id,
            user_id=context.user_id,
        )

        # Auto-learn from the task creation event
        if self._learning_engine is not None:
            try:
                await self._learning_engine.learn_from_execution(
                    execution_data={
                        "id": task_id,
                        "status": "CREATED",
                        "user_id": context.user_id,
                    },
                    task_data=task,
                )
            except Exception:
                logger.debug("LearningEngine auto-learn from task creation skipped")

        return result

    async def _execute_delegate(self, decision: CognitiveDecision) -> dict[str, Any]:
        action_to_agent = {
            DecisionAction.DELEGATE_TO_PLANNER: "planner",
            DecisionAction.DELEGATE_TO_RESEARCHER: "researcher",
            DecisionAction.DELEGATE_TO_CODER: "coder",
            DecisionAction.DELEGATE_TO_MEMORY: "memory",
            DecisionAction.DELEGATE_TO_EXECUTOR: "executor",
            DecisionAction.DELEGATE_TO_REVIEWER: "reviewer",
            DecisionAction.DELEGATE_TO_OPENCODE: "opencode",
        }
        agent_id = action_to_agent.get(decision.action)
        if agent_id is None:
            return {"error": f"Unknown delegation action: {decision.action}"}

        runtime = self._agent_manager.get_runtime_agent(agent_id)
        if runtime is None:
            return {"error": f"Agent '{agent_id}' not registered", "agent_id": agent_id}

        result = await self._agent_manager.dispatch(
            agent_id=agent_id,
            task=decision.payload.get("task", ""),
            context=decision.payload,
        )
        return {"agent_id": agent_id, "result": result}

    async def _execute_profile_update(
        self, decision: CognitiveDecision, context: CognitiveContext
    ) -> dict[str, Any]:
        uid = self._resolve_uid(context)
        if uid is None:
            return {"error": "No user_id available to update profile"}
        try:
            updated = await self._profile_memory.update_profile(uid)
            return {"updated_profile": True, "profile": updated}
        except Exception as exc:
            return {"error": str(exc)}

    @staticmethod
    def _resolve_uid(context: CognitiveContext) -> UUID | None:
        raw = context.user_id
        if raw is None:
            return None
        try:
            return UUID(str(raw)) if isinstance(raw, str) else raw
        except ValueError:
            return None

    async def _publish_event(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        aggregate_id: str = "",
        aggregate_type: str = "cognitive",
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> None:
        if self._event_publisher is None:
            return
        try:
            await self._event_publisher.publish(
                event_type=event_type,
                payload=payload or {},
                aggregate_id=aggregate_id,
                aggregate_type=aggregate_type,
                source="cognitive_engine",
                session_id=session_id or "",
                user_id=user_id or "",
            )
        except Exception:
            logger.debug("Failed to publish event %s", event_type)
