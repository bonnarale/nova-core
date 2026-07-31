"""Integration test: full meta cycle from CognitiveEngine → EvolutionEngine → MetaAgent → ImprovementGoals."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.agent_manager import AgentManager
from app.agents.builtins.meta_agent import MetaAgent
from app.agents.capability_auditor import CapabilityAuditor
from app.cognitive.engine import CognitiveEngine
from app.cognitive.context import IntentType
from app.cognitive.decision import DecisionAction
from app.learning.evolution_engine import EvolutionEngine
from app.learning.outcome_tracker import InMemoryOutcomeStore
from app.learning.success_tracker import SuccessTracker
from app.memory.conversation_memory import ConversationMemory
from app.memory.goals import GoalManager
from app.memory.profile import UserProfileMemory
from app.orchestrator.task_manager import TaskManager


class TestMetaCycleIntegration:
    """End-to-end integration test for the meta-improvement cycle.

    Verifies: CognitiveEngine → EvolutionEngine → MetaAgent → CapabilityAuditor → ImprovementGoals
    """

    @pytest.fixture
    def components(self):
        """Wire up real components with minimal mocks."""
        # Real components
        store = InMemoryOutcomeStore()
        success_tracker = SuccessTracker(store=store)
        agent_manager = AgentManager()
        auditor = CapabilityAuditor(
            agent_manager=agent_manager,
            success_tracker=success_tracker,
        )
        meta_agent = MetaAgent(auditor=auditor)

        # Mock event bus
        event_bus = AsyncMock()
        event_bus.emit = AsyncMock()

        # EvolutionEngine with real MetaAgent
        evolution_engine = EvolutionEngine(
            bus=event_bus,
            meta_agent=meta_agent,
            min_tasks_between_cycles=0,  # No rate limiting for test
        )

        # Mock dependencies for CognitiveEngine
        goal_manager = MagicMock(spec=GoalManager)
        goal_manager.list_goals = AsyncMock(return_value=[])
        goal_manager.create_goal = AsyncMock(return_value={"id": "goal-1", "title": "test"})

        task_manager = MagicMock(spec=TaskManager)
        task_manager.list_tasks = AsyncMock(return_value=[])

        profile_memory = MagicMock(spec=UserProfileMemory)
        profile_memory.get_profile = AsyncMock(return_value=None)

        conversation_memory = MagicMock(spec=ConversationMemory)
        conversation_memory.get_history = AsyncMock(return_value=[])

        # CognitiveEngine with real EvolutionEngine
        cognitive_engine = CognitiveEngine(
            goal_manager=goal_manager,
            task_manager=task_manager,
            agent_manager=agent_manager,
            profile_memory=profile_memory,
            conversation_memory=conversation_memory,
            event_publisher=event_bus,
            evolution_engine=evolution_engine,
        )

        return {
            "cognitive_engine": cognitive_engine,
            "evolution_engine": evolution_engine,
            "meta_agent": meta_agent,
            "auditor": auditor,
            "success_tracker": success_tracker,
            "agent_manager": agent_manager,
        }

    @pytest.mark.asyncio
    async def test_full_meta_cycle_from_input(self, components):
        """Test full flow: user input → CognitiveEngine → EvolutionEngine → MetaAgent → results."""
        cognitive_engine = components["cognitive_engine"]

        # Run cognitive cycle with meta-improvement request (use valid UUID)
        state = await cognitive_engine.process(
            raw_input="run a capability audit and improve agents",
            user_id="550e8400-e29b-41d4-a716-446655440000",
        )

        # Verify intent was detected
        assert state.context is not None
        assert state.context.intent == IntentType.META_IMPROVEMENT

        # Verify decision was made
        assert state.decision is not None
        assert state.decision.action == DecisionAction.RUN_META_CYCLE

        # Verify execution result contains evolution cycle results
        assert state.execution_result is not None
        result = state.execution_result
        assert "evolution_cycle" in result

        cycle_result = result["evolution_cycle"]
        assert cycle_result["status"] == "completed"
        assert cycle_result["result"] is not None

        # Verify MetaAgent was called and returned audit results
        meta_result = cycle_result["result"]
        assert meta_result["agent"] == "meta"
        assert meta_result["status"] == "completed"
        assert "audit_report" in meta_result
        assert "targets" in meta_result
        assert "goals_created" in meta_result

    @pytest.mark.asyncio
    async def test_meta_cycle_detects_uncovered_intents(self, components):
        """Verify CapabilityAuditor detects intents without agents."""
        agent_manager = components["agent_manager"]
        auditor = components["auditor"]

        # Run audit directly
        report = await auditor.audit()

        # Should have uncovered intents (most intents have no agent)
        assert len(report.uncovered_intents) > 0
        assert report.total_agents >= 0
        assert 0.0 <= report.coverage_ratio <= 1.0

    @pytest.mark.asyncio
    async def test_evolution_engine_wired_correctly(self, components):
        """Verify EvolutionEngine is properly wired into CognitiveEngine."""
        cognitive_engine = components["cognitive_engine"]
        evolution_engine = components["evolution_engine"]

        # CognitiveEngine should have the evolution engine
        assert cognitive_engine._evolution_engine is evolution_engine

        # EvolutionEngine should have the meta agent
        assert evolution_engine._meta_agent is components["meta_agent"]

    @pytest.mark.asyncio
    async def test_meta_cycle_publishes_events(self, components):
        """Verify EvolutionEngine publishes events during cycle."""
        evolution_engine = components["evolution_engine"]

        # Run evolution cycle directly (bypass CognitiveEngine)
        await evolution_engine.run_evolution_cycle()

        # Verify events were published
        event_bus = evolution_engine._bus
        assert event_bus.emit.call_count >= 2  # started + completed

        # Check event types
        event_types = [call.args[0] for call in event_bus.emit.call_args_list]
        assert "evolution_cycle_started" in event_types
        assert "evolution_cycle_completed" in event_types

    @pytest.mark.asyncio
    async def test_meta_cycle_history_recorded(self, components):
        """Verify EvolutionEngine records cycle history."""
        evolution_engine = components["evolution_engine"]

        # Run cycle directly
        await evolution_engine.run_evolution_cycle()

        # Check history
        history = evolution_engine.get_history()
        assert len(history) == 1
        assert history[0]["status"] == "completed"
        assert "cycle_id" in history[0]
