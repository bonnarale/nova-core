"""Tests for UserProfileMemory service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.memory.profile import UserProfileMemory


@pytest.fixture
def mock_database():
    db = MagicMock()
    db.session_factory = MagicMock()
    return db


@pytest.fixture
def memory(mock_database):
    return UserProfileMemory(mock_database)


class TestUserProfileMemory:
    @pytest.mark.asyncio
    async def test_create_profile_returns_dict(self, memory):
        pid = "00000000-0000-0000-0000-000000000001"
        orm = MagicMock()
        orm.id = pid
        orm.name = "Ariel"
        orm.bio = None
        orm.preferences = {}
        orm.goals = []
        orm.facts = []
        orm.created_at = None
        orm.updated_at = None

        with patch.object(memory._repo, "create_profile", new_callable=AsyncMock) as mock:
            mock.return_value = orm
            result = await memory.create_profile(pid, name="Ariel")

        assert result["id"] == pid
        assert result["name"] == "Ariel"
        mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_profile_returns_none_when_missing(self, memory):
        with patch.object(memory._repo, "get_profile", new_callable=AsyncMock) as mock:
            mock.return_value = None
            result = await memory.get_profile("00000000-0000-0000-0000-000000000001")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_profile_returns_dict(self, memory):
        pid = "00000000-0000-0000-0000-000000000001"
        orm = MagicMock()
        orm.id = pid
        orm.name = "Ariel"
        orm.bio = "Bio"
        orm.preferences = {"lang": "Python"}
        orm.goals = ["build"]
        orm.facts = ["fact1"]
        orm.created_at = None
        orm.updated_at = None

        with patch.object(memory._repo, "get_profile", new_callable=AsyncMock) as mock:
            mock.return_value = orm
            result = await memory.get_profile(pid)

        assert result["name"] == "Ariel"
        assert result["bio"] == "Bio"
        assert result["preferences"] == {"lang": "Python"}
        assert result["goals"] == ["build"]
        assert result["facts"] == ["fact1"]

    @pytest.mark.asyncio
    async def test_update_profile_delegates(self, memory):
        pid = "00000000-0000-0000-0000-000000000001"

        with patch.object(memory._repo, "update_profile", new_callable=AsyncMock) as mock:
            await memory.update_profile(pid, bio="New bio")
            mock.assert_awaited_once_with(pid, None, "New bio", None, None, None)

    @pytest.mark.asyncio
    async def test_add_facts_delegates(self, memory):
        pid = "00000000-0000-0000-0000-000000000001"

        with patch.object(memory._repo, "add_facts", new_callable=AsyncMock) as mock:
            await memory.add_facts(pid, ["new fact"])
            mock.assert_awaited_once_with(pid, ["new fact"])


class TestProfileProvider:
    def test_implements_profile_provider(self, memory):
        from app.memory.profile import ProfileProvider
        assert isinstance(memory, ProfileProvider)
