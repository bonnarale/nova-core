"""Tests for n8n integration routes and trigger service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from http import HTTPStatus

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.routes.n8n_integration import (
    N8nTriggerService,
    N8nTriggerRequest,
    N8nWebhookPayload,
    _validate_webhook_signature,
    router,
    set_dependencies,
)


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with n8n routes."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


class TestWebhookSignatureValidation:
    """Tests for HMAC webhook signature validation."""

    def test_valid_signature(self) -> None:
        """Test valid HMAC signature is accepted."""
        import hashlib
        import hmac as hmac_mod
        secret = "test-secret"
        payload = b'{"event": "test"}'
        expected = hmac_mod.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert _validate_webhook_signature(payload, expected, secret) is True

    def test_invalid_signature(self) -> None:
        """Test invalid HMAC signature is rejected."""
        assert _validate_webhook_signature(b'payload', "wrong-sig", "secret") is False

    def test_missing_signature(self) -> None:
        """Test missing signature returns False."""
        assert _validate_webhook_signature(b'payload', None, "secret") is False

    def test_empty_secret_no_crash(self) -> None:
        """Test empty secret doesn't crash."""
        assert _validate_webhook_signature(b'payload', "sig", "") is False


class TestWebhookEndpoint:
    """Tests for POST /api/v1/n8n/webhook."""

    def test_receive_webhook_no_secret(self, client: TestClient) -> None:
        """Test webhook accepted when no secret is configured."""
        with patch("app.api.v1.routes.n8n_integration.get_settings") as mock_settings:
            mock_settings.return_value.n8n_webhook_secret = None
            response = client.post(
                "/api/v1/n8n/webhook",
                json={"workflow_id": "wf-1", "event_type": "test", "data": {"key": "value"}},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "received"
            assert data["workflow_id"] == "wf-1"

    def test_receive_webhook_with_valid_signature(self, client: TestClient) -> None:
        """Test webhook accepted with valid HMAC signature."""
        import hashlib
        import hmac as hmac_mod
        import json as json_mod
        from pydantic import SecretStr

        secret = "test-secret"
        payload = {"workflow_id": "wf-1", "event_type": "test", "data": {}}
        raw_body = json_mod.dumps(payload, sort_keys=True).encode()
        sig = hmac_mod.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()

        with patch("app.api.v1.routes.n8n_integration.get_settings") as mock_settings:
            mock_settings.return_value.n8n_webhook_secret = SecretStr(secret)
            response = client.post(
                "/api/v1/n8n/webhook",
                json=payload,
                headers={"X-N8N-Signature": sig},
            )
            assert response.status_code == 200

    def test_receive_webhook_with_invalid_signature(self, client: TestClient) -> None:
        """Test webhook rejected with invalid HMAC signature."""
        from pydantic import SecretStr

        with patch("app.api.v1.routes.n8n_integration.get_settings") as mock_settings:
            mock_settings.return_value.n8n_webhook_secret = SecretStr("test-secret")
            response = client.post(
                "/api/v1/n8n/webhook",
                json={"workflow_id": "wf-1", "event_type": "test", "data": {}},
                headers={"X-N8N-Signature": "invalid-sig"},
            )
            assert response.status_code == 401


class TestTriggerEndpoint:
    """Tests for POST /api/v1/n8n/trigger/{workflow_id}."""

    def test_trigger_no_service(self, client: TestClient) -> None:
        """Test trigger returns 503 when service not configured."""
        set_dependencies(trigger_service=None)
        response = client.post(
            "/api/v1/n8n/trigger/wf-123",
            json={"payload": {"key": "value"}},
        )
        assert response.status_code == 503

    def test_trigger_success(self, client: TestClient) -> None:
        """Test trigger returns success when workflow executes."""
        mock_service = AsyncMock()
        mock_service.trigger_workflow = AsyncMock(return_value={
            "execution_id": "exec-123",
            "status": "triggered",
            "data": {},
        })
        set_dependencies(trigger_service=mock_service)
        response = client.post(
            "/api/v1/n8n/trigger/wf-123",
            json={"payload": {"key": "value"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["execution_id"] == "exec-123"
        set_dependencies(trigger_service=None)

    def test_trigger_connection_error(self, client: TestClient) -> None:
        """Test trigger returns 502 on connection error."""
        mock_service = AsyncMock()
        mock_service.trigger_workflow = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        set_dependencies(trigger_service=mock_service)
        response = client.post(
            "/api/v1/n8n/trigger/wf-123",
            json={"payload": {}},
        )
        assert response.status_code == 502
        set_dependencies(trigger_service=None)

    def test_trigger_timeout_error(self, client: TestClient) -> None:
        """Test trigger returns 504 on timeout."""
        mock_service = AsyncMock()
        mock_service.trigger_workflow = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        set_dependencies(trigger_service=mock_service)
        response = client.post(
            "/api/v1/n8n/trigger/wf-123",
            json={"payload": {}},
        )
        assert response.status_code == 504
        set_dependencies(trigger_service=None)


class TestN8nTriggerService:
    """Tests for N8nTriggerService."""

    @pytest.mark.asyncio
    async def test_initialize_creates_client(self) -> None:
        """Test initialize creates httpx client."""
        service = N8nTriggerService(base_url="http://n8n:5678", api_key="test-key")
        await service.initialize()
        assert service._client is not None
        await service.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_closes_client(self) -> None:
        """Test shutdown closes httpx client."""
        service = N8nTriggerService(base_url="http://n8n:5678")
        await service.initialize()
        await service.shutdown()
        assert service._client is None

    @pytest.mark.asyncio
    async def test_trigger_workflow_raises_when_not_initialized(self) -> None:
        """Test trigger raises when service not initialized."""
        service = N8nTriggerService(base_url="http://n8n:5678")
        with pytest.raises(RuntimeError, match="not initialized"):
            await service.trigger_workflow("wf-1", {"key": "value"})

    @pytest.mark.asyncio
    async def test_trigger_workflow_success(self) -> None:
        """Test trigger_workflow returns execution ID on success."""
        service = N8nTriggerService(base_url="http://n8n:5678", api_key="test-key")
        await service.initialize()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"executionId": "exec-456", "status": "success"}
        service._client.post = AsyncMock(return_value=mock_response)

        result = await service.trigger_workflow("wf-1", {"data": "test"})
        assert result["execution_id"] == "exec-456"
        assert result["status"] == "success"
        await service.shutdown()

    @pytest.mark.asyncio
    async def test_trigger_workflow_connection_error(self) -> None:
        """Test trigger raises on connection error."""
        service = N8nTriggerService(base_url="http://n8n:5678")
        await service.initialize()
        service._client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        with pytest.raises(httpx.ConnectError):
            await service.trigger_workflow("wf-1", {})
        await service.shutdown()
