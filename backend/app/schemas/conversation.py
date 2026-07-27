"""Pydantic schemas for conversation domain."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ConversationSessionSchema(BaseModel):
    id: UUID
    agent_id: str
    created_at: datetime
    is_active: bool


class ConversationMessageSchema(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    created_at: datetime


class ConversationHistorySchema(BaseModel):
    session_id: UUID
    messages: list[ConversationMessageSchema]
