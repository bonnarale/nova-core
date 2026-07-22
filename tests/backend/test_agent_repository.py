"""Tests for AgentRepository."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.agent_repository import AgentRepository


class TestAgentRepository:
    @pytest.fixture
    def mock_session_factory(self):
        factory = MagicMock()
        session = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.get = AsyncMock()
        session.delete = AsyncMock()
        cm = MagicMock()
        cm.__aenter__.return_value = session
        cm.__aexit__.return_value = None
        factory.return_value = cm
        return factory

    @pytest.fixture
    def repo(self, mock_session_factory):
        return AgentRepository(mock_session_factory)

    @pytest.mark.asyncio
    async def test_create(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        session.add = MagicMock()

        agent = await repo.create(
            agent_id="test-agent",
            name="Test Agent",
            role="tester",
        )
        assert agent.id == "test-agent"
        assert agent.name == "Test Agent"
        session.add.assert_called_once()
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_found(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        session.get = AsyncMock(return_value=MagicMock(id="found", name="Found"))

        result = await repo.get("found")
        assert result is not None
        assert result.id == "found"

    @pytest.mark.asyncio
    async def test_get_not_found(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        session.get = AsyncMock(return_value=None)

        result = await repo.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_list(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            MagicMock(id="a"), MagicMock(id="b"),
        ]
        session.execute = AsyncMock(return_value=mock_result)

        agents = await repo.list()
        assert len(agents) == 2

    @pytest.mark.asyncio
    async def test_update(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        agent_mock = MagicMock(id="upd", name="Original")
        session.get = AsyncMock(return_value=agent_mock)

        updated = await repo.update("upd", name="Updated")
        assert updated is not None
        assert agent_mock.name == "Updated"
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        session.get = AsyncMock(return_value=None)

        result = await repo.update("nonexistent", name="Nope")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_existing(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        session.get = AsyncMock(return_value=MagicMock(id="del"))

        result = await repo.delete("del")
        assert result is True
        session.delete.assert_called_once()
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        session.get = AsyncMock(return_value=None)

        result = await repo.delete("nonexistent")
        assert result is False
