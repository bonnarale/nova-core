"""Tests for ConversationMemory service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.memory.conversation_memory import ConversationMemory


@pytest.fixture
def memory():
    """Module-level fixture so both test classes can use it."""
    db = MagicMock()
    db.session_factory = MagicMock()
    return ConversationMemory(db)


class TestConversationMemory:
    """Tests for ConversationMemory service."""

    @pytest.mark.asyncio
    async def test_ensure_session_delegates_to_repo(self, memory):
        session_id = "00000000-0000-0000-0000-000000000001"
        agent_id = "assistant"

        with patch.object(memory._repo, "ensure_session", new_callable=AsyncMock) as mock:
            await memory.ensure_session(session_id, agent_id)
            mock.assert_awaited_once_with(session_id, agent_id)

    @pytest.mark.asyncio
    async def test_add_message_delegates_to_repo(self, memory):
        session_id = "00000000-0000-0000-0000-000000000001"

        with patch.object(memory._repo, "add_message", new_callable=AsyncMock) as mock:
            await memory.add_message(session_id, "user", "test")
            mock.assert_awaited_once_with(session_id, "user", "test")

    @pytest.mark.asyncio
    async def test_get_history_delegates_to_repo(self, memory):
        session_id = "00000000-0000-0000-0000-000000000001"
        expected = [{"role": "user", "content": "test"}]

        with patch.object(memory._repo, "get_history", new_callable=AsyncMock) as mock:
            mock.return_value = expected
            result = await memory.get_history(session_id, limit=10)
            mock.assert_awaited_once_with(session_id, limit=10)
            assert result == expected

    @pytest.mark.asyncio
    async def test_get_history_default_limit(self, memory):
        session_id = "00000000-0000-0000-0000-000000000001"

        with patch.object(memory._repo, "get_history", new_callable=AsyncMock) as mock:
            await memory.get_history(session_id)
            mock.assert_awaited_once_with(session_id, limit=20)


class TestMemoryProvider:
    """Tests that ConversationMemory satisfies MemoryProvider interface."""

    def test_implements_memory_provider(self, memory):
        from app.memory.base import MemoryProvider
        assert isinstance(memory, MemoryProvider)

    def test_has_all_abstract_methods(self):
        from app.memory.base import MemoryProvider
        import inspect

        methods = [
            m for m in dir(MemoryProvider)
            if inspect.iscoroutinefunction(getattr(MemoryProvider, m))
        ]
        expected = {"ensure_session", "add_message", "get_history"}
        assert set(methods) == expected
