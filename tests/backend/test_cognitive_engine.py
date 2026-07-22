"""Tests for Cognitive Engine — context, router, decision, engine."""

from __future__ import annotations

from unittest.mock import ANY, AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.cognitive.context import CognitiveContext, IntentType
from app.cognitive.decision import (
    ChatHandler,
    CodeHandler,
    CognitiveDecision,
    DecisionAction,
    FallbackHandler,
    GoalHandler,
    MemoryHandler,
    PlannerHandler,
    ProfileUpdateHandler,
    QuestionHandler,
    ResearchHandler,
    SearchHandler,
    SystemHandler,
    TaskHandler,
    default_handler_registry,
)
from app.cognitive.engine import CognitiveEngine
from app.cognitive.router import CognitiveRouter, IntentDetector, RuleBasedIntentDetector
from app.cognitive.state import CognitiveState


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def mock_goal_manager():
    gm = MagicMock()
    gm.list_goals = AsyncMock(return_value=[])
    gm.create_goal = AsyncMock(return_value={"id": "g1", "title": "test goal"})
    gm.get_next_actions = AsyncMock(return_value=[])
    gm.analyze_progress = AsyncMock(return_value={})
    return gm


@pytest.fixture
def mock_task_manager():
    tm = MagicMock()
    tm.list_tasks = AsyncMock(return_value=[])
    tm.create_task = AsyncMock(return_value={"id": "t1", "goal": "test task"})
    return tm


@pytest.fixture
def mock_agent_manager():
    am = MagicMock()
    am.list_runtime_agents = MagicMock(return_value=[])
    am.get_runtime_agent = MagicMock(return_value=None)
    am.dispatch = AsyncMock(return_value={"status": "completed"})
    return am


@pytest.fixture
def mock_profile_memory():
    pm = MagicMock()
    pm.get_profile = AsyncMock(return_value={"id": "p1", "name": "Test"})
    pm.update_profile = AsyncMock(return_value={"id": "p1", "name": "Test"})
    return pm


@pytest.fixture
def mock_conversation_memory():
    cm = MagicMock()
    cm.get_history = AsyncMock(return_value=[{"role": "user", "content": "hello"}])
    return cm


@pytest.fixture
def engine(
    mock_goal_manager,
    mock_task_manager,
    mock_agent_manager,
    mock_profile_memory,
    mock_conversation_memory,
):
    return CognitiveEngine(
        goal_manager=mock_goal_manager,
        task_manager=mock_task_manager,
        agent_manager=mock_agent_manager,
        profile_memory=mock_profile_memory,
        conversation_memory=mock_conversation_memory,
    )


# ======================================================================
# IntentType enum
# ======================================================================

class TestIntentType:
    def test_has_expected_values(self):
        values = {e.value for e in IntentType}
        assert IntentType.CHAT.value == "CHAT"
        assert IntentType.QUESTION.value == "QUESTION"
        assert IntentType.GOAL.value == "GOAL"
        assert IntentType.TASK.value == "TASK"
        assert IntentType.SEARCH.value == "SEARCH"
        assert IntentType.RESEARCH.value == "RESEARCH"
        assert IntentType.CODE.value == "CODE"
        assert IntentType.MEMORY.value == "MEMORY"
        assert IntentType.PROFILE_UPDATE.value == "PROFILE_UPDATE"
        assert IntentType.SYSTEM.value == "SYSTEM"
        assert IntentType.PLAN.value == "PLAN"
        assert IntentType.REASON.value == "REASON"
        assert IntentType.KNOWLEDGE_GRAPH.value == "KNOWLEDGE_GRAPH"

    def test_all_14_intents(self):
        assert len(IntentType) == 14


# ======================================================================
# CognitiveContext
# ======================================================================

class TestCognitiveContext:
    def test_default_construction(self):
        ctx = CognitiveContext(raw_input="hello")
        assert ctx.raw_input == "hello"
        assert ctx.user_id is None
        assert ctx.session_id is None
        assert ctx.intent == IntentType.CHAT
        assert ctx.confidence == 0.0
        assert ctx.conversation_history == []
        assert ctx.user_profile is None
        assert ctx.goals == []
        assert ctx.pending_tasks == []
        assert ctx.running_tasks == []
        assert ctx.agent_registry == []
        assert ctx.extra == {}

    def test_full_construction(self):
        ctx = CognitiveContext(
            raw_input="test",
            user_id="u1",
            session_id="s1",
            intent=IntentType.QUESTION,
            confidence=0.9,
            conversation_history=[{"role": "user", "content": "hi"}],
            user_profile={"name": "Tester"},
            goals=[{"id": "g1"}],
            pending_tasks=[{"id": "t1", "status": "QUEUED"}],
            running_tasks=[{"id": "t2", "status": "RUNNING"}],
            agent_registry=["assistant", "coder"],
            extra={"source": "api"},
        )
        assert ctx.intent == IntentType.QUESTION
        assert ctx.user_profile["name"] == "Tester"


# ======================================================================
# CognitiveState
# ======================================================================

class TestCognitiveState:
    def test_default_state(self):
        s = CognitiveState()
        assert s.context is not None
        assert s.context.raw_input == ""
        assert s.decision is None
        assert s.execution_result is None
        assert s.error is None

    def test_filled_state(self):
        ctx = CognitiveContext(raw_input="hi")
        dec = CognitiveDecision(action=DecisionAction.ROUTE_TO_KERNEL)
        s = CognitiveState(context=ctx, decision=dec, execution_result={"ok": True})
        assert s.context is ctx
        assert s.decision is dec
        assert s.execution_result == {"ok": True}


# ======================================================================
# CognitiveDecision
# ======================================================================

class TestCognitiveDecision:
    def test_defaults(self):
        d = CognitiveDecision()
        assert d.action == DecisionAction.FALLBACK
        assert d.handler_name == "fallback"
        assert d.payload == {}
        assert d.confidence == 0.0
        assert d.reasoning == ""

    def test_to_dict(self):
        d = CognitiveDecision(
            action=DecisionAction.CREATE_GOAL,
            handler_name="goal",
            payload={"title": "test"},
            confidence=0.8,
            reasoning="test reason",
        )
        dd = d.to_dict()
        assert dd["action"] == "CREATE_GOAL"
        assert dd["handler"] == "goal"
        assert dd["payload"] == {"title": "test"}
        assert dd["confidence"] == 0.8
        assert dd["reasoning"] == "test reason"

    def test_decision_action_values(self):
        assert DecisionAction.ANSWER_DIRECTLY.value == "ANSWER_DIRECTLY"
        assert DecisionAction.UPDATE_PROFILE.value == "UPDATE_PROFILE"
        assert DecisionAction.CREATE_GOAL.value == "CREATE_GOAL"
        assert DecisionAction.CREATE_TASK.value == "CREATE_TASK"
        assert DecisionAction.CREATE_PLAN.value == "CREATE_PLAN"
        assert DecisionAction.REASON.value == "REASON"
        assert DecisionAction.ROUTE_TO_KERNEL.value == "ROUTE_TO_KERNEL"
        assert DecisionAction.FALLBACK.value == "FALLBACK"


# ======================================================================
# DecisionHandler implementations
# ======================================================================

class TestHandlers:
    @pytest.mark.asyncio
    async def test_chat_handler_routes_to_kernel(self):
        handler = ChatHandler()
        assert handler.handled_intents == {IntentType.CHAT}
        ctx = CognitiveContext(raw_input="hello", session_id="s1")
        dec = await handler.decide(ctx)
        assert dec.action == DecisionAction.ROUTE_TO_KERNEL
        assert dec.confidence == 0.9

    @pytest.mark.asyncio
    async def test_question_handler_routes_to_kernel(self):
        handler = QuestionHandler()
        ctx = CognitiveContext(raw_input="what is quantum computing?")
        dec = await handler.decide(ctx)
        assert dec.action == DecisionAction.ROUTE_TO_KERNEL
        assert dec.confidence == 0.85

    @pytest.mark.asyncio
    async def test_goal_handler_creates_goal(self):
        handler = GoalHandler()
        ctx = CognitiveContext(raw_input="I want to learn Python")
        dec = await handler.decide(ctx)
        assert dec.action == DecisionAction.CREATE_GOAL
        assert dec.payload["delegate_to"] == "planner"
        assert dec.confidence == 0.8

    @pytest.mark.asyncio
    async def test_task_handler_creates_task(self):
        handler = TaskHandler()
        ctx = CognitiveContext(raw_input="search for AI papers")
        dec = await handler.decide(ctx)
        assert dec.action == DecisionAction.CREATE_TASK
        assert dec.payload["assigned_agent"] == "researcher"

    @pytest.mark.asyncio
    async def test_task_handler_suggests_coder(self):
        handler = TaskHandler()
        ctx = CognitiveContext(raw_input="write a REST API in Python")
        dec = await handler.decide(ctx)
        assert dec.payload["assigned_agent"] == "coder"

    @pytest.mark.asyncio
    async def test_search_handler_delegates(self):
        handler = SearchHandler()
        ctx = CognitiveContext(raw_input="search for climate data")
        dec = await handler.decide(ctx)
        assert dec.action == DecisionAction.DELEGATE_TO_RESEARCHER

    @pytest.mark.asyncio
    async def test_research_handler_delegates(self):
        handler = ResearchHandler()
        ctx = CognitiveContext(raw_input="research quantum computing")
        dec = await handler.decide(ctx)
        assert dec.action == DecisionAction.DELEGATE_TO_RESEARCHER

    @pytest.mark.asyncio
    async def test_code_handler_delegates(self):
        handler = CodeHandler()
        ctx = CognitiveContext(raw_input="write a fibonacci function")
        dec = await handler.decide(ctx)
        assert dec.action == DecisionAction.DELEGATE_TO_CODER

    @pytest.mark.asyncio
    async def test_memory_handler_delegates(self):
        handler = MemoryHandler()
        ctx = CognitiveContext(raw_input="remember my birthday is Jan 1")
        dec = await handler.decide(ctx)
        assert dec.action == DecisionAction.DELEGATE_TO_MEMORY

    @pytest.mark.asyncio
    async def test_profile_update_handler_updates(self):
        handler = ProfileUpdateHandler()
        ctx = CognitiveContext(raw_input="my name is Alice")
        dec = await handler.decide(ctx)
        assert dec.action == DecisionAction.UPDATE_PROFILE

    @pytest.mark.asyncio
    async def test_system_handler_routes_to_kernel(self):
        handler = SystemHandler()
        ctx = CognitiveContext(raw_input="system status")
        dec = await handler.decide(ctx)
        assert dec.action == DecisionAction.ROUTE_TO_KERNEL
        assert dec.confidence == 0.95

    @pytest.mark.asyncio
    async def test_fallback_handler_returns_fallback(self):
        handler = FallbackHandler()
        ctx = CognitiveContext(raw_input="")
        dec = await handler.decide(ctx)
        assert dec.action == DecisionAction.FALLBACK
        assert dec.confidence == 0.3

    @pytest.mark.asyncio
    async def test_plan_handler_creates_plan(self):
        handler = PlannerHandler()
        ctx = CognitiveContext(raw_input="build a landing page")
        dec = await handler.decide(ctx)
        assert dec.action == DecisionAction.CREATE_PLAN
        assert dec.payload["objective"] == "build a landing page"
        assert dec.confidence == 0.8


class TestDefaultHandlerRegistry:
    def test_has_all_14_intents(self):
        registry = default_handler_registry()
        all_intents = {IntentType.CHAT, IntentType.QUESTION, IntentType.GOAL,
                       IntentType.TASK, IntentType.SEARCH, IntentType.RESEARCH,
                       IntentType.CODE, IntentType.MEMORY, IntentType.PROFILE_UPDATE,
                       IntentType.SYSTEM, IntentType.PLAN, IntentType.REASON,
                       IntentType.WORKFLOW, IntentType.KNOWLEDGE_GRAPH}
        assert set(registry.keys()) == all_intents


# ======================================================================
# IntentDetector / Router
# ======================================================================

class TestRuleBasedIntentDetector:
    @pytest.mark.asyncio
    async def test_detect_chat_greeting(self):
        detector = RuleBasedIntentDetector()
        intent, conf = await detector.detect(CognitiveContext(raw_input="hello"))
        assert intent == IntentType.CHAT
        assert conf > 0

    @pytest.mark.asyncio
    async def test_detect_question(self):
        detector = RuleBasedIntentDetector()
        intent, conf = await detector.detect(CognitiveContext(raw_input="what is the meaning of life?"))
        assert intent == IntentType.QUESTION
        assert conf > 0

    @pytest.mark.asyncio
    async def test_detect_goal(self):
        detector = RuleBasedIntentDetector()
        intent, conf = await detector.detect(CognitiveContext(raw_input="i want to learn spanish"))
        assert intent == IntentType.GOAL

    @pytest.mark.asyncio
    async def test_detect_task(self):
        detector = RuleBasedIntentDetector()
        intent, conf = await detector.detect(CognitiveContext(raw_input="create a task for code review"))
        assert intent == IntentType.TASK

    @pytest.mark.asyncio
    async def test_detect_search(self):
        detector = RuleBasedIntentDetector()
        intent, conf = await detector.detect(CognitiveContext(raw_input="search for python tutorials"))
        assert intent == IntentType.SEARCH

    @pytest.mark.asyncio
    async def test_detect_research(self):
        detector = RuleBasedIntentDetector()
        intent, conf = await detector.detect(CognitiveContext(raw_input="research about machine learning"))
        assert intent == IntentType.RESEARCH

    @pytest.mark.asyncio
    async def test_detect_code(self):
        detector = RuleBasedIntentDetector()
        intent, conf = await detector.detect(CognitiveContext(raw_input="write code for a python script"))
        assert intent == IntentType.CODE

    @pytest.mark.asyncio
    async def test_detect_memory(self):
        detector = RuleBasedIntentDetector()
        intent, conf = await detector.detect(CognitiveContext(raw_input="do you remember my name"))
        assert intent == IntentType.MEMORY

    @pytest.mark.asyncio
    async def test_detect_profile_update(self):
        detector = RuleBasedIntentDetector()
        intent, conf = await detector.detect(CognitiveContext(raw_input="my name is Bob"))
        assert intent == IntentType.PROFILE_UPDATE

    @pytest.mark.asyncio
    async def test_detect_system(self):
        detector = RuleBasedIntentDetector()
        intent, conf = await detector.detect(CognitiveContext(raw_input="system status check"))
        assert intent == IntentType.SYSTEM

    @pytest.mark.asyncio
    async def test_detect_plan(self):
        detector = RuleBasedIntentDetector()
        intent, conf = await detector.detect(CognitiveContext(raw_input="build a landing page"))
        assert intent == IntentType.PLAN
        assert conf > 0

    @pytest.mark.asyncio
    async def test_empty_input_falls_to_chat(self):
        detector = RuleBasedIntentDetector()
        intent, conf = await detector.detect(CognitiveContext(raw_input=""))
        assert intent == IntentType.CHAT


class TestCognitiveRouter:
    @pytest.mark.asyncio
    async def test_route_with_default_detector(self):
        router = CognitiveRouter(handlers=default_handler_registry())
        ctx = CognitiveContext(raw_input="hello")
        dec = await router.route(ctx)
        # The default detector + handler for CHAT
        assert dec.action in (DecisionAction.ROUTE_TO_KERNEL, DecisionAction.FALLBACK)

    @pytest.mark.asyncio
    async def test_route_question_to_kernel(self):
        router = CognitiveRouter(handlers=default_handler_registry())
        ctx = CognitiveContext(raw_input="what is AI?")
        dec = await router.route(ctx)
        assert dec.action == DecisionAction.ROUTE_TO_KERNEL

    @pytest.mark.asyncio
    async def test_route_goal_creates_goal(self):
        router = CognitiveRouter(handlers=default_handler_registry())
        ctx = CognitiveContext(raw_input="i want to build a startup")
        dec = await router.route(ctx)
        assert dec.action == DecisionAction.CREATE_GOAL

    @pytest.mark.asyncio
    async def test_custom_detector(self):
        mock_detector = MagicMock(spec=IntentDetector)
        mock_detector.detect = AsyncMock(return_value=(IntentType.CHAT, 0.9))
        router = CognitiveRouter(
            detector=mock_detector,
            handlers=default_handler_registry(),
        )
        ctx = CognitiveContext(raw_input="anything")
        dec = await router.route(ctx)
        assert dec.action == DecisionAction.ROUTE_TO_KERNEL

    @pytest.mark.asyncio
    async def test_register_handler(self):
        router = CognitiveRouter(handlers={})
        handler = ChatHandler()
        router.register_handler(IntentType.CHAT, handler)
        assert router.handlers[IntentType.CHAT] is handler

    @pytest.mark.asyncio
    async def test_unregister_handler(self):
        router = CognitiveRouter(handlers=default_handler_registry())
        router.unregister_handler(IntentType.CHAT)
        assert IntentType.CHAT not in router.handlers


# ======================================================================
# CognitiveEngine
# ======================================================================

class TestCognitiveEngine:
    @pytest.mark.asyncio
    async def test_process_chat_returns_state(self, engine):
        state = await engine.process(raw_input="hello", user_id=None)
        assert isinstance(state, CognitiveState)
        assert state.context is not None
        assert state.decision is not None
        assert state.error is None

    @pytest.mark.asyncio
    async def test_process_question_routes_to_kernel(self, engine):
        state = await engine.process(raw_input="what is python?")
        assert state.decision.action == DecisionAction.ROUTE_TO_KERNEL

    @pytest.mark.asyncio
    async def test_process_goal_creates_goal(self, engine):
        state = await engine.process(raw_input="i want to learn rust", user_id=str(uuid4()))
        assert state.decision.action == DecisionAction.CREATE_GOAL

    @pytest.mark.asyncio
    async def test_process_error_creates_fallback(self, engine):
        # Force an error by making list_runtime_agents raise
        engine._agent_manager.list_runtime_agents = MagicMock(side_effect=ValueError("boom"))
        state = await engine.process(raw_input="hello")
        assert state.error is not None
        assert state.decision.action == DecisionAction.FALLBACK

    @pytest.mark.asyncio
    async def test_load_context_includes_agent_registry(self, engine):
        state = await engine.process(raw_input="hello")
        assert state.context.agent_registry == []

    @pytest.mark.asyncio
    async def test_load_context_with_user_id(self, engine):
        uid = str(uuid4())
        state = await engine.process(raw_input="hello", user_id=uid)
        ctx = state.context
        assert ctx.user_id == uid
        # profile should be loaded if available
        assert ctx.user_profile is not None

    @pytest.mark.asyncio
    async def test_execute_create_goal(self, engine, mock_goal_manager):
        ctx = CognitiveContext(raw_input="i want to travel", user_id=str(uuid4()))
        decision = CognitiveDecision(
            action=DecisionAction.CREATE_GOAL,
            handler_name="goal",
            payload={"title": "travel more"},
        )
        result = await engine._execute_decision(decision, ctx)
        assert result is not None
        assert "created_goal" in result
        mock_goal_manager.create_goal.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_create_task(self, engine, mock_task_manager):
        ctx = CognitiveContext(raw_input="write code")
        decision = CognitiveDecision(
            action=DecisionAction.CREATE_TASK,
            handler_name="task",
            payload={"goal": "write a script", "assigned_agent": "coder"},
        )
        result = await engine._execute_decision(decision, ctx)
        assert result is not None
        assert "created_task" in result
        mock_task_manager.create_task.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_profile_update(self, engine, mock_profile_memory):
        ctx = CognitiveContext(raw_input="my name is Alice", user_id=str(uuid4()))
        decision = CognitiveDecision(
            action=DecisionAction.UPDATE_PROFILE,
            handler_name="profile_update",
            payload={"user_id": ctx.user_id, "input": ctx.raw_input},
        )
        result = await engine._execute_decision(decision, ctx)
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_delegate_requires_runtime_agent(self, engine):
        ctx = CognitiveContext(raw_input="research AI")
        decision = CognitiveDecision(
            action=DecisionAction.DELEGATE_TO_RESEARCHER,
            handler_name="research",
            payload={"task": "research AI"},
        )
        result = await engine._execute_decision(decision, ctx)
        assert result is not None
        assert "error" in result  # no agent registered

    @pytest.mark.asyncio
    async def test_execute_none_for_kernel_actions(self, engine):
        ctx = CognitiveContext(raw_input="hello")
        decision = CognitiveDecision(action=DecisionAction.ROUTE_TO_KERNEL)
        result = await engine._execute_decision(decision, ctx)
        assert result is None

    @pytest.mark.asyncio
    async def test_run_full_cycle_with_user(self, engine):
        uid = str(uuid4())
        state = await engine.process(
            raw_input="i want to build a mobile app",
            user_id=uid,
            session_id=str(uuid4()),
        )
        assert state.context is not None
        assert state.decision is not None
        assert state.decision.action == DecisionAction.CREATE_GOAL
        assert state.execution_result is not None
        assert "created_goal" in state.execution_result

    @pytest.mark.asyncio
    async def test_state_property(self, engine):
        assert engine.state is None
        await engine.process(raw_input="hello")
        assert engine.state is not None
        assert engine.state is engine.state  # same reference
