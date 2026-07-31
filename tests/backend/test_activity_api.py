"""Tests for Activity API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.routes.activity import router, ActivityEntry, ActivityListResponse


def _make_mock_entry(
    entry_id: Any = None,
    goal_id: Any = None,
    goal_title: str = "Test Goal",
    action: str = "reviewed",
    status: str = "executed",
    goal_priority: int = 3,
    approval_id: str | None = None,
    reason: str | None = None,
    details: dict | None = None,
) -> MagicMock:
    entry = MagicMock()
    entry.id = entry_id or uuid4()
    entry.goal_id = goal_id
    entry.goal_title = goal_title
    entry.action = action
    entry.status = status
    entry.goal_priority = goal_priority
    entry.approval_id = approval_id
    entry.reason = reason
    entry.details = details or {}
    entry.created_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return entry


def _make_app_with_mock_repo(repo: MagicMock) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.activity_repository = repo
    return app


class TestActivityAPI:
    """Tests for Activity API endpoints."""

    def test_get_activity_returns_200_with_entries(self) -> None:
        """GET /api/v1/activity returns 200 with a list of entries."""
        repo = MagicMock()
        repo.list_recent = AsyncMock(
            return_value=[
                _make_mock_entry(goal_title="Goal A"),
                _make_mock_entry(goal_title="Goal B"),
            ]
        )
        app = _make_app_with_mock_repo(repo)
        client = TestClient(app)

        response = client.get("/activity/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["entries"]) == 2
        assert data["entries"][0]["goal_title"] == "Goal A"
        assert data["entries"][1]["goal_title"] == "Goal B"
        repo.list_recent.assert_awaited_once_with(limit=20)

    def test_get_activity_respects_limit(self) -> None:
        """GET /api/v1/activity/?limit=5 respects the limit parameter."""
        repo = MagicMock()
        repo.list_recent = AsyncMock(return_value=[])
        app = _make_app_with_mock_repo(repo)
        client = TestClient(app)

        response = client.get("/activity/?limit=5")

        assert response.status_code == 200
        repo.list_recent.assert_awaited_once_with(limit=5)

    def test_get_activity_respects_min_limit(self) -> None:
        """GET /api/v1/activity/?limit=0 returns 422 (validation error)."""
        repo = MagicMock()
        repo.list_recent = AsyncMock(return_value=[])
        app = _make_app_with_mock_repo(repo)
        client = TestClient(app)

        response = client.get("/activity/?limit=0")

        assert response.status_code == 422

    def test_get_activity_respects_max_limit(self) -> None:
        """GET /api/v1/activity/?limit=101 returns 422 (validation error)."""
        repo = MagicMock()
        repo.list_recent = AsyncMock(return_value=[])
        app = _make_app_with_mock_repo(repo)
        client = TestClient(app)

        response = client.get("/activity/?limit=101")

        assert response.status_code == 422

    def test_get_activity_empty_database(self) -> None:
        """GET /api/v1/activity/ returns empty list when database is empty."""
        repo = MagicMock()
        repo.list_recent = AsyncMock(return_value=[])
        app = _make_app_with_mock_repo(repo)
        client = TestClient(app)

        response = client.get("/activity/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["entries"] == []

    def test_get_activity_by_goal(self) -> None:
        """GET /api/v1/activity/goal/{goal_id} returns entries for a goal."""
        repo = MagicMock()
        goal_id = uuid4()
        repo.list_by_goal = AsyncMock(
            return_value=[
                _make_mock_entry(goal_id=goal_id, goal_title="Specific Goal"),
            ]
        )
        app = _make_app_with_mock_repo(repo)
        client = TestClient(app)

        response = client.get(f"/activity/goal/{goal_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["entries"][0]["goal_title"] == "Specific Goal"
        repo.list_by_goal.assert_awaited_once()

    def test_get_activity_by_goal_invalid_id(self) -> None:
        """GET /api/v1/activity/goal/not-a-uuid returns 400."""
        repo = MagicMock()
        app = _make_app_with_mock_repo(repo)
        client = TestClient(app)

        response = client.get("/activity/goal/not-a-uuid")

        assert response.status_code == 400
        assert "Invalid goal ID" in response.json()["detail"]

    def test_activity_entry_serialization(self) -> None:
        """ActivityEntry model serializes correctly."""
        entry = ActivityEntry(
            id="test-id",
            goal_id="goal-123",
            goal_title="Test Goal",
            action="reviewed",
            status="executed",
            goal_priority=3,
            approval_id="approval-456",
            reason=None,
            details={"key": "value"},
            created_at="2026-01-01T12:00:00+00:00",
        )
        d = entry.model_dump()
        assert d["id"] == "test-id"
        assert d["goal_id"] == "goal-123"
        assert d["details"] == {"key": "value"}

    def test_activity_list_response_serialization(self) -> None:
        """ActivityListResponse model serializes correctly."""
        resp = ActivityListResponse(
            entries=[
                ActivityEntry(
                    id="e1",
                    action="reviewed",
                    status="executed",
                    created_at="2026-01-01T12:00:00+00:00",
                )
            ],
            total=1,
        )
        d = resp.model_dump()
        assert d["total"] == 1
        assert len(d["entries"]) == 1

    def test_activity_entry_optional_fields(self) -> None:
        """ActivityEntry handles None optional fields."""
        entry = ActivityEntry(
            id="test-id",
            action="reviewed",
            status="skipped",
            created_at="2026-01-01T12:00:00+00:00",
        )
        d = entry.model_dump()
        assert d["goal_id"] is None
        assert d["goal_title"] is None
        assert d["goal_priority"] is None
        assert d["approval_id"] is None
        assert d["reason"] is None
        assert d["details"] == {}

    def test_get_activity_by_goal_empty(self) -> None:
        """GET /api/v1/activity/goal/{goal_id} returns empty list when no entries."""
        repo = MagicMock()
        goal_id = uuid4()
        repo.list_by_goal = AsyncMock(return_value=[])
        app = _make_app_with_mock_repo(repo)
        client = TestClient(app)

        response = client.get(f"/activity/goal/{goal_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["entries"] == []
