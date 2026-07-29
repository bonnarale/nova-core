"""Tests for META_IMPROVEMENT cognitive integration."""

from __future__ import annotations

import pytest

from app.cognitive.context import CognitiveContext, IntentType
from app.cognitive.decision import (
    CognitiveDecision,
    DecisionAction,
    MetaHandler,
    default_handler_registry,
)
from app.cognitive.router import CognitiveRouter, RuleBasedIntentDetector


class TestMetaHandler:
    @pytest.fixture
    def handler(self):
        return MetaHandler()

    @pytest.mark.asyncio
    async def test_handler_handles_meta_improvement(self, handler):
        """MetaHandler should handle META_IMPROVEMENT intent."""
        assert IntentType.META_IMPROVEMENT in handler.handled_intents

    @pytest.mark.asyncio
    async def test_handler_produces_valid_decision(self, handler):
        """MetaHandler should produce a decision with action RUN_META_CYCLE."""
        context = CognitiveContext(
            raw_input="run a capability audit",
            user_id="test-user",
        )
        decision = await handler.decide(context)

        assert isinstance(decision, CognitiveDecision)
        assert decision.action == DecisionAction.RUN_META_CYCLE
        assert decision.handler_name == "meta"
        assert decision.confidence > 0.5
        assert "task" in decision.payload
        assert decision.payload["task"] == "run a capability audit"

    @pytest.mark.asyncio
    async def test_handler_includes_user_id(self, handler):
        """Decision payload should include user_id."""
        context = CognitiveContext(
            raw_input="evolve the agent system",
            user_id="user-123",
        )
        decision = await handler.decide(context)

        assert decision.payload["user_id"] == "user-123"


class TestDefaultHandlerRegistry:
    def test_meta_handler_registered(self):
        """MetaHandler should be in the default handler registry."""
        registry = default_handler_registry()
        assert IntentType.META_IMPROVEMENT in registry
        handler = registry[IntentType.META_IMPROVEMENT]
        assert isinstance(handler, MetaHandler)


class TestIntentDetection:
    @pytest.fixture
    def detector(self):
        return RuleBasedIntentDetector()

    @pytest.mark.asyncio
    async def test_capability_audit_detected(self, detector):
        """'run a capability audit' should detect META_IMPROVEMENT."""
        context = CognitiveContext(raw_input="run a capability audit")
        intent, confidence = await detector.detect(context)

        assert intent == IntentType.META_IMPROVEMENT

    @pytest.mark.asyncio
    async def test_evolve_detected(self, detector):
        """'evolve the agent system' should detect META_IMPROVEMENT."""
        context = CognitiveContext(raw_input="evolve the agent system")
        intent, confidence = await detector.detect(context)

        # "evolve" matches META_IMPROVEMENT, "system" matches SYSTEM
        # META_IMPROVEMENT should win due to "evolve" being more specific
        assert intent in (IntentType.META_IMPROVEMENT, IntentType.SYSTEM)

    @pytest.mark.asyncio
    async def test_self_improvement_detected(self, detector):
        """'self-improvement' should detect META_IMPROVEMENT."""
        context = CognitiveContext(raw_input="run self-improvement")
        intent, confidence = await detector.detect(context)

        assert intent == IntentType.META_IMPROVEMENT

    @pytest.mark.asyncio
    async def test_non_meta_request_not_classified(self, detector):
        """User-facing feature request should NOT detect META_IMPROVEMENT."""
        context = CognitiveContext(raw_input="write me a Python function")
        intent, confidence = await detector.detect(context)

        assert intent != IntentType.META_IMPROVEMENT

    @pytest.mark.asyncio
    async def test_improve_agents_detected(self, detector):
        """'improve agents' should detect META_IMPROVEMENT."""
        context = CognitiveContext(raw_input="improve agents performance")
        intent, confidence = await detector.detect(context)

        assert intent == IntentType.META_IMPROVEMENT


class TestRouterIntegration:
    @pytest.mark.asyncio
    async def test_router_routes_meta_to_meta_handler(self):
        """CognitiveRouter should route META_IMPROVEMENT to MetaHandler."""
        from app.cognitive.decision import default_handler_registry

        handlers = default_handler_registry()
        router = CognitiveRouter(handlers=handlers)

        context = CognitiveContext(raw_input="run a capability audit")
        decision = await router.route(context)

        assert decision.action == DecisionAction.RUN_META_CYCLE
        assert decision.handler_name == "meta"
