"""Tests for MetaAgent."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.builtins.meta_agent import MetaAgent
from app.agents.capability_auditor import AuditReport, AgentPerformance


class TestMetaAgent:
    @pytest.fixture
    def mock_auditor(self):
        auditor = AsyncMock()
        auditor.audit = AsyncMock(return_value=AuditReport(
            uncovered_intents=["META_IMPROVEMENT"],
            low_performing_agents=[
                AgentPerformance(agent_id="coder", success_rate=0.45, execution_count=20)
            ],
            total_agents=8,
            coverage_ratio=0.75,
            all_intents=["CHAT", "CODE", "META_IMPROVEMENT"],
            registered_agents=["coder", "planner"],
        ))
        return auditor

    @pytest.fixture
    def mock_opencode(self):
        agent = AsyncMock()
        agent.execute = AsyncMock(return_value={
            "status": "completed",
            "response": "Implementation done",
        })
        return agent

    @pytest.fixture
    def meta_agent(self, mock_auditor, mock_opencode):
        return MetaAgent(
            auditor=mock_auditor,
            opencode_agent=mock_opencode,
        )

    def test_definition(self, meta_agent):
        d = meta_agent.definition
        assert d.agent_id == "meta"
        assert d.role == "meta"
        assert "capability_audit" in d.allowed_tools

    @pytest.mark.asyncio
    async def test_execute_evolution_cycle(self, meta_agent, mock_auditor, mock_opencode):
        """Full evolution cycle should audit, create goals, and delegate."""
        result = await meta_agent.execute("run_evolution_cycle", {})

        assert result["status"] == "completed"
        assert len(result["targets"]) > 0
        assert len(result["goals_created"]) > 0
        assert result["audit_report"]["total_agents"] == 8
        mock_auditor.audit.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_unknown_task(self, meta_agent):
        """Unknown task should return error."""
        result = await meta_agent.execute("unknown_task", {})
        assert result["status"] == "error"
        assert "Unknown task" in result["error"]

    @pytest.mark.asyncio
    async def test_no_auditor_returns_error(self):
        """MetaAgent without auditor should return error."""
        agent = MetaAgent(auditor=None)
        result = await agent.execute("run_evolution_cycle", {})
        assert result["status"] == "error"
        assert "CapabilityAuditor not available" in result["error"]

    @pytest.mark.asyncio
    async def test_rank_gaps_ordering(self, meta_agent, mock_auditor):
        """Uncovered intents should rank higher than low-performing agents."""
        report = AuditReport(
            uncovered_intents=["META_IMPROVEMENT", "WORKFLOW"],
            low_performing_agents=[
                AgentPerformance(agent_id="coder", success_rate=0.45, execution_count=20),
            ],
            total_agents=8,
            coverage_ratio=0.75,
            all_intents=[],
            registered_agents=[],
        )

        targets = meta_agent._rank_gaps(report)

        # Uncovered intents should come first
        assert targets[0]["type"] == "uncovered_intent"
        assert targets[1]["type"] == "uncovered_intent"
        assert targets[2]["type"] == "low_performing"

    @pytest.mark.asyncio
    async def test_goals_have_evolving_status(self, meta_agent, mock_auditor):
        """Created goals should have status 'evolving'."""
        result = await meta_agent.execute("run_evolution_cycle", {})

        for goal in result["goals_created"]:
            assert goal["status"] == "evolving"

    @pytest.mark.asyncio
    async def test_opencode_delegation(self, meta_agent, mock_opencode):
        """Should delegate to OpenCodeAgent for each target."""
        result = await meta_agent.execute("run_evolution_cycle", {})

        assert mock_opencode.execute.call_count == len(result["targets"])

    @pytest.mark.asyncio
    async def test_opencode_failure_handled_gracefully(self, mock_auditor):
        """OpenCodeAgent failures should be caught and reported."""
        failing_opencode = AsyncMock()
        failing_opencode.execute = AsyncMock(side_effect=Exception("subprocess failed"))

        agent = MetaAgent(
            auditor=mock_auditor,
            opencode_agent=failing_opencode,
        )

        result = await agent.execute("run_evolution_cycle", {})

        assert result["status"] == "completed"
        assert len(result["improvements"]) > 0
        for imp in result["improvements"]:
            assert imp["result"]["status"] == "error"

    @pytest.mark.asyncio
    async def test_summary_message(self, meta_agent):
        """Summary should contain audit stats."""
        result = await meta_agent.execute("run_evolution_cycle", {})

        assert "uncovered intents" in result["summary"]
        assert "low-performing agents" in result["summary"]
        assert "improvement goals" in result["summary"]
