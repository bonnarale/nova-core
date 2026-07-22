"""Pydantic schemas for the Reasoning Engine API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ReasoningStepSchema(BaseModel):
    description: str
    content: str
    step_type: str = "analysis"
    confidence: float = 0.0
    alternatives: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReasoningChainSchema(BaseModel):
    steps: list[ReasoningStepSchema] = Field(default_factory=list)
    conclusion: str = ""
    confidence: float = 0.0
    strategy: str = "DIRECT"
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationResultSchema(BaseModel):
    score: float = 0.0
    completeness: float = 0.0
    coherence: float = 0.0
    relevance: float = 0.0
    feedback: list[str] = Field(default_factory=list)


class ValidationResultSchema(BaseModel):
    is_valid: bool = True
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class CritiqueResultSchema(BaseModel):
    flaws: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    overall_assessment: str = ""


class ReasoningRequest(BaseModel):
    query: str
    user_id: str | None = None
    session_id: str | None = None
    strategy: str | None = None
    constraints: list[str] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)
    context_data: dict[str, Any] = Field(default_factory=dict)


class ReasoningResponse(BaseModel):
    query: str
    conclusion: str
    confidence: float
    chain: ReasoningChainSchema | None = None
    evaluation: EvaluationResultSchema | None = None
    validation: ValidationResultSchema | None = None
    critique: CritiqueResultSchema | None = None
    status: str
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
