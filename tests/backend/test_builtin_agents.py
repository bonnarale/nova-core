"""Tests for built-in agents."""

from __future__ import annotations

import pytest

from app.agents.builtins import (
    CoderAgent,
    ExecutorAgent,
    MemoryAgent,
    PlannerAgent,
    ResearchAgent,
    ReviewerAgent,
)


class TestPlannerAgent:
    @pytest.fixture
    def agent(self):
        return PlannerAgent()

    def test_definition(self, agent):
        d = agent.definition
        assert d.agent_id == "planner"
        assert d.role == "planner"
        assert "task_decomposition" in d.allowed_tools

    @pytest.mark.asyncio
    async def test_execute_creates_plan(self, agent):
        result = await agent.execute("Build a login system", {"goal": "Build a login system"})
        assert result["status"] == "completed"
        assert "steps" in result
        assert len(result["steps"]) == 5

    @pytest.mark.asyncio
    async def test_execute_with_existing_plan(self, agent):
        existing = {"steps": ["step1"], "dependencies": []}
        result = await agent.execute("Build something", {"goal": "Build something", "plan": existing})
        assert result["status"] == "completed"
        assert result["plan"] == existing


class TestResearchAgent:
    @pytest.fixture
    def agent(self):
        return ResearchAgent()

    def test_definition(self, agent):
        d = agent.definition
        assert d.agent_id == "researcher"
        assert d.memory_scope == "user"

    @pytest.mark.asyncio
    async def test_execute_gathers_findings(self, agent):
        result = await agent.execute("Research topic X", {"goal": "Research topic X"})
        assert result["status"] == "completed"
        assert "findings" in result


class TestCoderAgent:
    @pytest.fixture
    def agent(self):
        return CoderAgent()

    def test_definition(self, agent):
        d = agent.definition
        assert d.agent_id == "coder"
        assert "file_write" in d.allowed_tools

    @pytest.mark.asyncio
    async def test_execute_returns_code(self, agent):
        result = await agent.execute("Write calculator", {"goal": "Write calculator"})
        assert result["status"] == "completed"
        assert "code" in result
        assert "calculator" in result["code"]


class TestReviewerAgent:
    @pytest.fixture
    def agent(self):
        return ReviewerAgent()

    def test_definition(self, agent):
        d = agent.definition
        assert d.agent_id == "reviewer"
        assert "code_analysis" in d.allowed_tools

    @pytest.mark.asyncio
    async def test_execute_reviews(self, agent):
        result = await agent.execute("Review code", {"goal": "Check PR", "artifact": "def foo(): pass"})
        assert result["status"] == "completed"
        assert result["approved"] is True
        assert result["score"] == 85


class TestMemoryAgent:
    @pytest.fixture
    def agent(self):
        return MemoryAgent()

    def test_definition(self, agent):
        d = agent.definition
        assert d.agent_id == "memory"
        assert d.memory_scope == "global"

    @pytest.mark.asyncio
    async def test_execute_recalls_memories(self, agent):
        result = await agent.execute("Recall context", {"goal": "Get context", "memory_action": "recall"})
        assert result["status"] == "completed"
        assert result["action"] == "recall"

    @pytest.mark.asyncio
    async def test_execute_default_action(self, agent):
        result = await agent.execute("Store info", {"goal": "Save data"})
        assert result["status"] == "completed"


class TestExecutorAgent:
    @pytest.fixture
    def agent(self):
        return ExecutorAgent()

    def test_definition(self, agent):
        d = agent.definition
        assert d.agent_id == "executor"
        assert "dispatch_task" in d.allowed_tools

    @pytest.mark.asyncio
    async def test_execute_runs_actions(self, agent):
        actions = [{"type": "deploy", "description": "Deploy to prod"}]
        result = await agent.execute("Deploy app", {"goal": "Deploy", "actions": actions})
        assert result["status"] == "completed"
        assert len(result["results"]) == 1
        assert result["results"][0]["status"] == "success"
