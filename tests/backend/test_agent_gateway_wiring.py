"""Verify all LLM agents are correctly wired to ModelGateway."""

from __future__ import annotations

import pytest

from app.models.gateway import ModelGateway
from app.agents.builtins.planner_agent import PlannerAgent
from app.agents.builtins.executor_agent import ExecutorAgent
from app.agents.builtins.coder_agent import CoderAgent
from app.agents.builtins.research_agent import ResearchAgent
from app.agents.llm_agent import LLMAgent


class TestAgentGatewayWiring:
    """Verify every LLM agent holds a reference to ModelGateway."""

    @pytest.fixture
    def gateway(self):
        return ModelGateway()

    def test_planner_has_gateway(self, gateway):
        agent = PlannerAgent(gateway=gateway)
        assert agent._gateway is gateway
        assert agent.agent_id == "planner"

    def test_executor_has_gateway(self, gateway):
        agent = ExecutorAgent(gateway=gateway)
        assert agent._gateway is gateway
        assert agent.agent_id == "executor"

    def test_coder_has_gateway(self, gateway):
        agent = CoderAgent(gateway=gateway)
        assert agent._gateway is gateway
        assert agent.agent_id == "coder"

    def test_researcher_has_gateway(self, gateway):
        agent = ResearchAgent(gateway=gateway)
        assert agent._gateway is gateway
        assert agent.agent_id == "researcher"

    def test_llm_agent_has_gateway(self, gateway):
        agent = LLMAgent(agent_id="chat", gateway=gateway)
        assert agent._gateway is gateway

    def test_all_agents_accept_gateway(self, gateway):
        """Smoke test: all 5 agent types can be instantiated with a gateway."""
        agents = [
            PlannerAgent(gateway=gateway),
            ExecutorAgent(gateway=gateway),
            CoderAgent(gateway=gateway),
            ResearchAgent(gateway=gateway),
            LLMAgent(agent_id="chat", gateway=gateway),
        ]
        assert len(agents) == 5
        for agent in agents:
            assert hasattr(agent, "_gateway")
