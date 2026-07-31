"""CognitiveRouter — intent detection and decision routing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.cognitive.context import CognitiveContext, IntentType
from app.cognitive.decision import CognitiveDecision, DecisionHandler, FallbackHandler


# ---------------------------------------------------------------------------
# Intent detectors (strategy pattern)
# ---------------------------------------------------------------------------

class IntentDetector(ABC):
    """Abstract intent detector."""

    @abstractmethod
    async def detect(self, context: CognitiveContext) -> tuple[IntentType, float]:
        """Return (intent, confidence)."""
        ...


class RuleBasedIntentDetector(IntentDetector):
    """Keyword-based intent detection with confidence scoring."""

    _PATTERNS: dict[IntentType, list[str]] = {
        IntentType.CHAT: [
            "hello", "hi ", "hey", "how are you", "good morning", "good evening",
            "what's up", "sup", "nice to meet", "greetings",
        ],
        IntentType.KNOWLEDGE_GRAPH: [
            "knowledge graph", "what do you know about", "find entity",
            "search graph", "graph query", "entity relationship",
            "related to", "shortest path", "neighborhood",
            "graph search", "knowledge base", "entity",
        ],
        IntentType.WORKFLOW: [
            "workflow", "run workflow", "start workflow", "execute workflow",
            "pipeline", "automation", "multi-step process",
        ],
        IntentType.REASON: [
            "reason", "think through", "logical", "deduce", "infer",
            "let me think", "let's think", "step by step",
            "what are the implications", "what if",
            "consider", "analyze the", "evaluate",
        ],
        IntentType.PLAN: [
            "build a", "create a", "develop a", "make a", "write a",
            "implement", "landing page", "landing", "construí",
            "creá un", "creá una", "investigá", "organizá",
            "construir", "crear", "desarrollar", "planificar",
            "backen", "frontend", "full stack", "fullstack",
        ],
        IntentType.QUESTION: [
            "what is", "what are", "how do", "how does", "why is", "why does",
            "when is", "where is", "who is", "can you explain", "tell me about",
            "define", "meaning of", "difference between", "?" "what's",
        ],
        IntentType.GOAL: [
            "i want to", "my goal is", "i aim to", "i plan to", "objective",
            "i would like to", "my objective", "aspire to", "strive to",
            "goal", "set a goal",
        ],
        IntentType.TASK: [
            "create a task", "add a task", "new task", "task for",
            "i need to", "create task", "assign task", "remind me to",
        ],
        IntentType.SEARCH: [
            "search for", "look up", "find information", "search the web",
            "google", "look for", "find me", "search about",
        ],
        IntentType.RESEARCH: [
            "research", "investigate", "deep dive", "study", "analyze",
            "gather information", "research about",
        ],
        IntentType.CODE: [
            "write code", "write a program", "implement", "code a",
            "develop a", "create a function", "write a function",
            "build an app", "program", "coding", "write a",
            "write an", "create a", "create an", "build a",
            "build an", "script", "function",
        ],
        IntentType.MEMORY: [
            "remember", "do you remember", "recall", "store this",
            "save this", "forget", "what do you know about me",
            "what did i say", "memory",
        ],
        IntentType.PROFILE_UPDATE: [
            "update my profile", "my name is", "i am ", "call me",
            "my email", "change my", "set my", "update my",
            "i like ", "i love ", "my favorite", "my preference",
        ],
        IntentType.SYSTEM: [
            "system", "shutdown", "restart", "status", "debug",
            "configuration", "settings", "admin",
        ],
        IntentType.SDD_TASK: [
            "sdd", "run sdd", "sdd explore", "sdd propose", "sdd spec",
            "sdd design", "sdd tasks", "sdd apply", "sdd verify", "sdd archive",
            "openspec", "proposal for change", "create proposal",
            "write spec", "design for change", "break into tasks",
            "run apply", "verify change", "archive change",
        ],
        IntentType.META_IMPROVEMENT: [
            "capability audit", "evolve", "self-improvement", "improve agents",
            "meta improvement", "run meta cycle", "agent evolution",
            "audit capabilities", "improve the system", "self-evolve",
            "evolution cycle", "improve agent system",
        ],
        IntentType.CONSULTING: [
            "proposal", "propuesta", "propuesta comercial",
            "report", "informe", "informe de consultoría",
            "contract", "contrato", "contrato de servicios",
            "invoice", "factura", "proforma",
            "market research", "investigación de mercado",
            "generate proposal", "generar propuesta",
            "generate report", "generar informe",
            "generate contract", "generar contrato",
            "generate invoice", "generar factura",
            "quote", "cotización", "presupuesto",
            "consulting", "consultoría", "consultor",
        ],
    }

    async def detect(self, context: CognitiveContext) -> tuple[IntentType, float]:
        text = context.raw_input.lower().strip()

        if not text:
            return IntentType.CHAT, 0.5

        best_intent = IntentType.CHAT
        best_score = 0.0

        for intent, patterns in self._PATTERNS.items():
            score = self._score_text(text, patterns)
            if score > best_score:
                best_score = score
                best_intent = intent

        confidence = min(best_score, 1.0)
        return best_intent, confidence

    @staticmethod
    def _score_text(text: str, patterns: list[str]) -> float:
        score = 0.0
        for pattern in patterns:
            if pattern in text:
                length_ratio = len(pattern) / max(len(text), 1)
                score += 0.15 + (length_ratio * 0.1)
        return score


# ---------------------------------------------------------------------------
# CognitiveRouter
# ---------------------------------------------------------------------------

class CognitiveRouter:
    """Routes a CognitiveContext to the appropriate DecisionHandler."""

    def __init__(
        self,
        detector: IntentDetector | None = None,
        handlers: dict[IntentType, DecisionHandler] | None = None,
        fallback: DecisionHandler | None = None,
    ) -> None:
        self._detector = detector or RuleBasedIntentDetector()
        self._handlers = handlers or {}
        self._fallback = fallback or FallbackHandler()

    @property
    def detector(self) -> IntentDetector:
        return self._detector

    @detector.setter
    def detector(self, d: IntentDetector) -> None:
        self._detector = d

    @property
    def handlers(self) -> dict[IntentType, DecisionHandler]:
        return self._handlers

    def register_handler(self, intent: IntentType, handler: DecisionHandler) -> None:
        self._handlers[intent] = handler

    def unregister_handler(self, intent: IntentType) -> None:
        self._handlers.pop(intent, None)

    async def route(self, context: CognitiveContext) -> CognitiveDecision:
        """Detect intent, find handler, return decision."""
        intent, confidence = await self._detector.detect(context)
        context.intent = intent
        context.confidence = confidence

        handler = self._handlers.get(intent, self._fallback)
        return await handler.decide(context)
