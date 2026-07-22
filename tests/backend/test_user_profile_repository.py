"""Tests for UserProfileRepository."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.profile_repository import UserProfileRepository


class TestUserProfileRepository:
    @pytest.fixture
    def mock_session_factory(self):
        factory = MagicMock()
        session = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.get = AsyncMock()
        cm = MagicMock()
        cm.__aenter__.return_value = session
        cm.__aexit__.return_value = None
        factory.return_value = cm
        return factory

    @pytest.fixture
    def repo(self, mock_session_factory):
        return UserProfileRepository(mock_session_factory)

    @pytest.mark.asyncio
    async def test_create_profile(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        pid = "00000000-0000-0000-0000-000000000001"

        result = await repo.create_profile(pid, name="Ariel", bio="Creator")

        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        added = session.add.call_args[0][0]
        assert added.name == "Ariel"
        assert added.bio == "Creator"

    @pytest.mark.asyncio
    async def test_get_profile_found(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        profile = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = profile
        session.execute.return_value = result_mock

        result = await repo.get_profile("00000000-0000-0000-0000-000000000001")

        assert result is profile

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute.return_value = result_mock

        result = await repo.get_profile("00000000-0000-0000-0000-000000000001")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_profile_existing(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        profile = MagicMock()
        profile.name = "Old"
        session.get.return_value = profile

        result = await repo.update_profile(
            "00000000-0000-0000-0000-000000000001", name="New"
        )

        assert profile.name == "New"
        session.commit.assert_awaited_once()
        assert result is profile

    @pytest.mark.asyncio
    async def test_update_profile_not_found(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        session.get.return_value = None

        result = await repo.update_profile(
            "00000000-0000-0000-0000-000000000001", name="New"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_add_facts_new(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        profile = MagicMock()
        profile.facts = ["Ariel"]
        session.get.return_value = profile

        result = await repo.add_facts(
            "00000000-0000-0000-0000-000000000001", ["developer"]
        )

        assert profile.facts == ["Ariel", "developer"]
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_add_facts_skips_duplicates(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        profile = MagicMock()
        profile.facts = ["Ariel"]
        session.get.return_value = profile

        result = await repo.add_facts(
            "00000000-0000-0000-0000-000000000001", ["Ariel", "dev"]
        )

        assert profile.facts == ["Ariel", "dev"]
