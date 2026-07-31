"""Unit tests for PostgresLearningStore using mock async sessions."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.learning.models import ArtifactType, KnowledgeArtifact
from app.learning.postgres_store import PostgresLearningStore


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_session_factory(mock_session):
    factory = MagicMock()
    # Make it an async context manager
    factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return factory


@pytest.fixture
def store(mock_session_factory):
    return PostgresLearningStore(session_factory=mock_session_factory)


def _sample_artifact(**overrides) -> KnowledgeArtifact:
    defaults = {
        "id": str(uuid4()),
        "artifact_type": ArtifactType.PROCEDURE.value,
        "content": "Test content about API setup",
        "summary": "API setup procedure",
        "tags": ["api", "rest"],
        "confidence": 0.8,
        "importance_score": 0.7,
    }
    defaults.update(overrides)
    return KnowledgeArtifact(**defaults)


# ======================================================================
# Create
# ======================================================================

class TestPostgresLearningStoreCreate:
    @pytest.mark.asyncio
    async def test_create_sets_timestamps(self, store, mock_session):
        artifact = _sample_artifact()
        artifact.created_at = ""
        artifact.updated_at = ""

        result = await store.create(artifact)

        assert result.created_at != ""
        assert result.updated_at != ""
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_preserves_existing_timestamps(self, store, mock_session):
        artifact = _sample_artifact()
        artifact.created_at = "2026-01-01T00:00:00+00:00"
        artifact.updated_at = "2026-01-01T00:00:00+00:00"

        result = await store.create(artifact)

        assert result.created_at == "2026-01-01T00:00:00+00:00"

    @pytest.mark.asyncio
    async def test_create_calls_upsert(self, store, mock_session):
        artifact = _sample_artifact()
        await store.create(artifact)

        # Verify the execute was called (upsert statement)
        call_args = mock_session.execute.call_args
        assert call_args is not None


# ======================================================================
# Get
# ======================================================================

class TestPostgresLearningStoreGet:
    @pytest.mark.asyncio
    async def test_get_returns_artifact(self, store, mock_session):
        now = datetime.now(tz=timezone.utc)
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = {
            "id": uuid4(),
            "artifact_type": "procedure",
            "content": "test content",
            "summary": "test summary",
            "tags": ["api"],
            "source_execution_id": None,
            "source_task_id": None,
            "user_id": None,
            "agent_id": None,
            "confidence": 0.8,
            "importance_score": 0.7,
            "access_count": 0,
            "metadata_": {},
            "created_at": now,
            "updated_at": now,
        }
        mock_session.execute.return_value = mock_result

        result = await store.get(str(uuid4()))

        assert result is not None
        assert result.content == "test content"

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing(self, store, mock_session):
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        result = await store.get(str(uuid4()))

        assert result is None


# ======================================================================
# Update
# ======================================================================

class TestPostgresLearningStoreUpdate:
    @pytest.mark.asyncio
    async def test_update_returns_artifact(self, store, mock_session):
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        artifact = _sample_artifact()
        result = await store.update(artifact)

        assert result is not None
        assert result.id == artifact.id
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_returns_none_for_missing(self, store, mock_session):
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        artifact = _sample_artifact()
        result = await store.update(artifact)

        assert result is None


# ======================================================================
# Delete
# ======================================================================

class TestPostgresLearningStoreDelete:
    @pytest.mark.asyncio
    async def test_delete_returns_true(self, store, mock_session):
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await store.delete(str(uuid4()))

        assert result is True
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_returns_false_for_missing(self, store, mock_session):
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await store.delete(str(uuid4()))

        assert result is False


# ======================================================================
# List operations
# ======================================================================

class TestPostgresLearningStoreList:
    @pytest.mark.asyncio
    async def test_list_by_user(self, store, mock_session):
        now = datetime.now(tz=timezone.utc)
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [
            {
                "id": uuid4(),
                "artifact_type": "fact",
                "content": "user fact",
                "summary": "",
                "tags": [],
                "source_execution_id": None,
                "source_task_id": None,
                "user_id": uuid4(),
                "agent_id": None,
                "confidence": 0.5,
                "importance_score": 0.5,
                "access_count": 0,
                "metadata_": {},
                "created_at": now,
                "updated_at": now,
            }
        ]
        mock_session.execute.return_value = mock_result

        results = await store.list_by_user(str(uuid4()))

        assert len(results) == 1
        assert results[0].content == "user fact"

    @pytest.mark.asyncio
    async def test_count(self, store, mock_session):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        mock_session.execute.return_value = mock_result

        count = await store.count()

        assert count == 42

    @pytest.mark.asyncio
    async def test_count_by_type(self, store, mock_session):
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("procedure", 5),
            ("fact", 3),
        ]
        mock_session.execute.return_value = mock_result

        counts = await store.count_by_type()

        assert counts == {"procedure": 5, "fact": 3}
