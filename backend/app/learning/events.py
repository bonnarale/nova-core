"""Learning events — event type constants and helper factories.

Emitted via the shared EventBus so other subsystems (CognitiveEngine,
LongTermMemory, etc.) can react to learning lifecycle changes.
"""

from __future__ import annotations

from typing import Any

from app.learning.models import LearningEvent, LearningEventType


def knowledge_extracted_event(
    execution_id: str,
    artifact_count: int,
    task_id: str | None = None,
    user_id: str | None = None,
) -> LearningEvent:
    return LearningEvent(
        event_type=LearningEventType.KNOWLEDGE_EXTRACTED.value,
        payload={
            "execution_id": execution_id,
            "task_id": task_id,
            "artifact_count": artifact_count,
            "user_id": user_id,
        },
    )


def artifact_stored_event(
    artifact_id: str,
    artifact_type: str,
    source_execution_id: str | None = None,
) -> LearningEvent:
    return LearningEvent(
        event_type=LearningEventType.ARTIFACT_STORED.value,
        payload={
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "source_execution_id": source_execution_id,
        },
    )


def artifact_consolidated_event(
    merged_count: int,
    duplicates_removed: int,
    artifacts_affected: list[str] | None = None,
) -> LearningEvent:
    return LearningEvent(
        event_type=LearningEventType.ARTIFACT_CONSOLIDATED.value,
        payload={
            "merged_count": merged_count,
            "duplicates_removed": duplicates_removed,
            "artifacts_affected": artifacts_affected or [],
        },
    )


def memory_ranked_event(
    query: str,
    top_score: float,
    result_count: int,
) -> LearningEvent:
    return LearningEvent(
        event_type=LearningEventType.MEMORY_RANKED.value,
        payload={
            "query": query,
            "top_score": top_score,
            "result_count": result_count,
        },
    )


def retrieval_performed_event(
    query: str,
    result_count: int,
    user_id: str | None = None,
) -> LearningEvent:
    return LearningEvent(
        event_type=LearningEventType.RETRIEVAL_PERFORMED.value,
        payload={
            "query": query,
            "result_count": result_count,
            "user_id": user_id,
        },
    )


def execution_learned_event(
    execution_id: str,
    session_id: str,
    artifacts_extracted: int,
    artifacts_stored: int,
) -> LearningEvent:
    return LearningEvent(
        event_type=LearningEventType.EXECUTION_LEARNED.value,
        payload={
            "execution_id": execution_id,
            "session_id": session_id,
            "artifacts_extracted": artifacts_extracted,
            "artifacts_stored": artifacts_stored,
        },
    )
