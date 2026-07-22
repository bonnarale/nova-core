"""SQLAlchemy ORM models for NOVA CORE."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, backref, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(String(100), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    is_active = Column(Boolean, default=True, nullable=False)

    messages = relationship(
        "ConversationMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    __table_args__ = (
        Index("ix_messages_session_created", "session_id", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversation_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session = relationship(
        "ConversationSession",
        back_populates="messages",
    )


class OrchestratorTask(Base):
    __tablename__ = "orchestrator_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal = Column(Text, nullable=False)
    plan = Column(JSONB, nullable=True, default=dict)
    steps = Column(JSONB, nullable=True, default=list)
    current_step = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="CREATED")
    dependencies = Column(JSONB, nullable=True, default=list)
    artifacts = Column(JSONB, nullable=True, default=dict)
    events = Column(JSONB, nullable=True, default=list)
    assigned_agent = Column(String(100), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class Goal(Base):
    __tablename__ = "goals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="active")
    priority = Column(Integer, nullable=False, default=3)
    progress = Column(Integer, nullable=False, default=0)
    block_reason = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    role = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=False)
    allowed_tools = Column(JSONB, nullable=True, default=list)
    memory_scope = Column(String(20), nullable=False, default="session")
    permissions = Column(JSONB, nullable=True, default=dict)
    supported_models = Column(JSONB, nullable=True, default=list)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    preferences = Column(JSONB, nullable=True, default=dict)
    goals = Column(JSONB, nullable=True, default=list)
    facts = Column(JSONB, nullable=True, default=list)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class LongTermMemoryEntry(Base):
    __tablename__ = "long_term_memory"

    __table_args__ = (
        Index("ix_ltm_type_status", "memory_type", "status"),
        Index("ix_ltm_user_id", "user_id"),
        Index("ix_ltm_source", "source"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_type = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    tags = Column(JSONB, nullable=True, default=list)
    categories = Column(JSONB, nullable=True, default=list)
    entities = Column(JSONB, nullable=True, default=list)
    importance_score = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="active")
    linked_memory_ids = Column(JSONB, nullable=True, default=list)
    source = Column(String(50), nullable=False)
    source_id = Column(String(255), nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    project_id = Column(String(255), nullable=True)
    agent_id = Column(String(100), nullable=True)
    access_count = Column(Integer, nullable=False, default=0)
    metadata_ = Column("metadata", JSONB, nullable=True, default=dict)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    accessed_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    archived_at = Column(DateTime(timezone=True), nullable=True)


class WorkflowDefinitionModel(Base):
    __tablename__ = "workflow_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(20), nullable=False, default="1.0.0")
    steps = Column(JSONB, nullable=True, default=list)
    input_schema = Column(JSONB, nullable=True, default=dict)
    output_schema = Column(JSONB, nullable=True, default=dict)
    tags = Column(JSONB, nullable=True, default=list)
    metadata_ = Column("metadata", JSONB, nullable=True, default=dict)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class WorkflowExecutionModel(Base):
    __tablename__ = "workflow_executions"

    __table_args__ = (
        Index("ix_wf_exec_status", "status"),
        Index("ix_wf_exec_workflow", "workflow_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_definitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    workflow_name = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="PENDING")
    input_ = Column("input", JSONB, nullable=True, default=dict)
    output_ = Column("output", JSONB, nullable=True, default=dict)
    error = Column(Text, nullable=True)
    current_step_id = Column(String(100), nullable=True)
    step_executions = Column(JSONB, nullable=True, default=list)
    context = Column(JSONB, nullable=True, default=dict)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    session_id = Column(String(255), nullable=True)
    tags = Column(JSONB, nullable=True, default=list)
    metadata_ = Column("metadata", JSONB, nullable=True, default=dict)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class KnowledgeGraphEntityModel(Base):
    __tablename__ = "knowledge_graph_entities"

    __table_args__ = (
        Index("ix_kg_entity_type", "entity_type"),
        Index("ix_kg_entity_status", "status"),
        Index("ix_kg_entity_name", "name"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(30), nullable=False)
    name = Column(String(500), nullable=False)
    aliases = Column(JSONB, nullable=True, default=list)
    description = Column(Text, nullable=True, default="")
    tags = Column(JSONB, nullable=True, default=list)
    properties = Column(JSONB, nullable=True, default=dict)
    status = Column(String(20), nullable=False, default="ACTIVE")
    source = Column(String(100), nullable=True, default="manual")
    confidence = Column(Float, nullable=True, default=1.0)
    provenance = Column(JSONB, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class KnowledgeGraphRelationshipModel(Base):
    __tablename__ = "knowledge_graph_relationships"

    __table_args__ = (
        Index("ix_kg_rel_source", "source_id"),
        Index("ix_kg_rel_target", "target_id"),
        Index("ix_kg_rel_type", "relationship_type"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_graph_entities.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_graph_entities.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(30), nullable=False)
    properties = Column(JSONB, nullable=True, default=dict)
    weight = Column(Float, nullable=True, default=1.0)
    status = Column(String(20), nullable=False, default="ACTIVE")
    source = Column(String(100), nullable=True, default="manual")
    confidence = Column(Float, nullable=True, default=1.0)
    provenance = Column(JSONB, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class WorkflowEventModel(Base):
    __tablename__ = "workflow_events"

    __table_args__ = (
        Index("ix_wf_event_exec", "execution_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type = Column(String(30), nullable=False)
    step_id = Column(String(100), nullable=True)
    payload = Column(JSONB, nullable=True, default=dict)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
