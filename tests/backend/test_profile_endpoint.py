"""Tests for the /profile/{user_id} endpoint."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.memory.profile import UserProfileMemory


@pytest.fixture
def profile_memory():
    return MagicMock(spec=UserProfileMemory)


@pytest.fixture
def request_mock(profile_memory):
    req = MagicMock()
    req.app.state.profile_memory = profile_memory
    return req


class TestProfileEndpoint:
    @pytest.mark.asyncio
    async def test_get_profile_found(self, request_mock, profile_memory):
        from app.api.v1.routes.profile import get_profile

        profile_memory.get_profile.return_value = {
            "id": "00000000-0000-0000-0000-000000000001",
            "name": "Ariel",
            "bio": None,
            "preferences": {},
            "goals": [],
            "facts": [],
        }

        result = await get_profile(
            "00000000-0000-0000-0000-000000000001", request_mock
        )

        assert result["name"] == "Ariel"
        profile_memory.get_profile.assert_awaited_once_with(
            "00000000-0000-0000-0000-000000000001"
        )

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, request_mock, profile_memory):
        from app.api.v1.routes.profile import get_profile

        profile_memory.get_profile.return_value = None

        with pytest.raises(HTTPException) as exc:
            await get_profile(
                "00000000-0000-0000-0000-000000000001", request_mock
            )

        assert exc.value.status_code == 404
