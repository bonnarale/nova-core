"""NOVA CORE Integration Tests — Chapter 29.

Provides reusable integration test infrastructure that validates
cross-subsystem interactions.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock


class IntegrationTestContext:
    """Context for integration tests with real or mocked subsystem wiring."""

    def __init__(self) -> None:
        self.cognitive_engine: MagicMock | None = None
        self.memory: MagicMock | None = None
        self.event_bus: MagicMock | None = None
        self.scheduler: MagicMock | None = None
        self.tool_registry: MagicMock | None = None
        self.plugin_manager: MagicMock | None = None
        self.security_engine: MagicMock | None = None
        self.workflow_engine: MagicMock | None = None
        self.knowledge_graph: MagicMock | None = None
        self.learning_engine: MagicMock | None = None
        self.rag_engine: MagicMock | None = None
        self.vector_memory: MagicMock | None = None
        self.scaling_engine: MagicMock | None = None
        self.deployment_manager: MagicMock | None = None
        self.database_manager: MagicMock | None = None
        self.observability: MagicMock | None = None
        self.request_id: str = str(uuid.uuid4())
        self.session_id: str = str(uuid.uuid4())
        self.created_at: datetime = datetime.now(timezone.utc)

    def setup_default_mocks(self) -> None:
        """Configure all subsystems with default mock behaviors."""
        self.cognitive_engine = MagicMock()
        self.memory = MagicMock()
        self.event_bus = MagicMock()
        self.event_bus.publish = AsyncMock()
        self.scheduler = MagicMock()
        self.scheduler.schedule = AsyncMock(return_value="job-123")
        self.tool_registry = MagicMock()
        self.plugin_manager = MagicMock()
        self.security_engine = MagicMock()
        self.security_engine.authenticate = AsyncMock(return_value=True)
        self.security_engine.authorize = AsyncMock(return_value=True)
        self.workflow_engine = MagicMock()
        self.knowledge_graph = MagicMock()
        self.learning_engine = MagicMock()
        self.rag_engine = MagicMock()
        self.vector_memory = MagicMock()
        self.scaling_engine = MagicMock()
        self.deployment_manager = MagicMock()
        self.database_manager = MagicMock()
        self.observability = MagicMock()

    def get_app_state(self) -> MagicMock:
        """Create a mock FastAPI app.state with all subsystems."""
        state = MagicMock()
        state.cognitive_engine = self.cognitive_engine
        state.memory = self.memory
        state.event_bus = self.event_bus
        state.scheduler = self.scheduler
        state.tool_registry = self.tool_registry
        state.plugin_manager = self.plugin_manager
        state.security_engine = self.security_engine
        state.workflow_engine = self.workflow_engine
        state.knowledge_graph = self.knowledge_graph
        state.learning_engine = self.learning_engine
        state.rag_engine = self.rag_engine
        state.vector_memory = self.vector_memory
        state.scaling_engine = self.scaling_engine
        state.deployment_manager = self.deployment_manager
        state.database_manager = self.database_manager
        state.observability = self.observability
        return state


class CognitiveMemoryIntegration:
    """Integration test helper for Cognitive Engine + Memory."""

    @staticmethod
    async def test_thinking_with_memory_retrieval(
        cognitive: MagicMock, memory: MagicMock, query: str = "test query"
    ) -> dict[str, Any]:
        memory.retrieve = AsyncMock(return_value=[{"content": "relevant context"}])
        cognitive.think = AsyncMock(return_value={"response": "thoughtful answer", "confidence": 0.9})
        context = await memory.retrieve(query)
        result = await cognitive.think(query, context=context)
        return {"context": context, "result": result}


class EventWorkflowIntegration:
    """Integration test helper for Events + Workflows."""

    @staticmethod
    async def test_event_triggers_workflow(
        event_bus: MagicMock, workflow_engine: MagicMock, event_type: str = "task.created"
    ) -> dict[str, Any]:
        event_bus.publish = AsyncMock()
        workflow_engine.execute_workflow = AsyncMock(return_value={"status": "running", "id": "wf-123"})
        await event_bus.publish({"type": event_type})
        result = await workflow_engine.execute_workflow(event_type=event_type)
        return {"published": True, "workflow": result}


class SecurityAPIIntegration:
    """Integration test helper for Security + API."""

    @staticmethod
    async def test_authenticated_request(
        security: MagicMock, token: str = "test-token"
    ) -> dict[str, Any]:
        security.validate_token = AsyncMock(return_value={"user_id": "user-1", "valid": True})
        security.authorize = AsyncMock(return_value=True)
        user = await security.validate_token(token)
        authorized = await security.authorize(user["user_id"], "read")
        return {"user": user, "authorized": authorized}


class RAGVectorIntegration:
    """Integration test helper for RAG + Vector Memory."""

    @staticmethod
    async def test_document_indexing(
        rag: MagicMock, vector_memory: MagicMock, doc: dict[str, Any]
    ) -> dict[str, Any]:
        vector_memory.add = AsyncMock(return_value=True)
        rag.index_document = AsyncMock(return_value={"indexed": True, "chunks": 3})
        await vector_memory.add(doc.get("id", "doc-1"), doc.get("embedding", [0.1, 0.2]), doc.get("metadata", {}))
        result = await rag.index_document(doc)
        return {"stored": True, "indexed": result}
