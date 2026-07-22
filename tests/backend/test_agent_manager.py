"""Tests for AgentManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.agent_manager import AgentManager
from app.agents.base import AgentDefinition, BaseAgent


class _MockAgent(BaseAgent):
    def __init__(self, agent_id: str, role: str = "tester") -> None:
        super().__init__(agent_id)
        self._role = role
        self._mock_execute = AsyncMock(return_value={"status": "completed", "agent": agent_id})

    @property
    def definition(self) -> AgentDefinition:
        return AgentDefinition(
            agent_id=self.agent_id,
            name=self.agent_id.title(),
            role=self._role,
        )

    async def execute(self, task: str, context: dict) -> dict:
        return await self._mock_execute(task, context)


@pytest.fixture
def manager():
    db = MagicMock()
    return AgentManager(db)


class TestAgentManager:
    def test_register_and_get_runtime_agent(self, manager):
        agent = _MockAgent("test-agent")
        manager.register_runtime_agent(agent)
        assert manager.get_runtime_agent("test-agent") is agent

    def test_unregister_runtime_agent(self, manager):
        agent = _MockAgent("test-agent")
        manager.register_runtime_agent(agent)
        manager.unregister_runtime_agent("test-agent")
        assert manager.get_runtime_agent("test-agent") is None

    def test_list_runtime_agents(self, manager):
        a1 = _MockAgent("a1")
        a2 = _MockAgent("a2")
        manager.register_runtime_agent(a1)
        manager.register_runtime_agent(a2)
        ids = [a.agent_id for a in manager.list_runtime_agents()]
        assert "a1" in ids
        assert "a2" in ids

    @patch.object(AgentManager, "_agent_to_dict")
    @pytest.mark.asyncio
    async def test_create_agent_definition(self, mock_to_dict, manager):
        manager._repo.create = AsyncMock()
        manager._repo.create.return_value = MagicMock()
        mock_to_dict.return_value = {"id": "new-agent"}

        result = await manager.create_agent_definition(
            agent_id="new-agent", name="New Agent", role="helper"
        )
        assert result == {"id": "new-agent"}

    @pytest.mark.asyncio
    async def test_create_agent_definition_failure(self, manager):
        manager._repo.create = AsyncMock(side_effect=Exception("DB error"))
        result = await manager.create_agent_definition(
            agent_id="fail-agent", name="Fail", role="fail"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_agent_definition_found(self, manager):
        manager._repo.get = AsyncMock(return_value=MagicMock(id="found"))
        result = await manager.get_agent_definition("found")
        assert result is not None
        assert result["id"] == "found"

    @pytest.mark.asyncio
    async def test_get_agent_definition_not_found(self, manager):
        manager._repo.get = AsyncMock(return_value=None)
        result = await manager.get_agent_definition("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_agent_definitions(self, manager):
        manager._repo.list = AsyncMock(return_value=[MagicMock(id="a"), MagicMock(id="b")])
        results = await manager.list_agent_definitions()
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_update_agent_definition(self, manager):
        mock_agent = MagicMock()
        mock_agent.id = "upd"
        mock_agent.name = "Updated"
        manager._repo.update = AsyncMock(return_value=mock_agent)
        result = await manager.update_agent_definition("upd", name="Updated")
        assert result["name"] == "Updated"

    @pytest.mark.asyncio
    async def test_delete_agent_definition(self, manager):
        manager._repo.delete = AsyncMock(return_value=True)
        assert await manager.delete_agent_definition("del") is True

    @pytest.mark.asyncio
    async def test_dispatch_success(self, manager):
        agent = _MockAgent("worker")
        manager.register_runtime_agent(agent)

        result = await manager.dispatch("worker", "do something", {"task_id": "123"})
        assert result["status"] == "completed"
        assert result["agent"] == "worker"

    @pytest.mark.asyncio
    async def test_dispatch_agent_not_found(self, manager):
        result = await manager.dispatch("unknown", "task")
        assert result["status"] == "error"
        assert "No runtime agent" in result["error"]

    @pytest.mark.asyncio
    async def test_dispatch_exception_handling(self, manager):
        agent = _MockAgent("fragile")
        agent._mock_execute = AsyncMock(side_effect=RuntimeError("boom"))
        manager.register_runtime_agent(agent)

        result = await manager.dispatch("fragile", "risky task")
        assert result["status"] == "error"
        assert "boom" in result["error"]

    @pytest.mark.asyncio
    async def test_delegate_creates_span(self, manager):
        agent_a = _MockAgent("agent_a")
        agent_b = _MockAgent("agent_b")
        manager.register_runtime_agent(agent_a)
        manager.register_runtime_agent(agent_b)

        result = await manager.delegate("agent_a", "agent_b", "delegated task")
        assert result["status"] == "completed"
        assert manager.metrics.snapshot()["counters"].get("delegation.total", 0) >= 1

    @pytest.mark.asyncio
    async def test_execute_nested(self, manager):
        a1 = _MockAgent("planner")
        a2 = _MockAgent("coder")
        manager.register_runtime_agent(a1)
        manager.register_runtime_agent(a2)

        plan = [
            {"agent": "planner", "task": "plan something"},
            {"agent": "coder", "task": "code something"},
        ]
        results = await manager.execute_nested(plan)
        assert len(results) == 2
        assert results[0]["status"] == "completed"
        assert results[1]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_tracing_on_dispatch(self, manager):
        agent = _MockAgent("traceable")
        manager.register_runtime_agent(agent)

        await manager.dispatch("traceable", "trace task", {"task_id": "t-1"})
        traces = manager.tracer.to_dict()
        assert len(traces) >= 1
        assert traces[0]["agent_id"] == "traceable"
        assert traces[0]["task"] == "trace task"

    @pytest.mark.asyncio
    async def test_metrics_on_dispatch(self, manager):
        agent = _MockAgent("metric-agent")
        manager.register_runtime_agent(agent)

        await manager.dispatch("metric-agent", "task 1")
        await manager.dispatch("metric-agent", "task 2")

        snap = manager.metrics.snapshot()
        assert snap["counters"]["dispatch.metric-agent"] == 2
        assert snap["counters"]["dispatch.total"] == 2
