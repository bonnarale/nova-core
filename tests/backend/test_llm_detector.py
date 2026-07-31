"""Unit tests for LLMIntentDetector."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.cognitive.context import CognitiveContext, IntentType
from app.cognitive.llm_detector import LLMIntentDetector
from app.cognitive.router import RuleBasedIntentDetector


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def mock_gateway():
    gw = MagicMock()
    gw.chat = AsyncMock()
    return gw


@pytest.fixture
def mock_fallback():
    fb = MagicMock(spec=RuleBasedIntentDetector)
    fb.detect = AsyncMock(return_value=(IntentType.CHAT, 0.6))
    return fb


@pytest.fixture
def detector(mock_gateway, mock_fallback):
    return LLMIntentDetector(gateway=mock_gateway, fallback=mock_fallback, model="test-model")


def _make_context(text: str) -> CognitiveContext:
    return CognitiveContext(raw_input=text)


# ======================================================================
# Happy Path
# ======================================================================

class TestLLMIntentDetectorHappyPath:
    @pytest.mark.asyncio
    async def test_confident_classification(self, detector, mock_gateway):
        mock_gateway.chat.return_value = {
            "message": {"content": json.dumps({"intent": "CODE", "confidence": 0.92})}
        }
        ctx = _make_context("write a Python function for sorting")
        intent, confidence = await detector.detect(ctx)

        assert intent == IntentType.CODE
        assert confidence >= 0.5
        mock_gateway.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_question_intent(self, detector, mock_gateway):
        mock_gateway.chat.return_value = {
            "message": {"content": json.dumps({"intent": "QUESTION", "confidence": 0.85})}
        }
        ctx = _make_context("what is a closure?")
        intent, confidence = await detector.detect(ctx)

        assert intent == IntentType.QUESTION
        assert confidence == 0.85

    @pytest.mark.asyncio
    async def test_goal_intent(self, detector, mock_gateway):
        mock_gateway.chat.return_value = {
            "message": {"content": json.dumps({"intent": "GOAL", "confidence": 0.78})}
        }
        ctx = _make_context("i want to build a web app")
        intent, confidence = await detector.detect(ctx)

        assert intent == IntentType.GOAL
        assert confidence == 0.78

    @pytest.mark.asyncio
    async def test_empty_input_returns_chat(self, detector):
        ctx = _make_context("")
        intent, confidence = await detector.detect(ctx)

        assert intent == IntentType.CHAT
        assert confidence == 0.5

    @pytest.mark.asyncio
    async def test_whitespace_only_returns_chat(self, detector):
        ctx = _make_context("   ")
        intent, confidence = await detector.detect(ctx)

        assert intent == IntentType.CHAT
        assert confidence == 0.5


# ======================================================================
# Low Confidence Fallback
# ======================================================================

class TestLLMIntentDetectorLowConfidence:
    @pytest.mark.asyncio
    async def test_low_confidence_falls_back(self, detector, mock_gateway, mock_fallback):
        mock_gateway.chat.return_value = {
            "message": {"content": json.dumps({"intent": "CHAT", "confidence": 0.3})}
        }
        ctx = _make_context("maybe do something?")
        intent, confidence = await detector.detect(ctx)

        assert intent == IntentType.CHAT
        assert confidence == 0.6  # from fallback mock
        mock_fallback.detect.assert_called_once_with(ctx)

    @pytest.mark.asyncio
    async def test_exact_threshold_0_5_uses_llm(self, detector, mock_gateway):
        mock_gateway.chat.return_value = {
            "message": {"content": json.dumps({"intent": "TASK", "confidence": 0.5})}
        }
        ctx = _make_context("create a task")
        intent, confidence = await detector.detect(ctx)

        assert intent == IntentType.TASK
        assert confidence == 0.5


# ======================================================================
# Gateway Failure Fallback
# ======================================================================

class TestLLMIntentDetectorGatewayFailure:
    @pytest.mark.asyncio
    async def test_gateway_exception_falls_back(self, detector, mock_gateway, mock_fallback):
        mock_gateway.chat.side_effect = RuntimeError("gateway down")
        ctx = _make_context("do something")
        intent, confidence = await detector.detect(ctx)

        assert intent == IntentType.CHAT
        assert confidence == 0.6  # from fallback mock
        mock_fallback.detect.assert_called_once_with(ctx)

    @pytest.mark.asyncio
    async def test_timeout_falls_back(self, detector, mock_gateway, mock_fallback):
        import asyncio
        mock_gateway.chat.side_effect = asyncio.TimeoutError("timeout")
        ctx = _make_context("slow request")
        intent, confidence = await detector.detect(ctx)

        assert intent == IntentType.CHAT
        assert confidence == 0.6

    @pytest.mark.asyncio
    async def test_malformed_json_falls_back(self, detector, mock_gateway, mock_fallback):
        mock_gateway.chat.return_value = {
            "message": {"content": "not valid json at all"}
        }
        ctx = _make_context("weird input")
        intent, confidence = await detector.detect(ctx)

        assert intent == IntentType.CHAT
        assert confidence == 0.6


# ======================================================================
# Caching
# ======================================================================

class TestLLMIntentDetectorCaching:
    @pytest.mark.asyncio
    async def test_cache_hit_on_repeated_input(self, detector, mock_gateway):
        mock_gateway.chat.return_value = {
            "message": {"content": json.dumps({"intent": "CODE", "confidence": 0.9})}
        }
        ctx1 = _make_context("write code")
        result1 = await detector.detect(ctx1)

        ctx2 = _make_context("write code")
        result2 = await detector.detect(ctx2)

        assert result1 == result2
        # Gateway should only be called once (second hit uses cache)
        assert mock_gateway.chat.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_does_not_cross_contaminate(self, detector, mock_gateway):
        mock_gateway.chat.return_value = {
            "message": {"content": json.dumps({"intent": "CODE", "confidence": 0.9})}
        }
        ctx1 = _make_context("write code")
        await detector.detect(ctx1)

        mock_gateway.chat.return_value = {
            "message": {"content": json.dumps({"intent": "QUESTION", "confidence": 0.8})}
        }
        ctx2 = _make_context("what is X?")
        result2 = await detector.detect(ctx2)

        assert result2 == (IntentType.QUESTION, 0.8)
        assert mock_gateway.chat.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_eviction(self, detector, mock_gateway):
        """Cache should not grow beyond 100 entries."""
        mock_gateway.chat.return_value = {
            "message": {"content": json.dumps({"intent": "CHAT", "confidence": 0.9})}
        }

        # Fill cache beyond max
        for i in range(105):
            ctx = _make_context(f"message {i}")
            await detector.detect(ctx)

        assert len(detector._cache) <= 100


# ======================================================================
# Response Parsing Edge Cases
# ======================================================================

class TestLLMIntentDetectorParsing:
    @pytest.mark.asyncio
    async def test_markdown_code_block_response(self, detector, mock_gateway):
        mock_gateway.chat.return_value = {
            "message": {"content": '```json\n{"intent": "CODE", "confidence": 0.88}\n```'}
        }
        ctx = _make_context("code something")
        intent, confidence = await detector.detect(ctx)

        assert intent == IntentType.CODE
        assert confidence == 0.88

    @pytest.mark.asyncio
    async def test_unknown_intent_defaults_to_chat(self, detector, mock_gateway):
        mock_gateway.chat.return_value = {
            "message": {"content": json.dumps({"intent": "UNKNOWN_INTENT", "confidence": 0.9})}
        }
        ctx = _make_context("something")
        intent, confidence = await detector.detect(ctx)

        assert intent == IntentType.CHAT
        assert confidence == 0.9

    @pytest.mark.asyncio
    async def test_confidence_clamped_to_range(self, detector, mock_gateway):
        mock_gateway.chat.return_value = {
            "message": {"content": json.dumps({"intent": "CODE", "confidence": 1.5})}
        }
        ctx = _make_context("code")
        intent, confidence = await detector.detect(ctx)

        assert confidence == 1.0  # clamped

    @pytest.mark.asyncio
    async def test_raw_text_response(self, detector, mock_gateway):
        """When response is plain text, parsing should fail and fall back."""
        mock_gateway.chat.return_value = {
            "message": {"content": "I think this is about coding but I'm not sure"}
        }
        ctx = _make_context("code")
        intent, confidence = await detector.detect(ctx)

        # Should fall back
        assert intent == IntentType.CHAT


# ======================================================================
# IntentType Values
# ======================================================================

class TestLLMIntentDetectorIntentTypes:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("intent_str", [t.value for t in IntentType])
    async def test_all_intent_types_parseable(self, detector, mock_gateway, intent_str):
        mock_gateway.chat.return_value = {
            "message": {"content": json.dumps({"intent": intent_str, "confidence": 0.8})}
        }
        ctx = _make_context(f"test {intent_str.lower()}")
        intent, _ = await detector.detect(ctx)

        assert intent == IntentType(intent_str)
