"""Default event handlers for all NOVA CORE subsystem events."""

from __future__ import annotations

import logging
from typing import Any

from app.events.base import EventHandler
from app.events.schemas import Event, EventType

logger = logging.getLogger(__name__)


class ConversationCreatedHandler(EventHandler):
    @property
    def event_type(self) -> str:
        return EventType.CONVERSATION_CREATED.value

    async def handle(self, event: Event) -> Event | None:
        logger.info("Conversation created: %s", event.aggregate_id)
        return None

    async def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


class MessageStoredHandler(EventHandler):
    @property
    def event_type(self) -> str:
        return EventType.MESSAGE_STORED.value

    async def handle(self, event: Event) -> Event | None:
        logger.info("Message stored: %s", event.aggregate_id)
        return None

    async def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


class MemoryUpdatedHandler(EventHandler):
    @property
    def event_type(self) -> str:
        return EventType.MEMORY_UPDATED.value

    async def handle(self, event: Event) -> Event | None:
        logger.info("Memory updated: %s", event.aggregate_id)
        return None

    async def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


class ProfileUpdatedHandler(EventHandler):
    @property
    def event_type(self) -> str:
        return EventType.PROFILE_UPDATED.value

    async def handle(self, event: Event) -> Event | None:
        logger.info("Profile updated: %s", event.aggregate_id)
        return None

    async def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


class KnowledgeLearnedHandler(EventHandler):
    @property
    def event_type(self) -> str:
        return EventType.KNOWLEDGE_LEARNED.value

    async def handle(self, event: Event) -> Event | None:
        logger.info("Knowledge learned: %s", event.aggregate_id)
        return None

    async def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


class GoalCreatedHandler(EventHandler):
    @property
    def event_type(self) -> str:
        return EventType.GOAL_CREATED.value

    async def handle(self, event: Event) -> Event | None:
        logger.info("Goal created: %s", event.aggregate_id)
        return None

    async def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


class GoalCompletedHandler(EventHandler):
    @property
    def event_type(self) -> str:
        return EventType.GOAL_COMPLETED.value

    async def handle(self, event: Event) -> Event | None:
        logger.info("Goal completed: %s", event.aggregate_id)
        return None

    async def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


class TaskCreatedHandler(EventHandler):
    @property
    def event_type(self) -> str:
        return EventType.TASK_CREATED.value

    async def handle(self, event: Event) -> Event | None:
        logger.info("Task created: %s", event.aggregate_id)
        return None

    async def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


class TaskStartedHandler(EventHandler):
    @property
    def event_type(self) -> str:
        return EventType.TASK_STARTED.value

    async def handle(self, event: Event) -> Event | None:
        logger.info("Task started: %s", event.aggregate_id)
        return None

    async def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


class TaskCompletedHandler(EventHandler):
    @property
    def event_type(self) -> str:
        return EventType.TASK_COMPLETED.value

    async def handle(self, event: Event) -> Event | None:
        logger.info("Task completed: %s", event.aggregate_id)
        return None

    async def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


class PlanCreatedHandler(EventHandler):
    @property
    def event_type(self) -> str:
        return EventType.PLAN_CREATED.value

    async def handle(self, event: Event) -> Event | None:
        logger.info("Plan created: %s", event.aggregate_id)
        return None

    async def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


class ExecutionStartedHandler(EventHandler):
    @property
    def event_type(self) -> str:
        return EventType.EXECUTION_STARTED.value

    async def handle(self, event: Event) -> Event | None:
        logger.info("Execution started: %s", event.aggregate_id)
        return None

    async def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


class ExecutionCompletedHandler(EventHandler):
    @property
    def event_type(self) -> str:
        return EventType.EXECUTION_COMPLETED.value

    async def handle(self, event: Event) -> Event | None:
        logger.info("Execution completed: %s", event.aggregate_id)
        return None

    async def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


class ToolExecutedHandler(EventHandler):
    @property
    def event_type(self) -> str:
        return EventType.TOOL_EXECUTED.value

    async def handle(self, event: Event) -> Event | None:
        logger.info("Tool executed: %s", event.aggregate_id)
        return None

    async def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


class AgentRegisteredHandler(EventHandler):
    @property
    def event_type(self) -> str:
        return EventType.AGENT_REGISTERED.value

    async def handle(self, event: Event) -> Event | None:
        logger.info("Agent registered: %s", event.aggregate_id)
        return None

    async def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


class AgentStartedHandler(EventHandler):
    @property
    def event_type(self) -> str:
        return EventType.AGENT_STARTED.value

    async def handle(self, event: Event) -> Event | None:
        logger.info("Agent started: %s", event.aggregate_id)
        return None

    async def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


class AgentFinishedHandler(EventHandler):
    @property
    def event_type(self) -> str:
        return EventType.AGENT_FINISHED.value

    async def handle(self, event: Event) -> Event | None:
        logger.info("Agent finished: %s", event.aggregate_id)
        return None

    async def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


class ModelInvokedHandler(EventHandler):
    @property
    def event_type(self) -> str:
        return EventType.MODEL_INVOKED.value

    async def handle(self, event: Event) -> Event | None:
        logger.info("Model invoked: %s", event.aggregate_id)
        return None

    async def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


class RetrievalCompletedHandler(EventHandler):
    @property
    def event_type(self) -> str:
        return EventType.RETRIEVAL_COMPLETED.value

    async def handle(self, event: Event) -> Event | None:
        logger.info("Retrieval completed: %s", event.aggregate_id)
        return None

    async def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


class VectorStoredHandler(EventHandler):
    @property
    def event_type(self) -> str:
        return EventType.VECTOR_STORED.value

    async def handle(self, event: Event) -> Event | None:
        logger.info("Vector stored: %s", event.aggregate_id)
        return None

    async def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


class SystemEventHandler(EventHandler):
    @property
    def event_type(self) -> str:
        return EventType.SYSTEM_EVENT.value

    async def handle(self, event: Event) -> Event | None:
        logger.info("System event: %s", event.event_id)
        return None

    async def can_handle(self, event: Event) -> bool:
        return event.event_type == self.event_type


DEFAULT_HANDLERS: list[type[EventHandler]] = [
    ConversationCreatedHandler,
    MessageStoredHandler,
    MemoryUpdatedHandler,
    ProfileUpdatedHandler,
    KnowledgeLearnedHandler,
    GoalCreatedHandler,
    GoalCompletedHandler,
    TaskCreatedHandler,
    TaskStartedHandler,
    TaskCompletedHandler,
    PlanCreatedHandler,
    ExecutionStartedHandler,
    ExecutionCompletedHandler,
    ToolExecutedHandler,
    AgentRegisteredHandler,
    AgentStartedHandler,
    AgentFinishedHandler,
    ModelInvokedHandler,
    RetrievalCompletedHandler,
    VectorStoredHandler,
    SystemEventHandler,
]
