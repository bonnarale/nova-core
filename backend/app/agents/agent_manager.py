"""AgentManager - multi-agent runtime for NOVA CORE."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.agents.base import AgentDefinition, BaseAgent
from app.agents.metrics import MetricsCollector
from app.agents.tracing import TraceSpan, Tracer
from app.db.agent_repository import AgentRepository
from app.db.postgres import Database

if TYPE_CHECKING:
    from app.tools.executor import ToolExecutor

logger = logging.getLogger(__name__)


class AgentManager:
    """Central registry and runtime for agents.

    Manages agent definitions (persisted in DB), runtime instances,
    task dispatch, delegation, execution tracing, and metrics.
    """

    def __init__(self, database: Database, tool_executor: ToolExecutor | None = None) -> None:
        self._repo = AgentRepository(database.session_factory)
        self._runtime_agents: dict[str, BaseAgent] = {}
        self.tracer = Tracer()
        self.metrics = MetricsCollector()
        self.tool_executor = tool_executor

    # ------------------------------------------------------------------
    # Runtime agent registration (built-in / custom code-based agents)
    # ------------------------------------------------------------------

    def register_runtime_agent(self, agent: BaseAgent) -> None:
        """Register a runtime agent instance (a BaseAgent subclass)."""
        self._runtime_agents[agent.agent_id] = agent
        logger.info("Runtime agent registered: %s (%s)", agent.agent_id, type(agent).__name__)

    def unregister_runtime_agent(self, agent_id: str) -> None:
        """Remove a runtime agent from the registry."""
        self._runtime_agents.pop(agent_id, None)

    def get_runtime_agent(self, agent_id: str) -> BaseAgent | None:
        """Look up a runtime agent by ID."""
        return self._runtime_agents.get(agent_id)

    def list_runtime_agents(self) -> list[BaseAgent]:
        """Return all registered runtime agents."""
        return list(self._runtime_agents.values())

    # ------------------------------------------------------------------
    # Agent definition CRUD (persisted in DB)
    # ------------------------------------------------------------------

    async def create_agent_definition(
        self,
        agent_id: str,
        name: str,
        role: str,
        description: str = "",
        system_prompt: str = "",
        allowed_tools: list[str] | None = None,
        memory_scope: str = "session",
        permissions: dict[str, Any] | None = None,
        supported_models: list[str] | None = None,
    ) -> dict[str, Any] | None:
        try:
            agent = await self._repo.create(
                agent_id=agent_id,
                name=name,
                role=role,
                description=description,
                system_prompt=system_prompt,
                allowed_tools=allowed_tools or [],
                memory_scope=memory_scope,
                permissions=permissions or {},
                supported_models=supported_models or [],
            )
            self.metrics.increment("agents.created")
            return self._agent_to_dict(agent)
        except Exception as exc:
            logger.error("Failed to create agent definition %s: %s", agent_id, exc)
            return None

    async def get_agent_definition(self, agent_id: str) -> dict[str, Any] | None:
        agent = await self._repo.get(agent_id)
        if agent is None:
            return None
        return self._agent_to_dict(agent)

    async def list_agent_definitions(self) -> list[dict[str, Any]]:
        agents = await self._repo.list()
        return [self._agent_to_dict(a) for a in agents]

    async def update_agent_definition(
        self, agent_id: str, **updates: Any
    ) -> dict[str, Any] | None:
        agent = await self._repo.update(agent_id, **updates)
        if agent is None:
            return None
        return self._agent_to_dict(agent)

    async def delete_agent_definition(self, agent_id: str) -> bool:
        return await self._repo.delete(agent_id)

    # ------------------------------------------------------------------
    # Task dispatch
    # ------------------------------------------------------------------

    async def dispatch(
        self,
        agent_id: str,
        task: str,
        context: dict[str, Any] | None = None,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
    ) -> dict[str, Any]:
        """Dispatch a task to a specific agent with tracing."""
        runtime = self._runtime_agents.get(agent_id)
        if runtime is None:
            self.metrics.increment("dispatch.errors.agent_not_found")
            return {
                "agent": agent_id,
                "status": "error",
                "error": f"No runtime agent registered for '{agent_id}'",
            }

        span = self.tracer.start_span(
            agent_id=agent_id,
            task=task,
            task_id=context.get("task_id", "") if context else "",
            parent_span_id=parent_span_id,
            trace_id=trace_id,
            context=context or {},
        )

        self.metrics.increment(f"dispatch.{agent_id}")
        self.metrics.increment("dispatch.total")

        # Inject tool_executor into agent context so agents can call tools
        exec_context = dict(context or {})
        if self.tool_executor is not None:
            exec_context["tool_executor"] = self.tool_executor
            exec_context["tool_registry"] = self.tool_executor.registry

        try:
            with self.metrics.time(f"execute.{agent_id}"):
                result = await runtime.execute(task, exec_context)

            status = "success" if result.get("status") == "completed" else "error"
            span.close(status=status, output=result)
            self.metrics.increment(f"dispatch.{agent_id}.{status}")
            return result

        except Exception as exc:
            logger.exception("Agent %s failed: %s", agent_id, exc)
            span.close(status="error", error=str(exc))
            self.metrics.increment(f"dispatch.{agent_id}.error")
            return {
                "agent": agent_id,
                "status": "error",
                "error": str(exc),
            }

    # ------------------------------------------------------------------
    # Agent-to-agent delegation
    # ------------------------------------------------------------------

    async def delegate(
        self,
        from_agent: str,
        to_agent: str,
        task: str,
        context: dict[str, Any] | None = None,
        parent_span_id: str | None = None,
    ) -> dict[str, Any]:
        """Delegate a task from one agent to another, recording a trace span."""
        logger.info("Delegation: %s -> %s for '%s'", from_agent, to_agent, task[:60])
        self.metrics.increment("delegation.total")
        self.metrics.increment(f"delegation.{from_agent}_to_{to_agent}")

        context = dict(context or {})
        context["delegated_from"] = from_agent
        context["delegated_to"] = to_agent

        result = await self.dispatch(
            agent_id=to_agent,
            task=task,
            context=context,
            parent_span_id=parent_span_id,
        )

        self.metrics.increment("delegation.completed")
        return result

    # ------------------------------------------------------------------
    # Nested task execution
    # ------------------------------------------------------------------

    async def execute_nested(
        self,
        plan: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
        parent_span_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a sequence of tasks across agents.

        Each item in ``plan`` has the form::

            {"agent": "coder", "task": "implement X", "context": {...}}
        """
        results: list[dict[str, Any]] = []
        for step in plan:
            agent_id = step.get("agent", "executor")
            task = step.get("task", "")
            step_context = dict(context or {})
            step_context.update(step.get("context", {}))

            result = await self.dispatch(
                agent_id=agent_id,
                task=task,
                context=step_context,
                parent_span_id=parent_span_id,
            )
            result["step_agent"] = agent_id
            result["step_task"] = task
            results.append(result)

        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _agent_to_dict(agent: Any) -> dict[str, Any]:
        return {
            "id": agent.id,
            "name": agent.name,
            "role": agent.role,
            "description": agent.description or "",
            "system_prompt": agent.system_prompt,
            "allowed_tools": list(agent.allowed_tools or []),
            "memory_scope": agent.memory_scope,
            "permissions": dict(agent.permissions or {}),
            "supported_models": list(agent.supported_models or []),
            "status": agent.status,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
        }
