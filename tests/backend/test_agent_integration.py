"""Integration tests for the Multi-Agent Runtime."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents import AgentManager, Tracer
from app.agents.builtins import (
    CoderAgent,
    ExecutorAgent,
    MemoryAgent,
    PlannerAgent,
    ResearchAgent,
    ReviewerAgent,
)


@pytest.fixture
def manager():
    db = MagicMock()
    m = AgentManager(db)
    for agent in [
        PlannerAgent(),
        ResearchAgent(),
        CoderAgent(),
        ReviewerAgent(),
        MemoryAgent(),
        ExecutorAgent(),
    ]:
        m.register_runtime_agent(agent)
    return m


class TestMultiAgentIntegration:
    @pytest.mark.asyncio
    async def test_planner_delegates_to_researcher(self, manager):
        plan_result = await manager.dispatch(
            "planner", "Build a recommendation engine",
            {"goal": "Build a recommendation engine"},
        )
        assert plan_result["status"] == "completed"

        research_result = await manager.dispatch(
            "researcher", "Research ML approaches",
            {"goal": "Research ML approaches"},
        )
        assert research_result["status"] == "completed"
        assert "findings" in research_result

    @pytest.mark.asyncio
    async def test_full_pipeline_via_delegation(self, manager):
        plan = await manager.dispatch("planner", "Create auth module", {"goal": "Create auth module"})
        assert plan["status"] == "completed"

        research = await manager.delegate("planner", "researcher", "Research auth patterns",
                                          {"goal": "Create auth module"})
        assert research["status"] == "completed"

        code = await manager.delegate("researcher", "coder", "Implement auth",
                                      {"goal": "Create auth module"})
        assert code["status"] == "completed"
        assert "code" in code

        review = await manager.delegate("coder", "reviewer", "Review auth implementation",
                                        {"goal": "Create auth module", "artifact": code["code"]})
        assert review["status"] == "completed"
        assert review["approved"] is True

    @pytest.mark.asyncio
    async def test_nested_task_execution(self, manager):
        plan = [
            {"agent": "planner", "task": "Plan feature X", "context": {"goal": "Feature X"}},
            {"agent": "coder", "task": "Implement feature X", "context": {"goal": "Feature X"}},
            {"agent": "reviewer", "task": "Review feature X", "context": {"goal": "Feature X"}},
        ]
        results = await manager.execute_nested(plan)
        assert len(results) == 3
        for r in results:
            assert r["status"] == "completed"

    @pytest.mark.asyncio
    async def test_tracing_captures_full_pipeline(self, manager):
        root_span = manager.tracer.start_span("root", "pipeline", task_id="pipe-1")

        await manager.dispatch("planner", "Plan task", {"goal": "Task"},
                               parent_span_id=root_span.span_id)
        await manager.delegate("planner", "coder", "Code task",
                               {"goal": "Task"}, parent_span_id=root_span.span_id)

        child_ids = {s.agent_id for s in root_span.child_spans}
        assert "planner" in child_ids
        assert "coder" in child_ids

    @pytest.mark.asyncio
    async def test_metrics_collected(self, manager):
        await manager.dispatch("planner", "Task A", {"goal": "A"})
        await manager.dispatch("coder", "Task B", {"goal": "B"})
        await manager.delegate("planner", "reviewer", "Review", {"goal": "A"})

        snap = manager.metrics.snapshot()
        assert snap["counters"]["dispatch.total"] == 3
        assert snap["counters"]["dispatch.planner"] == 1
        assert snap["counters"]["dispatch.coder"] == 1
        assert snap["counters"]["delegation.total"] >= 1

    @pytest.mark.asyncio
    async def test_agent_to_agent_delegation_chain(self, manager):
        span = manager.tracer.start_span("planner", "Root task", task_id="root-001")

        r1 = await manager.delegate("planner", "researcher", "Research phase",
                                    {"goal": "Root"}, parent_span_id=span.span_id)

        r2 = await manager.delegate("researcher", "executor", "Execute phase",
                                    {"goal": "Root"}, parent_span_id=span.span_id)

        span.close(status="success")

        assert r1["status"] == "completed"
        assert r2["status"] == "completed"
        assert len(span.child_spans) == 2

    @pytest.mark.asyncio
    async def test_dispatch_to_unregistered_agent_returns_error(self, manager):
        result = await manager.dispatch("nonexistent", "Do something")
        assert result["status"] == "error"
        assert "No runtime agent" in result["error"]

    @pytest.mark.asyncio
    async def test_agent_definition_crud(self, manager):
        mock_agent = MagicMock()
        mock_agent.id = "custom-v1"
        mock_agent.name = "Custom Agent"
        mock_agent.role = "custom"
        mock_agent.description = ""
        mock_agent.system_prompt = ""
        mock_agent.allowed_tools = []
        mock_agent.memory_scope = "session"
        mock_agent.permissions = {}
        mock_agent.supported_models = []
        mock_agent.status = "active"
        mock_agent.created_at = MagicMock(isoformat=lambda: "2025-01-01T00:00:00")
        mock_agent.updated_at = MagicMock(isoformat=lambda: "2025-01-01T00:00:00")

        manager._repo.create = AsyncMock(return_value=mock_agent)
        created = await manager.create_agent_definition(
            agent_id="custom-v1", name="Custom Agent", role="custom"
        )
        assert created["id"] == "custom-v1"

        manager._repo.get = AsyncMock(return_value=mock_agent)
        fetched = await manager.get_agent_definition("custom-v1")
        assert fetched["id"] == "custom-v1"

    @pytest.mark.asyncio
    async def test_tracer_clear(self, manager):
        await manager.dispatch("planner", "Task", {"goal": "A"})
        assert len(manager.tracer.to_dict()) >= 1
        manager.tracer.clear()
        assert manager.tracer.to_dict() == []

    @pytest.mark.asyncio
    async def test_metrics_clear(self, manager):
        await manager.dispatch("planner", "Task", {"goal": "A"})
        assert manager.metrics.snapshot()["counters"]["dispatch.total"] >= 1
        manager.metrics.clear()
        assert manager.metrics.snapshot()["counters"] == {}
