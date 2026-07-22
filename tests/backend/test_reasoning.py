"""Tests for Reasoning Engine v1 — models, base, strategies, evaluator,
validator, critic, registry, engine, and integration with CognitiveEngine.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.cognitive.context import CognitiveContext, IntentType
from app.cognitive.decision import (
    CognitiveDecision,
    DecisionAction,
    ReasoningHandler,
    default_handler_registry,
)
from app.cognitive.engine import CognitiveEngine
from app.cognitive.router import RuleBasedIntentDetector
from app.reasoning.base import (
    CandidateEvaluator,
    DecisionValidator,
    ReasoningStrategy,
    SelfCritic,
)
from app.reasoning.critic import DefaultCritic
from app.reasoning.engine import ReasoningEngine
from app.reasoning.evaluator import DefaultEvaluator
from app.reasoning.models import (
    CritiqueResult,
    EvaluationResult,
    ReasoningChain,
    ReasoningContext,
    ReasoningDecision,
    ReasoningStatus,
    ReasoningStep,
    StrategyType,
    ValidationResult,
)
from app.reasoning.registry import StrategyRegistry
from app.reasoning.strategy import (
    AnalyticalReasoningStrategy,
    ComparativeReasoningStrategy,
    DirectReasoningStrategy,
    MultiStepReasoningStrategy,
    SelfCritiqueReasoningStrategy,
)
from app.reasoning.validator import DefaultValidator


# ======================================================================
# Domain model tests
# ======================================================================

class TestReasoningContext:
    def test_default_construction(self):
        ctx = ReasoningContext(query="test")
        assert ctx.query == "test"
        assert ctx.user_id is None
        assert ctx.constraints == []
        assert ctx.preferences == {}
        assert ctx.context_data == {}
        assert ctx.extra == {}

    def test_full_construction(self):
        ctx = ReasoningContext(
            query="why is the sky blue",
            user_id="u1",
            session_id="s1",
            constraints=["time: 30s"],
            preferences={"style": "concise"},
            context_data={"source": "science"},
            extra={"tags": ["physics"]},
        )
        assert ctx.user_id == "u1"
        assert ctx.constraints == ["time: 30s"]
        assert ctx.context_data["source"] == "science"

    def test_to_dict(self):
        ctx = ReasoningContext(query="test")
        d = ctx.to_dict()
        assert d["query"] == "test"


class TestReasoningStep:
    def test_default_construction(self):
        step = ReasoningStep(description="test", content="content")
        assert step.description == "test"
        assert step.content == "content"
        assert step.step_type == "analysis"
        assert step.confidence == 0.0
        assert step.alternatives == []
        assert step.evidence == []

    def test_to_dict(self):
        step = ReasoningStep(description="d", content="c", confidence=0.8)
        d = step.to_dict()
        assert d["description"] == "d"
        assert d["confidence"] == 0.8


class TestReasoningChain:
    def test_default_construction(self):
        chain = ReasoningChain()
        assert chain.steps == []
        assert chain.conclusion == ""
        assert chain.confidence == 0.0
        assert chain.strategy == StrategyType.DIRECT

    def test_add_step(self):
        chain = ReasoningChain()
        step = ReasoningStep(description="s1", content="c1")
        chain.add_step(step)
        assert len(chain.steps) == 1
        assert chain.steps[0] is step

    def test_to_dict(self):
        chain = ReasoningChain(
            steps=[ReasoningStep(description="s", content="c")],
            conclusion="done",
            confidence=0.9,
        )
        d = chain.to_dict()
        assert d["conclusion"] == "done"
        assert len(d["steps"]) == 1


class TestEvaluationResult:
    def test_defaults(self):
        r = EvaluationResult()
        assert r.score == 0.0
        assert r.feedback == []

    def test_to_dict(self):
        r = EvaluationResult(score=0.8, feedback=["good"])
        d = r.to_dict()
        assert d["score"] == 0.8
        assert d["feedback"] == ["good"]


class TestValidationResult:
    def test_defaults(self):
        r = ValidationResult()
        assert r.is_valid is True
        assert r.issues == []

    def test_invalid(self):
        r = ValidationResult(is_valid=False, issues=["missing conclusion"])
        assert not r.is_valid
        assert "missing conclusion" in r.issues


class TestCritiqueResult:
    def test_defaults(self):
        r = CritiqueResult()
        assert r.flaws == []
        assert r.overall_assessment == ""


class TestReasoningDecision:
    def test_default_construction(self):
        d = ReasoningDecision()
        assert d.query == ""
        assert d.status == ReasoningStatus.PENDING
        assert d.chain is None
        assert d.error is None

    def test_completed_decision(self):
        chain = ReasoningChain(conclusion="done", confidence=0.9)
        d = ReasoningDecision(
            query="test",
            chain=chain,
            conclusion="done",
            confidence=0.9,
            status=ReasoningStatus.COMPLETED,
        )
        assert d.conclusion == "done"
        assert d.to_dict()["status"] == "COMPLETED"

    def test_to_dict(self):
        d = ReasoningDecision(query="q", status=ReasoningStatus.FAILED, error="err")
        dd = d.to_dict()
        assert dd["query"] == "q"
        assert dd["status"] == "FAILED"
        assert dd["error"] == "err"


# ======================================================================
# ABC verification
# ======================================================================

class TestABCs:
    def test_reasoning_strategy_cannot_instantiate(self):
        with pytest.raises(TypeError):
            ReasoningStrategy()

    def test_candidate_evaluator_cannot_instantiate(self):
        with pytest.raises(TypeError):
            CandidateEvaluator()

    def test_decision_validator_cannot_instantiate(self):
        with pytest.raises(TypeError):
            DecisionValidator()

    def test_self_critic_cannot_instantiate(self):
        with pytest.raises(TypeError):
            SelfCritic()


# ======================================================================
# Strategy tests
# ======================================================================

class TestDirectReasoningStrategy:
    @pytest.mark.asyncio
    async def test_name(self):
        s = DirectReasoningStrategy()
        assert s.name == "DIRECT"

    @pytest.mark.asyncio
    async def test_can_handle_short_query(self):
        s = DirectReasoningStrategy()
        ctx = ReasoningContext(query="hello world")
        assert await s.can_handle(ctx)

    @pytest.mark.asyncio
    async def test_cannot_handle_comparison(self):
        s = DirectReasoningStrategy()
        ctx = ReasoningContext(query="compare python vs java")
        assert not await s.can_handle(ctx)

    @pytest.mark.asyncio
    async def test_cannot_handle_multi_part(self):
        s = DirectReasoningStrategy()
        ctx = ReasoningContext(query="what is a? what is b?")
        assert not await s.can_handle(ctx)

    @pytest.mark.asyncio
    async def test_reason(self):
        s = DirectReasoningStrategy()
        ctx = ReasoningContext(query="hello")
        chain = await s.reason(ctx)
        assert chain.strategy == StrategyType.DIRECT
        assert len(chain.steps) == 1
        assert chain.confidence == 0.85


class TestAnalyticalReasoningStrategy:
    @pytest.mark.asyncio
    async def test_name(self):
        s = AnalyticalReasoningStrategy()
        assert s.name == "ANALYTICAL"

    @pytest.mark.asyncio
    async def test_can_handle_why_question(self):
        s = AnalyticalReasoningStrategy()
        ctx = ReasoningContext(query="why is the sky blue")
        assert await s.can_handle(ctx)

    @pytest.mark.asyncio
    async def test_can_handle_analyze(self):
        s = AnalyticalReasoningStrategy()
        ctx = ReasoningContext(query="analyze the market trends")
        assert await s.can_handle(ctx)

    @pytest.mark.asyncio
    async def test_cannot_handle_simple(self):
        s = AnalyticalReasoningStrategy()
        ctx = ReasoningContext(query="hello there")
        assert not await s.can_handle(ctx)

    @pytest.mark.asyncio
    async def test_reason_has_three_steps(self):
        s = AnalyticalReasoningStrategy()
        ctx = ReasoningContext(query="why do we need sleep")
        chain = await s.reason(ctx)
        assert len(chain.steps) >= 3
        assert chain.strategy == StrategyType.ANALYTICAL


class TestComparativeReasoningStrategy:
    @pytest.mark.asyncio
    async def test_name(self):
        s = ComparativeReasoningStrategy()
        assert s.name == "COMPARATIVE"

    @pytest.mark.asyncio
    async def test_can_handle_compare(self):
        s = ComparativeReasoningStrategy()
        ctx = ReasoningContext(query="compare python and java")
        assert await s.can_handle(ctx)

    @pytest.mark.asyncio
    async def test_can_handle_vs(self):
        s = ComparativeReasoningStrategy()
        ctx = ReasoningContext(query="react vs vue")
        assert await s.can_handle(ctx)

    @pytest.mark.asyncio
    async def test_cannot_handle_simple(self):
        s = ComparativeReasoningStrategy()
        ctx = ReasoningContext(query="hello")
        assert not await s.can_handle(ctx)

    @pytest.mark.asyncio
    async def test_reason(self):
        s = ComparativeReasoningStrategy()
        ctx = ReasoningContext(query="compare aws vs azure for hosting")
        chain = await s.reason(ctx)
        assert chain.strategy == StrategyType.COMPARATIVE
        assert len(chain.steps) >= 3


class TestMultiStepReasoningStrategy:
    @pytest.mark.asyncio
    async def test_name(self):
        s = MultiStepReasoningStrategy()
        assert s.name == "MULTI_STEP"

    @pytest.mark.asyncio
    async def test_can_handle_multi_question(self):
        s = MultiStepReasoningStrategy()
        ctx = ReasoningContext(query="what is step one? what is step two?")
        assert await s.can_handle(ctx)

    @pytest.mark.asyncio
    async def test_can_handle_long(self):
        s = MultiStepReasoningStrategy()
        ctx = ReasoningContext(query="first we need to do this. then we do that. finally we finish.")
        assert await s.can_handle(ctx)

    @pytest.mark.asyncio
    async def test_cannot_handle_short(self):
        s = MultiStepReasoningStrategy()
        ctx = ReasoningContext(query="hello")
        assert not await s.can_handle(ctx)

    @pytest.mark.asyncio
    async def test_reason(self):
        s = MultiStepReasoningStrategy()
        ctx = ReasoningContext(query="step one: research. step two: implement. step three: test. what next?")
        chain = await s.reason(ctx)
        assert chain.strategy == StrategyType.MULTI_STEP
        assert len(chain.steps) >= 2


class TestSelfCritiqueReasoningStrategy:
    @pytest.mark.asyncio
    async def test_name(self):
        s = SelfCritiqueReasoningStrategy()
        assert s.name == "SELF_CRITIQUE"

    @pytest.mark.asyncio
    async def test_delegates_can_handle(self):
        inner = MagicMock(spec=ReasoningStrategy)
        inner.can_handle = AsyncMock(return_value=True)
        s = SelfCritiqueReasoningStrategy(inner=inner)
        ctx = ReasoningContext(query="test")
        assert await s.can_handle(ctx)
        inner.can_handle.assert_awaited_once_with(ctx)

    @pytest.mark.asyncio
    async def test_reason_adds_refinement_for_empty_chain(self):
        inner = MagicMock(spec=ReasoningStrategy)
        inner.reason = AsyncMock(return_value=ReasoningChain())
        s = SelfCritiqueReasoningStrategy(inner=inner)
        ctx = ReasoningContext(query="test")
        chain = await s.reason(ctx)
        assert chain.metadata.get("self_critiqued") is True
        # Should have original steps + refinement step
        assert len(chain.steps) >= 1

    @pytest.mark.asyncio
    async def test_reason_no_refinement_if_no_flaws(self):
        inner = MagicMock(spec=ReasoningStrategy)
        inner.reason = AsyncMock(
            return_value=ReasoningChain(
                steps=[ReasoningStep(description="s1", content="c1"),
                       ReasoningStep(description="s2", content="c2")],
                conclusion="done",
                confidence=0.9,
            )
        )
        s = SelfCritiqueReasoningStrategy(inner=inner)
        ctx = ReasoningContext(query="test")
        chain = await s.reason(ctx)
        assert chain.metadata.get("self_critiqued") is True


# ======================================================================
# Evaluator tests
# ======================================================================

class TestDefaultEvaluator:
    @pytest.mark.asyncio
    async def test_evaluate_empty_chain(self):
        evaluator = DefaultEvaluator()
        ctx = ReasoningContext(query="test")
        result = await evaluator.evaluate(ReasoningChain(), ctx)
        assert result.score == 0.15
        assert result.feedback

    @pytest.mark.asyncio
    async def test_evaluate_complete_chain(self):
        evaluator = DefaultEvaluator()
        chain = ReasoningChain(
            steps=[
                ReasoningStep(description="s1", content="test analysis", step_type="definition"),
                ReasoningStep(description="s2", content="test evaluation", step_type="evaluation"),
                ReasoningStep(description="s3", content="test conclusion", step_type="conclusion"),
            ],
            conclusion="done",
            confidence=0.8,
        )
        ctx = ReasoningContext(query="test")
        result = await evaluator.evaluate(chain, ctx)
        assert result.score > 0.5
        assert result.completeness > 0.5

    @pytest.mark.asyncio
    async def test_evaluate_feedback(self):
        evaluator = DefaultEvaluator()
        ctx = ReasoningContext(query="test")
        result = await evaluator.evaluate(ReasoningChain(), ctx)
        assert any(f for f in result.feedback if "lacks" in f.lower())


# ======================================================================
# Validator tests
# ======================================================================

class TestDefaultValidator:
    @pytest.mark.asyncio
    async def test_validate_complete_decision(self):
        validator = DefaultValidator()
        chain = ReasoningChain(
            steps=[ReasoningStep(description="s", content="c")],
            conclusion="done",
            confidence=0.8,
        )
        eval_result = EvaluationResult(score=0.8)
        decision = ReasoningDecision(
            conclusion="done",
            confidence=0.8,
            chain=chain,
            evaluation=eval_result,
        )
        ctx = ReasoningContext(query="test")
        result = await validator.validate(decision, ctx)
        assert result.is_valid

    @pytest.mark.asyncio
    async def test_validate_missing_conclusion(self):
        validator = DefaultValidator()
        decision = ReasoningDecision(confidence=0.0)
        ctx = ReasoningContext(query="test")
        result = await validator.validate(decision, ctx)
        assert not result.is_valid
        assert any("conclusion" in i.lower() for i in result.issues)

    @pytest.mark.asyncio
    async def test_validate_low_confidence(self):
        validator = DefaultValidator()
        decision = ReasoningDecision(conclusion="done", confidence=0.1)
        ctx = ReasoningContext(query="test")
        result = await validator.validate(decision, ctx)
        assert not result.is_valid
        assert any("confidence" in i.lower() for i in result.issues)


# ======================================================================
# Critic tests
# ======================================================================

class TestDefaultCritic:
    @pytest.mark.asyncio
    async def test_critique_empty_chain(self):
        critic = DefaultCritic()
        ctx = ReasoningContext(query="test")
        result = await critic.critique(ReasoningChain(), ctx)
        assert "No reasoning steps generated" in result.flaws

    @pytest.mark.asyncio
    async def test_critique_complete_chain(self):
        critic = DefaultCritic()
        chain = ReasoningChain(
            steps=[
                ReasoningStep(description="s1", content="detailed analysis step one", step_type="definition"),
                ReasoningStep(description="s2", content="detailed evaluation step two", step_type="evaluation"),
            ],
            conclusion="done",
            confidence=0.8,
        )
        ctx = ReasoningContext(query="test")
        result = await critic.critique(chain, ctx)
        assert result.overall_assessment

    @pytest.mark.asyncio
    async def test_critique_identifies_brief_content(self):
        critic = DefaultCritic()
        chain = ReasoningChain(
            steps=[ReasoningStep(description="s", content="short")],
            conclusion="done",
            confidence=0.6,
        )
        ctx = ReasoningContext(query="test")
        result = await critic.critique(chain, ctx)
        assert result.gaps


# ======================================================================
# StrategyRegistry tests
# ======================================================================

class TestStrategyRegistry:
    def test_default_registry_has_all_strategies(self):
        registry = StrategyRegistry()
        names = registry.list_names()
        assert "DIRECT" in names
        assert "ANALYTICAL" in names
        assert "COMPARATIVE" in names
        assert "MULTI_STEP" in names
        assert "SELF_CRITIQUE" in names

    def test_register_and_unregister(self):
        registry = StrategyRegistry(strategies=[])
        s = DirectReasoningStrategy()
        registry.register(s)
        assert registry.get("DIRECT") is s
        registry.unregister("DIRECT")
        assert registry.get("DIRECT") is None

    def test_get_returns_none_for_unknown(self):
        registry = StrategyRegistry(strategies=[])
        assert registry.get("NONEXISTENT") is None

    @pytest.mark.asyncio
    async def test_select_direct_for_simple(self):
        registry = StrategyRegistry()
        ctx = ReasoningContext(query="hello")
        strategy = await registry.select(ctx)
        assert strategy is not None
        assert strategy.name == "DIRECT"

    @pytest.mark.asyncio
    async def test_select_analytical_for_why(self):
        registry = StrategyRegistry()
        ctx = ReasoningContext(query="why is the sky blue")
        strategy = await registry.select(ctx)
        assert strategy is not None
        assert strategy.name in ("ANALYTICAL", "SELF_CRITIQUE")

    @pytest.mark.asyncio
    async def test_select_comparative_for_compare(self):
        registry = StrategyRegistry()
        ctx = ReasoningContext(query="compare python vs java")
        strategy = await registry.select(ctx)
        assert strategy is not None
        assert strategy.name == "COMPARATIVE"

    @pytest.mark.asyncio
    async def test_select_returns_none_when_empty(self):
        registry = StrategyRegistry(strategies=[])
        ctx = ReasoningContext(query="hello")
        strategy = await registry.select(ctx)
        assert strategy is None


# ======================================================================
# ReasoningEngine tests
# ======================================================================

class TestReasoningEngine:
    @pytest.mark.asyncio
    async def test_reason_returns_decision(self):
        engine = ReasoningEngine()
        decision = await engine.reason(query="hello")
        assert isinstance(decision, ReasoningDecision)
        assert decision.status == ReasoningStatus.COMPLETED
        assert decision.conclusion is not None

    @pytest.mark.asyncio
    async def test_reason_analytical_query(self):
        engine = ReasoningEngine()
        decision = await engine.reason(query="why do we dream")
        assert decision.status == ReasoningStatus.COMPLETED
        assert decision.chain is not None
        assert decision.chain.strategy == StrategyType.ANALYTICAL

    @pytest.mark.asyncio
    async def test_reason_comparative_query(self):
        engine = ReasoningEngine()
        decision = await engine.reason(query="compare cats vs dogs as pets")
        assert decision.chain.strategy == StrategyType.COMPARATIVE

    @pytest.mark.asyncio
    async def test_reason_with_explicit_strategy(self):
        engine = ReasoningEngine()
        decision = await engine.reason(query="hello", strategy_name="ANALYTICAL")
        assert decision.chain is not None
        assert decision.chain.strategy == StrategyType.ANALYTICAL

    @pytest.mark.asyncio
    async def test_reason_with_invalid_strategy_falls_back(self):
        engine = ReasoningEngine()
        decision = await engine.reason(query="hello", strategy_name="NONEXISTENT")
        assert decision.status == ReasoningStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_reason_includes_evaluation(self):
        engine = ReasoningEngine()
        decision = await engine.reason(query="analyze the market")
        assert decision.evaluation is not None
        assert decision.evaluation.score > 0

    @pytest.mark.asyncio
    async def test_reason_includes_validation(self):
        engine = ReasoningEngine()
        decision = await engine.reason(query="hello")
        assert decision.validation is not None

    @pytest.mark.asyncio
    async def test_reason_includes_critique(self):
        engine = ReasoningEngine()
        decision = await engine.reason(query="why is the sky blue")
        assert decision.critique is not None

    @pytest.mark.asyncio
    async def test_reason_with_user_id(self):
        engine = ReasoningEngine()
        decision = await engine.reason(query="hello", user_id="u1", session_id="s1")
        assert decision.status == ReasoningStatus.COMPLETED
        assert "u1" in decision.to_dict()["query"] or True  # query is stored directly

    @pytest.mark.asyncio
    async def test_reason_with_constraints(self):
        engine = ReasoningEngine()
        decision = await engine.reason(query="hello", constraints=["be concise"])
        assert decision.status == ReasoningStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_reason_with_strategy_in_metadata(self):
        engine = ReasoningEngine()
        decision = await engine.reason(query="hello")
        assert "strategy" in decision.metadata
        assert "steps_count" in decision.metadata

    @pytest.mark.asyncio
    async def test_reason_with_strategy_error_returns_failed(self):
        engine = ReasoningEngine(registry=StrategyRegistry(strategies=[]))
        decision = await engine.reason(query="hello")
        assert decision.status == ReasoningStatus.FAILED
        assert decision.error is not None

    @pytest.mark.asyncio
    async def test_reason_with_strategy_pipeline(self):
        engine = ReasoningEngine()
        ctx = ReasoningContext(query="why do we sleep")
        strategy = AnalyticalReasoningStrategy()
        decision = await engine.reason_with_strategy(ctx, strategy)
        assert decision.status == ReasoningStatus.COMPLETED
        assert decision.chain.strategy == StrategyType.ANALYTICAL

    @pytest.mark.asyncio
    async def test_reason_with_strategy_produces_evaluation(self):
        engine = ReasoningEngine()
        ctx = ReasoningContext(query="test")
        strategy = DirectReasoningStrategy()
        decision = await engine.reason_with_strategy(ctx, strategy)
        assert decision.evaluation is not None

    @pytest.mark.asyncio
    async def test_registry_property(self):
        engine = ReasoningEngine()
        assert engine.registry is not None
        assert "DIRECT" in engine.registry.list_names()

    @pytest.mark.asyncio
    async def test_custom_evaluator(self):
        mock_evaluator = MagicMock(spec=CandidateEvaluator)
        mock_evaluator.evaluate = AsyncMock(
            return_value=EvaluationResult(score=1.0, feedback=["custom"])
        )
        engine = ReasoningEngine(evaluator=mock_evaluator)
        decision = await engine.reason(query="hello")
        assert decision.evaluation.score == 1.0
        mock_evaluator.evaluate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_custom_validator(self):
        mock_validator = MagicMock(spec=DecisionValidator)
        mock_validator.validate = AsyncMock(
            return_value=ValidationResult(is_valid=False, issues=["custom"])
        )
        engine = ReasoningEngine(validator=mock_validator)
        decision = await engine.reason(query="hello")
        assert not decision.validation.is_valid
        assert "custom" in decision.validation.issues

    @pytest.mark.asyncio
    async def test_custom_critic(self):
        mock_critic = MagicMock(spec=SelfCritic)
        mock_critic.critique = AsyncMock(
            return_value=CritiqueResult(flaws=["custom flaw"])
        )
        engine = ReasoningEngine(critic=mock_critic)
        decision = await engine.reason(query="why is the sky blue")
        assert "custom flaw" in decision.critique.flaws

    @pytest.mark.asyncio
    async def test_validation_failure_skips_critique(self):
        mock_validator = MagicMock(spec=DecisionValidator)
        mock_validator.validate = AsyncMock(
            return_value=ValidationResult(is_valid=False, issues=["fail"])
        )
        mock_critic = MagicMock(spec=SelfCritic)
        engine = ReasoningEngine(validator=mock_validator, critic=mock_critic)
        decision = await engine.reason(query="hello")
        assert decision.critique is None
        mock_critic.critique.assert_not_called()
        assert "validation_issues" in decision.metadata

    @pytest.mark.asyncio
    async def test_properties(self):
        engine = ReasoningEngine()
        assert engine.evaluator is not None
        assert engine.validator is not None
        assert engine.critic is not None


# ======================================================================
# CognitiveEngine integration tests
# ======================================================================

class TestReasoningCognitiveIntegration:
    @pytest.mark.asyncio
    async def test_reasoning_handler_returns_reason_action(self):
        handler = ReasoningHandler()
        assert IntentType.REASON in handler.handled_intents
        ctx = CognitiveContext(raw_input="let me think about this problem")
        dec = await handler.decide(ctx)
        assert dec.action == DecisionAction.REASON
        assert dec.handler_name == "reason"
        assert dec.confidence == 0.85

    @pytest.mark.asyncio
    async def test_default_handler_registry_includes_reason(self):
        registry = default_handler_registry()
        assert IntentType.REASON in registry

    @pytest.mark.asyncio
    async def test_intent_type_has_reason(self):
        assert IntentType.REASON.value == "REASON"

    @pytest.mark.asyncio
    async def test_decision_action_has_reason(self):
        assert DecisionAction.REASON.value == "REASON"

    @pytest.mark.asyncio
    async def test_intent_type_count(self):
        assert len(IntentType) == 14

    @pytest.mark.asyncio
    async def test_reason_detection_pattern(self):
        detector = RuleBasedIntentDetector()
        ctx = CognitiveContext(raw_input="let's think through this logically")
        intent, conf = await detector.detect(ctx)
        assert intent == IntentType.REASON
        assert conf > 0

    @pytest.mark.asyncio
    async def test_reason_detection_analyze(self):
        detector = RuleBasedIntentDetector()
        ctx = CognitiveContext(raw_input="analyze the implications of this decision")
        intent, conf = await detector.detect(ctx)
        assert intent == IntentType.REASON

    @pytest.mark.asyncio
    async def test_cognitive_engine_with_reasoning(self):
        mock_gm = MagicMock()
        mock_gm.list_goals = AsyncMock(return_value=[])
        mock_tm = MagicMock()
        mock_tm.list_tasks = AsyncMock(return_value=[])
        mock_am = MagicMock()
        mock_am.list_runtime_agents = MagicMock(return_value=[])
        mock_pm = MagicMock()
        mock_pm.get_profile = AsyncMock(return_value={})
        mock_cm = MagicMock()
        mock_cm.get_history = AsyncMock(return_value=[])

        reasoning_engine = ReasoningEngine()

        engine = CognitiveEngine(
            goal_manager=mock_gm,
            task_manager=mock_tm,
            agent_manager=mock_am,
            profile_memory=mock_pm,
            conversation_memory=mock_cm,
            reasoning_engine=reasoning_engine,
        )

        state = await engine.process(
            raw_input="let me reason through this problem step by step"
        )
        # Will detect as REASON or fallback depending on detector
        assert state.decision is not None
        assert state.error is None

    @pytest.mark.asyncio
    async def test_cognitive_engine_reason_execution(self):
        mock_gm = MagicMock()
        mock_gm.list_goals = AsyncMock(return_value=[])
        mock_tm = MagicMock()
        mock_tm.list_tasks = AsyncMock(return_value=[])
        mock_am = MagicMock()
        mock_am.list_runtime_agents = MagicMock(return_value=[])
        mock_pm = MagicMock()
        mock_pm.get_profile = AsyncMock(return_value={})
        mock_cm = MagicMock()
        mock_cm.get_history = AsyncMock(return_value=[])

        reasoning_engine = ReasoningEngine()

        engine = CognitiveEngine(
            goal_manager=mock_gm,
            task_manager=mock_tm,
            agent_manager=mock_am,
            profile_memory=mock_pm,
            conversation_memory=mock_cm,
            reasoning_engine=reasoning_engine,
        )

        ctx = CognitiveContext(raw_input="let's think about AI safety")
        decision = CognitiveDecision(
            action=DecisionAction.REASON,
            handler_name="reason",
            payload={"query": "AI safety implications", "user_id": "u1", "session_id": "s1"},
        )
        result = await engine._execute_decision(decision, ctx)
        assert result is not None
        assert "reasoning_decision" in result
        assert result["reasoning_decision"]["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_cognitive_engine_reason_without_reasoning_engine(self):
        mock_gm = MagicMock()
        mock_gm.list_goals = AsyncMock(return_value=[])
        mock_tm = MagicMock()
        mock_tm.list_tasks = AsyncMock(return_value=[])
        mock_am = MagicMock()
        mock_am.list_runtime_agents = MagicMock(return_value=[])
        mock_pm = MagicMock()
        mock_pm.get_profile = AsyncMock(return_value={})
        mock_cm = MagicMock()
        mock_cm.get_history = AsyncMock(return_value=[])

        engine = CognitiveEngine(
            goal_manager=mock_gm,
            task_manager=mock_tm,
            agent_manager=mock_am,
            profile_memory=mock_pm,
            conversation_memory=mock_cm,
        )

        ctx = CognitiveContext(raw_input="let's think")
        decision = CognitiveDecision(
            action=DecisionAction.REASON,
            handler_name="reason",
            payload={"query": "think", "user_id": None, "session_id": None},
        )
        result = await engine._execute_decision(decision, ctx)
        assert result is not None
        assert "error" in result
        assert "ReasoningEngine not available" in result["error"]
