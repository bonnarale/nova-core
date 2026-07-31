"""LLM-powered intent detector with rule-based fallback.

Implements the IntentDetector ABC using ModelGateway.chat() for
classification, with automatic fallback to RuleBasedIntentDetector
on low confidence or gateway failures.
"""

from __future__ import annotations

import json
import logging
from collections import OrderedDict
from typing import Any

from app.cognitive.context import CognitiveContext, IntentType
from app.cognitive.router import IntentDetector, RuleBasedIntentDetector

logger = logging.getLogger(__name__)

# All valid IntentType values for the classification prompt
_INTENT_TYPES = [t.value for t in IntentType]

_CLASSIFICATION_PROMPT = """You are an intent classifier. Given a user message, classify it into exactly one of the following intent types:

{intents}

Respond with ONLY a JSON object in this exact format:
{{"intent": "INTENT_NAME", "confidence": 0.0到1.0}}

Where:
- "intent" is one of the intent types listed above (exact uppercase match)
- "confidence" is a float between 0.0 and 1.0 indicating your certainty

User message: "{message}"

Response:"""

_CACHE_MAX_SIZE = 100


class LLMIntentDetector(IntentDetector):
    """Classifies user intent via LLM with rule-based fallback.

    Falls back to ``RuleBasedIntentDetector`` when:
    - LLM confidence < 0.5
    - ModelGateway raises an exception or times out
    - LLM response cannot be parsed

    Caches the first 100 unique inputs to avoid redundant LLM calls.
    """

    def __init__(
        self,
        gateway: Any,
        fallback: IntentDetector | None = None,
        model: str = "qwen2.5-coder:7b",
    ) -> None:
        self._gateway = gateway
        self._fallback = fallback or RuleBasedIntentDetector()
        self._model = model
        self._cache: OrderedDict[str, tuple[IntentType, float]] = OrderedDict()
        self._cache_max = _CACHE_MAX_SIZE

    async def detect(self, context: CognitiveContext) -> tuple[IntentType, float]:
        """Classify intent via LLM, falling back to rule-based on failure."""
        raw = context.raw_input.strip()
        if not raw:
            return IntentType.CHAT, 0.5

        # Check cache
        if raw in self._cache:
            self._cache.move_to_end(raw)
            return self._cache[raw]

        try:
            result = await self._classify(raw)
            intent, confidence = result

            if confidence < 0.5:
                logger.debug(
                    "LLM confidence %.2f < 0.5, falling back to rule-based", confidence
                )
                return await self._fallback.detect(context)

            # Cache the result
            self._cache[raw] = (intent, confidence)
            if len(self._cache) > self._cache_max:
                self._cache.popitem(last=False)

            return intent, confidence

        except Exception as exc:
            logger.debug("LLM intent detection failed: %s — falling back", exc)
            return await self._fallback.detect(context)

    async def _classify(self, message: str) -> tuple[IntentType, float]:
        """Send classification prompt to gateway and parse response."""
        prompt = _CLASSIFICATION_PROMPT.format(
            intents="\n".join(f"- {t}" for t in _INTENT_TYPES),
            message=message,
        )

        response = await self._gateway.chat(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            use_cache=True,
        )

        # Extract content from response
        content = self._extract_response_content(response)
        return self._parse_classification(content)

    @staticmethod
    def _extract_response_content(response: dict[str, Any]) -> str:
        """Extract text content from gateway response."""
        # Handle different response formats
        if "message" in response:
            msg = response["message"]
            if isinstance(msg, dict):
                return msg.get("content", "")
            return str(msg)
        if "content" in response:
            return str(response["content"])
        if "choices" in response:
            choices = response["choices"]
            if choices and isinstance(choices[0], dict):
                return choices[0].get("message", {}).get("content", "")
        # Fallback: treat entire response as text content
        return str(response)

    @staticmethod
    def _parse_classification(content: str) -> tuple[IntentType, float]:
        """Parse JSON classification from LLM response."""
        # Try to find JSON in the response
        text = content.strip()

        # Handle markdown code blocks
        if text.startswith("```"):
            lines = text.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```") and not in_block:
                    in_block = True
                    continue
                elif line.startswith("```") and in_block:
                    break
                elif in_block:
                    json_lines.append(line)
            text = "\n".join(json_lines).strip()

        # Try to find a JSON object in the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]

        parsed = json.loads(text)
        intent_str = parsed.get("intent", "CHAT").upper()
        confidence = float(parsed.get("confidence", 0.5))

        # Validate intent
        try:
            intent = IntentType(intent_str)
        except ValueError:
            logger.warning("Unknown intent type from LLM: %s, defaulting to CHAT", intent_str)
            intent = IntentType.CHAT

        confidence = max(0.0, min(1.0, confidence))
        return intent, confidence
