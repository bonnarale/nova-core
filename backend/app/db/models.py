"""SQLAlchemy ORM models for NOVA CORE."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
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
