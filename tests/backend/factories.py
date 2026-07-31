from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


class EventBusFactory:
    """Create InMemoryEventBus instances."""

    @staticmethod
    def create(**overrides) -> Any:
        from app.events.bus import InMemoryEventBus
        return InMemoryEventBus()


class EventFactory:
    """Create Event schema instances."""

    @staticmethod
    def create(event_type: str = "test.event", **overrides) -> Any:
        from app.events.schemas import Event, EventType, EventPriority, EventStatus
        defaults = {
            "id": str(uuid.uuid4()),
            "type": EventType(event_type) if event_type in [e.value for e in EventType] else EventType.CONVERSATION_CREATED,
            "source": "test",
            "timestamp": datetime.now(timezone.utc),
            "priority": EventPriority.NORMAL,
            "status": EventStatus.CREATED,
            "payload": {},
        }
        defaults.update(overrides)
        return Event(**defaults)


class SecurityFactory:
    """Create security model instances."""

    @staticmethod
    def create_user(username: str = "testuser", **overrides) -> Any:
        from app.security.models import User
        defaults = {"id": str(uuid.uuid4()), "username": username, "email": f"{username}@test.com", "roles": [], "state": "active", "created_at": datetime.now(timezone.utc)}
        defaults.update(overrides)
        return User(**defaults)

    @staticmethod
    def create_token(user_id: str = "test", **overrides) -> Any:
        from app.security.models import Token
        defaults = {"id": str(uuid.uuid4()), "user_id": user_id, "token_type": "access", "expires_at": datetime.now(timezone.utc), "scopes": []}
        defaults.update(overrides)
        return Token(**defaults)

    @staticmethod
    def create_role(name: str = "user", **overrides) -> Any:
        from app.security.models import Role
        defaults = {"id": str(uuid.uuid4()), "name": name, "permissions": []}
        defaults.update(overrides)
        return Role(**defaults)

    @staticmethod
    def create_api_key(name: str = "test-key", **overrides) -> Any:
        from app.security.models import APIKey
        defaults = {"id": str(uuid.uuid4()), "name": name, "key": str(uuid.uuid4()), "user_id": "test", "scopes": [], "created_at": datetime.now(timezone.utc), "expires_at": None, "is_active": True}
        defaults.update(overrides)
        return APIKey(**defaults)


class WorkflowFactory:
    """Create workflow model instances."""

    @staticmethod
    def create_definition(name: str = "test-workflow", **overrides) -> Any:
        from app.workflows.models import WorkflowDefinition, WorkflowStatus
        defaults = {"id": str(uuid.uuid4()), "name": name, "description": f"Test workflow: {name}", "steps": [], "status": WorkflowStatus.DRAFT, "version": "1.0.0", "created_at": datetime.now(timezone.utc), "metadata": {}}
        defaults.update(overrides)
        return WorkflowDefinition(**defaults)

    @staticmethod
    def create_execution(workflow_id: str = "test", **overrides) -> Any:
        from app.workflows.models import WorkflowExecution, WorkflowStatus
        defaults = {"id": str(uuid.uuid4()), "workflow_id": workflow_id, "status": WorkflowStatus.RUNNING, "started_at": datetime.now(timezone.utc), "completed_at": None, "results": {}, "error": None}
        defaults.update(overrides)
        return WorkflowExecution(**defaults)


class PluginFactory:
    """Create plugin model instances."""

    @staticmethod
    def create_manifest(name: str = "test-plugin", **overrides) -> Any:
        from app.plugins.models import PluginManifest, PluginType
        defaults = {"name": name, "version": "1.0.0", "description": f"Test plugin: {name}", "author": "test", "plugin_type": PluginType.UTILITY, "entry_point": "test_plugin", "permissions": [], "dependencies": [], "min_nova_version": "0.1.0", "config_schema": {}}
        defaults.update(overrides)
        return PluginManifest(**defaults)

    @staticmethod
    def create_plugin_info(name: str = "test-plugin", **overrides) -> Any:
        from app.plugins.models import PluginInfo, PluginState
        defaults = {"id": str(uuid.uuid4()), "name": name, "version": "1.0.0", "state": PluginState.LOADED, "enabled": True, "loaded_at": datetime.now(timezone.utc), "error_count": 0, "metadata": {}}
        defaults.update(overrides)
        return PluginInfo(**defaults)


class SchedulerFactory:
    """Create scheduler model instances."""

    @staticmethod
    def create_job(name: str = "test-job", **overrides) -> Any:
        from app.scheduler.schemas import Job, JobStatus, JobType, TriggerType
        defaults = {"id": str(uuid.uuid4()), "name": name, "job_type": JobType.CUSTOM, "status": JobStatus.PENDING, "trigger_type": TriggerType.MANUAL, "payload": {}, "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc), "metadata": {}}
        defaults.update(overrides)
        return Job(**defaults)


class KnowledgeGraphFactory:
    """Create knowledge graph entities."""

    @staticmethod
    def create_entity(name: str = "test-entity", **overrides) -> Any:
        from app.knowledge_graph.models import Entity, EntityType, EntityStatus
        defaults = {"id": str(uuid.uuid4()), "name": name, "entity_type": EntityType.CONCEPT, "status": EntityStatus.ACTIVE, "properties": {}, "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)}
        defaults.update(overrides)
        return Entity(**defaults)

    @staticmethod
    def create_relationship(source_id: str = "s1", target_id: str = "t1", **overrides) -> Any:
        from app.knowledge_graph.models import Relationship, RelationshipType, RelationshipStatus
        defaults = {"id": str(uuid.uuid4()), "source_id": source_id, "target_id": target_id, "relationship_type": RelationshipType.RELATED_TO, "status": RelationshipStatus.ACTIVE, "properties": {}, "weight": 1.0, "created_at": datetime.now(timezone.utc)}
        defaults.update(overrides)
        return Relationship(**defaults)


class LongTermMemoryFactory:
    """Create long-term memory instances."""

    @staticmethod
    def create(content: str = "test memory", **overrides) -> Any:
        from app.long_term_memory.models import LongTermMemory, MemoryType, MemoryStatus
        defaults = {"id": str(uuid.uuid4()), "content": content, "memory_type": MemoryType.EPISODIC, "status": MemoryStatus.ACTIVE, "importance": 0.5, "access_count": 0, "created_at": datetime.now(timezone.utc), "last_accessed": None, "metadata": {}, "tags": [], "embeddings": []}
        defaults.update(overrides)
        return LongTermMemory(**defaults)


class LearningFactory:
    """Create learning model instances."""

    @staticmethod
    def create_artifact(title: str = "test-artifact", **overrides) -> Any:
        from app.learning.models import KnowledgeArtifact, ArtifactType
        defaults = {"id": str(uuid.uuid4()), "title": title, "content": f"Content for {title}", "artifact_type": ArtifactType.EXPERIENCE, "confidence": 0.8, "source": "test", "created_at": datetime.now(timezone.utc), "metadata": {}}
        defaults.update(overrides)
        return KnowledgeArtifact(**defaults)


class ToolFactory:
    """Create tool instances."""

    @staticmethod
    def create_spec(name: str = "test-tool", **overrides) -> Any:
        from app.tools.base import ToolSpec, ToolParam
        defaults = {"name": name, "description": f"Test tool: {name}", "params": [ToolParam(name="input", type="string", description="Input", required=True)], "version": "1.0.0"}
        defaults.update(overrides)
        return ToolSpec(**defaults)


class ScalingFactory:
    """Create scaling model instances."""

    @staticmethod
    def create_worker(name: str = "worker-1", **overrides) -> Any:
        from app.scaling.enums import WorkerState
        from app.scaling.models import WorkerInfo
        defaults = {"name": name, "state": WorkerState.IDLE, "current_task": None, "tasks_completed": 0, "tasks_failed": 0, "created_at": datetime.now(timezone.utc), "last_active": datetime.now(timezone.utc)}
        defaults.update(overrides)
        return WorkerInfo(**defaults)


class DeploymentFactory:
    """Create deployment model instances."""

    @staticmethod
    def create_config(env: str = "testing", **overrides) -> Any:
        from app.deployment.enums import DeployEnvironment, DeployState
        defaults = {"environment": DeployEnvironment(env), "state": DeployState.INITIALIZED, "version": "1.0.0", "created_at": datetime.now(timezone.utc), "config": {}}
        defaults.update(overrides)
        return defaults


class RAGFactory:
    """Create RAG model instances."""

    @staticmethod
    def create_document(title: str = "test-doc", **overrides) -> Any:
        from app.rag.schemas import DocumentStatus, IndexDocument
        defaults = {"id": str(uuid.uuid4()), "title": title, "content": f"Content for {title}", "source": "test", "status": DocumentStatus.INDEXED, "metadata": {}, "chunks_count": 1, "created_at": datetime.now(timezone.utc)}
        defaults.update(overrides)
        return IndexDocument(**defaults)

    @staticmethod
    def create_retrieval_result(query: str = "test query", **overrides) -> Any:
        from app.rag.schemas import RetrievalResult, RetrievalStatus
        defaults = {"query": query, "chunks": [], "scores": [], "status": RetrievalStatus.SUCCESS, "metadata": {}}
        defaults.update(overrides)
        return RetrievalResult(**defaults)
