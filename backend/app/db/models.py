"""SQLAlchemy ORM models for NOVA CORE."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
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
