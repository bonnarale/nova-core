"""Tests for ConversationRepository."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.db.repository import ConversationRepository


class TestConversationRepository:
    """Tests for ConversationRepository."""

    @pytest.fixture
    def mock_session_factory(self):
        """Create a mock async_sessionmaker that yields a controlled session."""
        factory = MagicMock()
        session = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        # async with factory() as session  ->  await cm.__aenter__() == session
        cm = MagicMock()
        cm.__aenter__.return_value = session
        cm.__aexit__.return_value = None
        factory.return_value = cm

        return factory

    @pytest.fixture
    def repo(self, mock_session_factory):
        return ConversationRepository(mock_session_factory)

    def test_init_stores_session_factory(self, mock_session_factory):
        repo = ConversationRepository(mock_session_factory)
        assert repo._session_factory is mock_session_factory

    @pytest.mark.asyncio
    async def test_ensure_session_creates_when_not_found(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute.return_value = result_mock

        await repo.ensure_session(
            "00000000-0000-0000-0000-000000000001", "assistant"
        )

        session.execute.assert_awaited_once()
        session.add.assert_called_once()
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ensure_session_skips_when_exists(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        existing = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing
        session.execute.return_value = result_mock

        await repo.ensure_session(
            "00000000-0000-0000-0000-000000000001", "assistant"
        )

        session.add.assert_not_called()
        session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_message_creates_record(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value

        await repo.add_message(
            "00000000-0000-0000-0000-000000000001", "user", "Hello"
        )

        session.add.assert_called_once()
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_history_returns_ordered_messages(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        msg1 = MagicMock()
        msg1.role = "user"
        msg1.content = "first"
        msg2 = MagicMock()
        msg2.role = "assistant"
        msg2.content = "second"

        scalar_result = MagicMock()
        scalar_result.all.return_value = [msg1, msg2]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalar_result
        session.execute.return_value = result_mock

        history = await repo.get_history(
            "00000000-0000-0000-0000-000000000001"
        )

        assert history == [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "second"},
        ]
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_history_respects_limit(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        result_mock = MagicMock()
        scalar_result = MagicMock()
        scalar_result.all.return_value = []
        result_mock.scalars.return_value = scalar_result
        session.execute.return_value = result_mock

        await repo.get_history(
            "00000000-0000-0000-0000-000000000001", limit=5
        )

        executed_stmt = session.execute.call_args[0][0]
        assert executed_stmt._limit == 5
