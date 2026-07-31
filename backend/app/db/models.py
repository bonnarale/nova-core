"""SQLAlchemy ORM models for NOVA CORE."""

import uuid

import sqlalchemy as sa
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
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


class ProjectORM(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True, default="")
    objective_id = Column(String, nullable=True)
    goal_id = Column(
        UUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="SET NULL"),
        nullable=True,
    )
    workflow_id = Column(String, nullable=True)
    status = Column(String(20), nullable=False, default="planning")
    progress = Column(Float, nullable=False, default=0.0)
    owner = Column(String(255), nullable=True, default="")
    budget = Column(JSONB, nullable=True, default=dict)
    decisions = Column(JSONB, nullable=True, default=list)
    phases = Column(JSONB, nullable=True, default=list)
    milestones = Column(JSONB, nullable=True, default=list)
    documents = Column(JSONB, nullable=True, default=list)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ActivityLog(Base):
    __tablename__ = "activity_log"

    __table_args__ = (
        Index("ix_activity_log_user_created", "user_id", "created_at"),
        Index("ix_activity_log_goal", "goal_id"),
        Index("ix_activity_log_tool", "tool_name"),
        Index("ix_activity_log_session", "session_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_id = Column(
        UUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    action = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    goal_title = Column(String(255), nullable=True)
    goal_priority = Column(Integer, nullable=True)
    approval_id = Column(String(100), nullable=True)
    reason = Column(Text, nullable=True)
    details = Column(JSONB, nullable=True, default=dict)
    # Tool tracking fields
    tool_name = Column(String(100), nullable=True)
    tool_params = Column(JSONB, nullable=True, default=dict)
    tool_result = Column(JSONB, nullable=True, default=dict)
    duration_ms = Column(Integer, nullable=True)
    session_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


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
