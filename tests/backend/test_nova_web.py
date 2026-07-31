"""Tests for the NOVA Web Platform unified API."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.routes.nova_web import router


@pytest.fixture(autouse=True)
def _reset_singleton() -> None:
    """Reset module-level singletons so each test gets fresh state."""
    import app.api.v1.routes.nova_web as mod

    mod._components = None
    yield
    mod._components = None


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)

    # Mock kernel — returns a canned response shape the handler expects
    mock_kernel = AsyncMock()
    mock_kernel.run_agent = AsyncMock(return_value={
        "response": {"message": {"content": "Hello! How can I help you?"}},
    })
    app.state.kernel = mock_kernel

    # Mock conversation memory
    mock_memory = AsyncMock()
    mock_memory.ensure_session = AsyncMock()
    mock_memory.add_message = AsyncMock()
    mock_memory.get_history = AsyncMock(return_value=[])
    app.state.memory = mock_memory

    # Mock semantic memory
    mock_semantic_memory = AsyncMock()
    mock_semantic_memory.search = AsyncMock(return_value=[])
    mock_semantic_memory.store = AsyncMock()
    app.state.semantic_memory = mock_semantic_memory

    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# 1. Dashboard
# ---------------------------------------------------------------------------

class TestDashboard:
    def test_returns_all_sections(self, client: TestClient) -> None:
        resp = client.get("/nova-web/dashboard")
        assert resp.status_code == 200
        body = resp.json()
        for key in (
            "system_status",
            "objectives",
            "projects",
            "approvals",
            "recommendations",
            "backlog",
            "roadmaps",
            "metrics",
            "lifecycle",
        ):
            assert key in body, f"missing key: {key}"

    def test_objectives_structure(self, client: TestClient) -> None:
        body = client.get("/nova-web/dashboard").json()
        assert "count" in body["objectives"]
        assert "items" in body["objectives"]
        assert isinstance(body["objectives"]["items"], list)

    def test_metrics_has_snapshots(self, client: TestClient) -> None:
        body = client.get("/nova-web/dashboard").json()
        assert "counters" in body["metrics"]
        assert "gauges" in body["metrics"]
        assert "histograms" in body["metrics"]

    def test_lifecycle_has_phase(self, client: TestClient) -> None:
        body = client.get("/nova-web/dashboard").json()
        assert "phase" in body["lifecycle"]


# ---------------------------------------------------------------------------
# 2. Chat — basic behaviour
# ---------------------------------------------------------------------------

class TestChat:
    def test_empty_message_rejected(self, client: TestClient) -> None:
        resp = client.post("/nova-web/chat", json={"message": ""})
        assert resp.status_code == 400

    def test_returns_required_fields(self, client: TestClient) -> None:
        resp = client.post("/nova-web/chat", json={"message": "hello"})
        assert resp.status_code == 200
        body = resp.json()
        for key in (
            "response",
            "session_id",
            "actions_taken",
            "objectives",
            "projects",
            "tasks",
            "approval_required",
        ):
            assert key in body, f"missing key: {key}"

    def test_response_text_is_non_empty(self, client: TestClient) -> None:
        body = client.post(
            "/nova-web/chat", json={"message": "hello"}
        ).json()
        assert body["response"]  # non-empty string

    def test_non_objective_no_actions(self, client: TestClient) -> None:
        body = client.post(
            "/nova-web/chat", json={"message": "What is the weather today?"}
        ).json()
        assert body["actions_taken"] == []
        assert body["objectives"] == []
        assert body["projects"] == []
        assert body["approval_required"] is False


# ---------------------------------------------------------------------------
# 3. Chat — objective creation
# ---------------------------------------------------------------------------

class TestChatObjectiveCreation:
    def test_build_returns_valid_response(self, client: TestClient) -> None:
        body = client.post(
            "/nova-web/chat",
            json={"message": "Build a personal website"},
        ).json()
        assert body["response"]  # non-empty
        assert body["session_id"]
        assert isinstance(body["actions_taken"], list)
        assert isinstance(body["objectives"], list)
        assert isinstance(body["projects"], list)
        assert isinstance(body["tasks"], list)
        assert body["approval_required"] is False

    def test_learn_returns_valid_response(self, client: TestClient) -> None:
        body = client.post(
            "/nova-web/chat",
            json={"message": "Learn AI and machine learning"},
        ).json()
        assert body["response"]
        assert body["session_id"]

    def test_create_roadmap_returns_valid_response(self, client: TestClient) -> None:
        body = client.post(
            "/nova-web/chat",
            json={"message": "Create a roadmap for our product launch"},
        ).json()
        assert body["response"]
        assert body["session_id"]

    def test_implement_returns_valid_response(self, client: TestClient) -> None:
        body = client.post(
            "/nova-web/chat",
            json={"message": "Implement a new authentication system"},
        ).json()
        assert body["response"]
        assert body["session_id"]

    def test_want_to_returns_valid_response(self, client: TestClient) -> None:
        body = client.post(
            "/nova-web/chat",
            json={"message": "I want to start a company"},
        ).json()
        assert body["response"]
        assert body["session_id"]


# ---------------------------------------------------------------------------
# 4. Objectives endpoint
# ---------------------------------------------------------------------------

class TestObjectivesEndpoint:
    def test_returns_list(self, client: TestClient) -> None:
        resp = client.get("/nova-web/objectives")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# 5. Projects endpoint
# ---------------------------------------------------------------------------

class TestProjectsEndpoint:
    def test_returns_list(self, client: TestClient) -> None:
        resp = client.get("/nova-web/projects")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# 6. Roadmaps endpoint
# ---------------------------------------------------------------------------

class TestRoadmapsEndpoint:
    def test_returns_list(self, client: TestClient) -> None:
        resp = client.get("/nova-web/roadmaps")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# 7. Tasks endpoint
# ---------------------------------------------------------------------------

class TestTasksEndpoint:
    def test_returns_list(self, client: TestClient) -> None:
        resp = client.get("/nova-web/tasks")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# 8. Backlog endpoint
# ---------------------------------------------------------------------------

class TestBacklogEndpoint:
    def test_returns_list(self, client: TestClient) -> None:
        resp = client.get("/nova-web/backlog")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# 9 & 10. Approvals endpoint + approve/reject
# ---------------------------------------------------------------------------

class TestApprovalsEndpoint:
    def test_returns_list(self, client: TestClient) -> None:
        resp = client.get("/nova-web/approvals")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_approve_nonexistent_returns_404(self, client: TestClient) -> None:
        resp = client.post("/nova-web/approvals/nonexistent/approve")
        assert resp.status_code == 404

    def test_reject_nonexistent_returns_404(self, client: TestClient) -> None:
        resp = client.post("/nova-web/approvals/nonexistent/reject")
        assert resp.status_code == 404

    def test_approve_then_reject_cycle(self, client: TestClient) -> None:
        from app.command_center import CommandCenterFactory

        comps = CommandCenterFactory.create_all()
        import app.api.v1.routes.nova_web as mod

        mod._components = comps
        approval = comps["approvals"].request(
            action_type="deploy",
            description="Deploy to production",
            risk_level="high",
        )

        resp = client.post(f"/nova-web/approvals/{approval.id}/approve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

        approval2 = comps["approvals"].request(
            action_type="deploy",
            description="Deploy v2",
            risk_level="critical",
        )
        resp2 = client.post(f"/nova-web/approvals/{approval2.id}/reject")
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "rejected"


# ---------------------------------------------------------------------------
# 11 & 12. Recommendations endpoint + accept
# ---------------------------------------------------------------------------

class TestRecommendationsEndpoint:
    def test_returns_list(self, client: TestClient) -> None:
        resp = client.get("/nova-web/recommendations")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_accept_nonexistent_returns_404(self, client: TestClient) -> None:
        resp = client.post("/nova-web/recommendations/nonexistent/accept")
        assert resp.status_code == 404

    def test_accept_recommendation(self, client: TestClient) -> None:
        from app.command_center import CommandCenterFactory

        comps = CommandCenterFactory.create_all()
        import app.api.v1.routes.nova_web as mod

        mod._components = comps
        rec = comps["recommendations"].create(
            category="performance",
            title="Optimize queries",
            description="Reduce DB query time",
            priority="high",
        )

        resp = client.post(f"/nova-web/recommendations/{rec.id}/accept")
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"


# ---------------------------------------------------------------------------
# 13. Memory endpoint
# ---------------------------------------------------------------------------

class TestMemoryEndpoint:
    def test_returns_memory_sections(self, client: TestClient) -> None:
        resp = client.get("/nova-web/memory")
        assert resp.status_code == 200
        body = resp.json()
        assert "learning" in body
        assert "vector_memory" in body
        assert "knowledge_graph" in body
        assert "command_center_memory" in body

    def test_learning_has_status_or_dict(self, client: TestClient) -> None:
        body = client.get("/nova-web/memory").json()
        learning = body["learning"]
        assert isinstance(learning, dict)


# ---------------------------------------------------------------------------
# 14. Observability endpoint
# ---------------------------------------------------------------------------

class TestObservabilityEndpoint:
    def test_returns_all_sections(self, client: TestClient) -> None:
        resp = client.get("/nova-web/observability")
        assert resp.status_code == 200
        body = resp.json()
        assert "metrics" in body
        assert "traces" in body
        assert "health" in body

    def test_metrics_structure(self, client: TestClient) -> None:
        body = client.get("/nova-web/observability").json()
        assert "counters" in body["metrics"]
        assert "gauges" in body["metrics"]

    def test_traces_has_total_spans(self, client: TestClient) -> None:
        body = client.get("/nova-web/observability").json()
        assert "total_spans" in body["traces"]


# ---------------------------------------------------------------------------
# 15. Tools endpoint
# ---------------------------------------------------------------------------

class TestToolsEndpoint:
    def test_returns_tool_sections(self, client: TestClient) -> None:
        resp = client.get("/nova-web/tools")
        assert resp.status_code == 200
        body = resp.json()
        assert "orchestrator" in body
        assert "autonomy" in body
        assert "optimization" in body

    def test_autonomy_has_level(self, client: TestClient) -> None:
        body = client.get("/nova-web/tools").json()
        assert "level" in body["autonomy"]


# ---------------------------------------------------------------------------
# Integration: chat → list round-trip
# ---------------------------------------------------------------------------

class TestChatIntegration:
    def test_chat_returns_response_and_session(self, client: TestClient) -> None:
        resp = client.post(
            "/nova-web/chat",
            json={"message": "Build a recommendation engine"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["response"]
        assert body["session_id"]

    def test_multiple_chats_return_independent_sessions(self, client: TestClient) -> None:
        r1 = client.post("/nova-web/chat", json={"message": "Build frontend"})
        r2 = client.post("/nova-web/chat", json={"message": "Create backend API"})
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["session_id"] != r2.json()["session_id"]
