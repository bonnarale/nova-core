"""Tests for SQLAlchemy ORM models."""

import uuid

import pytest
from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.models import Base, ConversationMessage, ConversationSession


class TestConversationSession:
    """Tests for ConversationSession model."""

    def test_table_name(self) -> None:
        assert ConversationSession.__tablename__ == "conversation_sessions"

    def test_primary_key(self) -> None:
        col = ConversationSession.__table__.c["id"]
        assert col.primary_key
        assert isinstance(col.type, UUID)
        assert col.type.as_uuid

    def test_agent_id_column(self) -> None:
        col = ConversationSession.__table__.c["agent_id"]
        assert not col.nullable
        assert isinstance(col.type, String)
        assert col.type.length == 100

    def test_created_at_has_server_default(self) -> None:
        col = ConversationSession.__table__.c["created_at"]
        assert isinstance(col.type, DateTime)
        assert col.server_default is not None

    def test_is_active_default_true(self) -> None:
        col = ConversationSession.__table__.c["is_active"]
        assert col.default.arg is True

    def test_has_messages_relationship(self) -> None:
        assert hasattr(ConversationSession, "messages")


class TestConversationMessage:
    """Tests for ConversationMessage model."""

    def test_table_name(self) -> None:
        assert ConversationMessage.__tablename__ == "conversation_messages"

    def test_primary_key(self) -> None:
        col = ConversationMessage.__table__.c["id"]
        assert col.primary_key
        assert isinstance(col.type, UUID)
        assert col.type.as_uuid

    def test_session_id_foreign_key(self) -> None:
        col = ConversationMessage.__table__.c["session_id"]
        assert isinstance(col.type, UUID)
        assert not col.nullable
        fk = list(col.foreign_keys)[0]
        assert fk.column.table.name == "conversation_sessions"

    def test_session_id_ondelete_cascade(self) -> None:
        col = ConversationMessage.__table__.c["session_id"]
        fk = list(col.foreign_keys)[0]
        assert fk.ondelete == "CASCADE"

    def test_role_column(self) -> None:
        col = ConversationMessage.__table__.c["role"]
        assert not col.nullable
        assert isinstance(col.type, String)
        assert col.type.length == 20

    def test_content_column(self) -> None:
        col = ConversationMessage.__table__.c["content"]
        assert not col.nullable
        assert isinstance(col.type, Text)

    def test_created_at_has_server_default(self) -> None:
        col = ConversationMessage.__table__.c["created_at"]
        assert isinstance(col.type, DateTime)
        assert col.server_default is not None

    def test_composite_index(self) -> None:
        indexes = ConversationMessage.__table__.indexes
        index_names = {idx.name for idx in indexes}
        assert "ix_messages_session_created" in index_names

    def test_has_session_relationship(self) -> None:
        assert hasattr(ConversationMessage, "session")


class TestBase:
    """Tests for Base declarative base."""

    def test_both_tables_registered(self) -> None:
        tables = Base.metadata.tables
        assert "conversation_sessions" in tables
        assert "conversation_messages" in tables

    def test_foreign_key_integrity(self) -> None:
        """Verify session_id FK references the correct column."""
        msg_table = Base.metadata.tables["conversation_messages"]
        session_table = Base.metadata.tables["conversation_sessions"]
        fk = list(msg_table.c["session_id"].foreign_keys)[0]
        assert fk.column.table == session_table
        assert fk.column.name == "id"
