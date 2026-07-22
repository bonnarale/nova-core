"""CognitiveDecision and DecisionHandler strategy pattern."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.cognitive.context import CognitiveContext, IntentType


class DecisionAction(str, Enum):
    """All possible actions the Cognitive Engine can decide."""

    ANSWER_DIRECTLY = "ANSWER_DIRECTLY"
    UPDATE_PROFILE = "UPDATE_PROFILE"
    CREATE_GOAL = "CREATE_GOAL"
    CREATE_TASK = "CREATE_TASK"
    CREATE_PLAN = "CREATE_PLAN"
    EXECUTE_EXISTING_TASK = "EXECUTE_EXISTING_TASK"
    DELEGATE_TO_PLANNER = "DELEGATE_TO_PLANNER"
    DELEGATE_TO_RESEARCHER = "DELEGATE_TO_RESEARCHER"
    DELEGATE_TO_CODER = "DELEGATE_TO_CODER"
    DELEGATE_TO_MEMORY = "DELEGATE_TO_MEMORY"
    DELEGATE_TO_EXECUTOR = "DELEGATE_TO_EXECUTOR"
    DELEGATE_TO_REVIEWER = "DELEGATE_TO_REVIEWER"
    ROUTE_TO_KERNEL = "ROUTE_TO_KERNEL"
    REASON = "REASON"
    EXECUTE_WORKFLOW = "EXECUTE_WORKFLOW"
    QUERY_KNOWLEDGE_GRAPH = "QUERY_KNOWLEDGE_GRAPH"
    FALLBACK = "FALLBACK"


@dataclass
class CognitiveDecision:
    """The output of a cognitive cycle — what to do next."""

    action: DecisionAction = DecisionAction.FALLBACK
    handler_name: str = "fallback"
    payload: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    reasoning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "handler": self.handler_name,
            "payload": self.payload,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }


# ---------------------------------------------------------------------------
# Handler registry — maps intent -> handler
# ---------------------------------------------------------------------------

class DecisionHandler(ABC):
    """Abstract handler that produces a CognitiveDecision from context."""

    @property
    @abstractmethod
    def handled_intents(self) -> set[IntentType]:
        """Return the intents this handler can process."""
        ...

    @abstractmethod
    async def decide(self, context: CognitiveContext) -> CognitiveDecision:
        """Examine context and return a decision."""
        ...


class ChatHandler(DecisionHandler):
    """Handler for casual chat — route directly to the kernel LLM."""

    @property
    def handled_intents(self) -> set[IntentType]:
        return {IntentType.CHAT}

    async def decide(self, context: CognitiveContext) -> CognitiveDecision:
        return CognitiveDecision(
            action=DecisionAction.ROUTE_TO_KERNEL,
            handler_name="chat",
            payload={"task": context.raw_input, "agent_id": "assistant"},
            confidence=0.9,
            reasoning="Casual chat detected — routing to assistant agent.",
        )


class QuestionHandler(DecisionHandler):
    """Handler for factual questions — route to the kernel LLM."""

    @property
    def handled_intents(self) -> set[IntentType]:
        return {IntentType.QUESTION}

    async def decide(self, context: CognitiveContext) -> CognitiveDecision:
        return CognitiveDecision(
            action=DecisionAction.ROUTE_TO_KERNEL,
            handler_name="question",
            payload={"task": context.raw_input, "agent_id": "assistant"},
            confidence=0.85,
            reasoning="Factual question — routing to assistant agent.",
        )


class GoalHandler(DecisionHandler):
    """Handler for goal-related intents — create a goal, then delegate to planner."""

    @property
    def handled_intents(self) -> set[IntentType]:
        return {IntentType.GOAL}

    async def decide(self, context: CognitiveContext) -> CognitiveDecision:
        return CognitiveDecision(
            action=DecisionAction.CREATE_GOAL,
            handler_name="goal",
            payload={
                "title": context.raw_input,
                "user_id": context.user_id,
                "description": context.raw_input,
                "delegate_to": "planner",
            },
            confidence=0.8,
            reasoning="User expressed a new goal — creating and delegating to planner.",
        )


class TaskHandler(DecisionHandler):
    """Handler for task-related intents — create a task with assigned agent."""

    @property
    def handled_intents(self) -> set[IntentType]:
        return {IntentType.TASK}

    async def decide(self, context: CognitiveContext) -> CognitiveDecision:
        agent = self._suggest_agent(context)
        return CognitiveDecision(
            action=DecisionAction.CREATE_TASK,
            handler_name="task",
            payload={
                "goal": context.raw_input,
                "user_id": context.user_id,
                "assigned_agent": agent,
            },
            confidence=0.75,
            reasoning=f"User requested a task — creating with suggested agent '{agent}'.",
        )

    @staticmethod
    def _suggest_agent(context: CognitiveContext) -> str:
        text = context.raw_input.lower()
        if any(w in text for w in ("search", "research", "find", "investigate")):
            return "researcher"
        if any(w in text for w in ("code", "write", "implement", "build", "develop")):
            return "coder"
        if any(w in text for w in ("plan", "organize", "strategy")):
            return "planner"
        if any(w in text for w in ("review", "check", "validate")):
            return "reviewer"
        return "executor"


class SearchHandler(DecisionHandler):
    """Handler for search intents — delegate to researcher."""

    @property
    def handled_intents(self) -> set[IntentType]:
        return {IntentType.SEARCH}

    async def decide(self, context: CognitiveContext) -> CognitiveDecision:
        return CognitiveDecision(
            action=DecisionAction.DELEGATE_TO_RESEARCHER,
            handler_name="search",
            payload={"task": context.raw_input, "user_id": context.user_id},
            confidence=0.85,
            reasoning="Search intent — delegating to researcher agent.",
        )


class ResearchHandler(DecisionHandler):
    """Handler for research intents — delegate to researcher."""

    @property
    def handled_intents(self) -> set[IntentType]:
        return {IntentType.RESEARCH}

    async def decide(self, context: CognitiveContext) -> CognitiveDecision:
        return CognitiveDecision(
            action=DecisionAction.DELEGATE_TO_RESEARCHER,
            handler_name="research",
            payload={"task": context.raw_input, "user_id": context.user_id},
            confidence=0.85,
            reasoning="Research request — delegating to researcher agent.",
        )


class CodeHandler(DecisionHandler):
    """Handler for code intents — delegate to coder."""

    @property
    def handled_intents(self) -> set[IntentType]:
        return {IntentType.CODE}

    async def decide(self, context: CognitiveContext) -> CognitiveDecision:
        return CognitiveDecision(
            action=DecisionAction.DELEGATE_TO_CODER,
            handler_name="code",
            payload={"task": context.raw_input, "user_id": context.user_id},
            confidence=0.85,
            reasoning="Code request — delegating to coder agent.",
        )


class MemoryHandler(DecisionHandler):
    """Handler for memory intents — delegate to memory agent."""

    @property
    def handled_intents(self) -> set[IntentType]:
        return {IntentType.MEMORY}

    async def decide(self, context: CognitiveContext) -> CognitiveDecision:
        action = DecisionAction.DELEGATE_TO_MEMORY
        return CognitiveDecision(
            action=action,
            handler_name="memory",
            payload={"task": context.raw_input, "user_id": context.user_id},
            confidence=0.8,
            reasoning="Memory-related request — delegating to memory agent.",
        )


class ProfileUpdateHandler(DecisionHandler):
    """Handler for profile update intents."""

    @property
    def handled_intents(self) -> set[IntentType]:
        return {IntentType.PROFILE_UPDATE}

    async def decide(self, context: CognitiveContext) -> CognitiveDecision:
        return CognitiveDecision(
            action=DecisionAction.UPDATE_PROFILE,
            handler_name="profile_update",
            payload={"user_id": context.user_id, "input": context.raw_input},
            confidence=0.8,
            reasoning="User wants to update profile information.",
        )


class SystemHandler(DecisionHandler):
    """Handler for system intents — route to kernel."""

    @property
    def handled_intents(self) -> set[IntentType]:
        return {IntentType.SYSTEM}

    async def decide(self, context: CognitiveContext) -> CognitiveDecision:
        return CognitiveDecision(
            action=DecisionAction.ROUTE_TO_KERNEL,
            handler_name="system",
            payload={"task": context.raw_input, "agent_id": "assistant"},
            confidence=0.95,
            reasoning="System command — routing to kernel.",
        )


class PlannerHandler(DecisionHandler):
    """Handler for planning intents — create an executable plan."""

    @property
    def handled_intents(self) -> set[IntentType]:
        return {IntentType.PLAN}

    async def decide(self, context: CognitiveContext) -> CognitiveDecision:
        return CognitiveDecision(
            action=DecisionAction.CREATE_PLAN,
            handler_name="planner",
            payload={
                "objective": context.raw_input,
                "user_id": context.user_id,
                "session_id": context.session_id,
            },
            confidence=0.8,
            reasoning="User expressed an objective that requires planning — creating executable plan.",
        )


class ReasoningHandler(DecisionHandler):
    """Handler for reasoning intents — structured reasoning pipeline."""

    @property
    def handled_intents(self) -> set[IntentType]:
        return {IntentType.REASON}

    async def decide(self, context: CognitiveContext) -> CognitiveDecision:
        return CognitiveDecision(
            action=DecisionAction.REASON,
            handler_name="reason",
            payload={
                "query": context.raw_input,
                "user_id": context.user_id,
                "session_id": context.session_id,
            },
            confidence=0.85,
            reasoning="User query requires structured reasoning — running reasoning pipeline.",
        )


class WorkflowHandler(DecisionHandler):
    """Handler for workflow intents — execute a workflow."""

    @property
    def handled_intents(self) -> set[IntentType]:
        return {IntentType.WORKFLOW}

    async def decide(self, context: CognitiveContext) -> CognitiveDecision:
        return CognitiveDecision(
            action=DecisionAction.EXECUTE_WORKFLOW,
            handler_name="workflow",
            payload={
                "task": context.raw_input,
                "user_id": context.user_id,
                "session_id": context.session_id,
            },
            confidence=0.8,
            reasoning="User request matches a workflow — routing to workflow engine.",
            )


class KnowledgeGraphHandler(DecisionHandler):
    """Handler for knowledge graph queries."""

    @property
    def handled_intents(self) -> set[IntentType]:
        return {IntentType.KNOWLEDGE_GRAPH}

    async def decide(self, context: CognitiveContext) -> CognitiveDecision:
        return CognitiveDecision(
            action=DecisionAction.QUERY_KNOWLEDGE_GRAPH,
            handler_name="knowledge_graph",
            payload={
                "query": context.raw_input,
                "user_id": context.user_id,
                "session_id": context.session_id,
            },
            confidence=0.8,
            reasoning="User query involves knowledge graph — searching entities and relationships.",
        )


class FallbackHandler(DecisionHandler):
    """Fallback when no handler matches — route to kernel as chat."""

    @property
    def handled_intents(self) -> set[IntentType]:
        return set()

    async def decide(self, context: CognitiveContext) -> CognitiveDecision:
        return CognitiveDecision(
            action=DecisionAction.FALLBACK,
            handler_name="fallback",
            payload={"task": context.raw_input, "agent_id": "assistant"},
            confidence=0.3,
            reasoning="Intent not clearly detected — falling back to assistant agent.",
        )


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def default_handler_registry() -> dict[IntentType, DecisionHandler]:
    """Build the default handler mapping.

    Custom mappings can be built by calling this and then overriding entries.
    """
    handlers: list[DecisionHandler] = [
        ChatHandler(),
        QuestionHandler(),
        GoalHandler(),
        TaskHandler(),
        PlannerHandler(),
        ReasoningHandler(),
        WorkflowHandler(),
        KnowledgeGraphHandler(),
        SearchHandler(),
        ResearchHandler(),
        CodeHandler(),
        MemoryHandler(),
        ProfileUpdateHandler(),
        SystemHandler(),
    ]
    registry: dict[IntentType, DecisionHandler] = {}
    for h in handlers:
        for intent in h.handled_intents:
            registry[intent] = h
    return registry
