"""Tests for CapabilityAuditor."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.capability_auditor import (
    AuditReport,
    AgentPerformance,
    CapabilityAuditor,
)
from app.cognitive.context import IntentType


class TestAuditReport:
    def test_to_dict_empty(self):
        report = AuditReport()
        d = report.to_dict()
        assert d["uncovered_intents"] == []
        assert d["low_performing_agents"] == []
        assert d["total_agents"] == 0
        assert d["coverage_ratio"] == 0.0

    def test_to_dict_with_data(self):
        perf = AgentPerformance(agent_id="coder", success_rate=0.45, execution_count=20)
        report = AuditReport(
            uncovered_intents=["META_IMPROVEMENT"],
            low_performing_agents=[perf],
            total_agents=5,
            coverage_ratio=0.6,
            all_intents=["CHAT", "CODE", "META_IMPROVEMENT"],
            registered_agents=["coder", "planner"],
            timestamp="2026-01-01T00:00:00Z",
        )
        d = report.to_dict()
        assert "META_IMPROVEMENT" in d["uncovered_intents"]
        assert len(d["low_performing_agents"]) == 1
        assert d["low_performing_agents"][0]["agent_id"] == "coder"
        assert d["coverage_ratio"] == 0.6


class TestAgentPerformance:
    def test_to_dict(self):
        perf = AgentPerformance(agent_id="researcher", success_rate=0.8, execution_count=50)
        d = perf.to_dict()
        assert d["agent_id"] == "researcher"
        assert d["success_rate"] == 0.8
        assert d["execution_count"] == 50


class TestCapabilityAuditor:
    @pytest.fixture
    def mock_agent_manager(self):
        manager = MagicMock()
        return manager

    @pytest.fixture
    def mock_success_tracker(self):
        tracker = AsyncMock()
        tracker.compute_strategy_effectiveness = AsyncMock(return_value={})
        return tracker

    @pytest.fixture
    def auditor(self, mock_agent_manager, mock_success_tracker):
        return CapabilityAuditor(
            agent_manager=mock_agent_manager,
            success_tracker=mock_success_tracker,
        )

    @pytest.mark.asyncio
    async def test_all_intents_covered(self, auditor, mock_agent_manager):
        """When all intents have matching agents, uncovered_intents should be empty."""
        # Create mock agents for each intent
        mock_agents = []
        for intent in IntentType:
            agent = MagicMock()
            agent.agent_id = intent.value.lower()
            agent.definition = MagicMock()
            agent.definition.role = intent.value.lower()
            agent.definition.allowed_tools = []
            mock_agents.append(agent)
        mock_agent_manager.list_runtime_agents.return_value = mock_agents

        report = await auditor.audit()

        assert report.uncovered_intents == []
        assert report.total_agents == len(IntentType)
        assert report.coverage_ratio == 1.0

    @pytest.mark.asyncio
    async def test_missing_agent_for_intent(self, auditor, mock_agent_manager):
        """IntentType with no agent should appear in uncovered_intents."""
        # Only register agents for some intents
        mock_agents = []
        for intent in [IntentType.CHAT, IntentType.CODE, IntentType.QUESTION]:
            agent = MagicMock()
            agent.agent_id = intent.value.lower()
            agent.definition = MagicMock()
            agent.definition.role = intent.value.lower()
            agent.definition.allowed_tools = []
            mock_agents.append(agent)
        mock_agent_manager.list_runtime_agents.return_value = mock_agents

        report = await auditor.audit()

        assert "META_IMPROVEMENT" not in [a.agent_id for a in []]  # sanity check
        assert report.total_agents == 3
        assert report.coverage_ratio < 1.0
        # META_IMPROVEMENT should be uncovered since no agent handles it
        assert "META_IMPROVEMENT" in report.uncovered_intents

    @pytest.mark.asyncio
    async def test_low_performance_detection(self, auditor, mock_agent_manager, mock_success_tracker):
        """Agents with success_rate < 0.6 should appear in low_performing_agents."""
        mock_agent = MagicMock()
        mock_agent.agent_id = "coder"
        mock_agent.definition = MagicMock()
        mock_agent.definition.role = "coder"
        mock_agent.definition.allowed_tools = []
        mock_agent_manager.list_runtime_agents.return_value = [mock_agent]

        # Mock success tracker to return low success rate for "coder"
        mock_success_tracker.compute_strategy_effectiveness = AsyncMock(
            return_value={"coder": 0.45, "planner": 0.85}
        )

        report = await auditor.audit()

        assert len(report.low_performing_agents) == 1
        assert report.low_performing_agents[0].agent_id == "coder"
        assert report.low_performing_agents[0].success_rate == 0.45

    @pytest.mark.asyncio
    async def test_all_agents_above_threshold(self, auditor, mock_agent_manager, mock_success_tracker):
        """When all agents have success_rate >= 0.6, low_performing_agents should be empty."""
        mock_agent = MagicMock()
        mock_agent.agent_id = "coder"
        mock_agent.definition = MagicMock()
        mock_agent.definition.role = "coder"
        mock_agent.definition.allowed_tools = []
        mock_agent_manager.list_runtime_agents.return_value = [mock_agent]

        mock_success_tracker.compute_strategy_effectiveness = AsyncMock(
            return_value={"coder": 0.75, "planner": 0.90}
        )

        report = await auditor.audit()

        assert report.low_performing_agents == []

    @pytest.mark.asyncio
    async def test_report_completeness(self, auditor, mock_agent_manager, mock_success_tracker):
        """Report should contain all required fields."""
        mock_agent = MagicMock()
        mock_agent.agent_id = "coder"
        mock_agent.definition = MagicMock()
        mock_agent.definition.role = "coder"
        mock_agent.definition.allowed_tools = []
        mock_agent_manager.list_runtime_agents.return_value = [mock_agent]

        mock_success_tracker.compute_strategy_effectiveness = AsyncMock(
            return_value={"coder": 0.8}
        )

        report = await auditor.audit()

        assert hasattr(report, "uncovered_intents")
        assert hasattr(report, "low_performing_agents")
        assert hasattr(report, "total_agents")
        assert hasattr(report, "coverage_ratio")
        assert hasattr(report, "all_intents")
        assert hasattr(report, "registered_agents")
        assert hasattr(report, "timestamp")
        assert isinstance(report.all_intents, list)
        assert len(report.all_intents) == len(IntentType)

    @pytest.mark.asyncio
    async def test_coverage_ratio_calculation(self, auditor, mock_agent_manager):
        """coverage_ratio should be covered_intents / total_intents."""
        # Register agents for 3 out of all intents
        covered_intents = [IntentType.CHAT, IntentType.CODE, IntentType.QUESTION]
        mock_agents = []
        for intent in covered_intents:
            agent = MagicMock()
            agent.agent_id = intent.value.lower()
            agent.definition = MagicMock()
            agent.definition.role = intent.value.lower()
            agent.definition.allowed_tools = []
            mock_agents.append(agent)
        mock_agent_manager.list_runtime_agents.return_value = mock_agents

        report = await auditor.audit()

        total = len(IntentType)
        expected_ratio = len(covered_intents) / total
        assert report.coverage_ratio == pytest.approx(expected_ratio, abs=0.01)

    @pytest.mark.asyncio
    async def test_no_agents_registered(self, auditor, mock_agent_manager):
        """With no agents registered, all intents should be uncovered."""
        mock_agent_manager.list_runtime_agents.return_value = []

        report = await auditor.audit()

        assert report.total_agents == 0
        assert len(report.uncovered_intents) == len(IntentType)
        assert report.coverage_ratio == 0.0

    @pytest.mark.asyncio
    async def test_success_tracker_failure_graceful(self, auditor, mock_agent_manager, mock_success_tracker):
        """If success tracker fails, low_performing_agents should be empty."""
        mock_agent = MagicMock()
        mock_agent.agent_id = "coder"
        mock_agent.definition = MagicMock()
        mock_agent.definition.role = "coder"
        mock_agent.definition.allowed_tools = []
        mock_agent_manager.list_runtime_agents.return_value = [mock_agent]

        mock_success_tracker.compute_strategy_effectiveness = AsyncMock(
            side_effect=Exception("tracker failure")
        )

        report = await auditor.audit()

        assert report.low_performing_agents == []
        assert report.total_agents == 1
