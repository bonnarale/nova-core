"""n8n integration routes — webhook receiver and workflow trigger."""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["n8n"])

# Module-level dependency (set via set_dependencies)
_trigger_service: N8nTriggerService | None = None


class N8nWebhookPayload(BaseModel):
    """Payload received from n8n webhook."""

    workflow_id: str = ""
    event_type: str = "unknown"
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: str | None = None


class N8nTriggerRequest(BaseModel):
    """Request to trigger an n8n workflow."""

    payload: dict[str, Any] = Field(default_factory=dict)
    wait_for_completion: bool = False
    timeout_seconds: int = 30


class N8nTriggerService:
    """Service for triggering n8n workflows via HTTP."""

    def __init__(self, base_url: str, api_key: str = "") -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def initialize(self) -> None:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["X-N8N-API-KEY"] = self._api_key
        self._client = httpx.AsyncClient(base_url=self._base_url, headers=headers, timeout=30.0)
        logger.info("n8n trigger service initialized: %s", self._base_url)

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("n8n trigger service shutdown")

    async def trigger_workflow(self, workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Trigger an n8n workflow by ID via its webhook URL.

        Returns the execution ID or response data from n8n.
        Raises httpx errors on connection failure.
        """
        if not self._client:
            raise RuntimeError("n8n trigger service not initialized")

        webhook_url = f"/webhook/{workflow_id}"
        response = await self._client.post(webhook_url, json=payload)
        response.raise_for_status()
        data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        return {
            "execution_id": data.get("executionId", data.get("id", "")),
            "status": data.get("status", "triggered"),
            "data": data,
        }


def set_dependencies(
    trigger_service: N8nTriggerService | None = None,
) -> None:
    """Wire dependencies for n8n integration routes."""
    global _trigger_service
    _trigger_service = trigger_service


def _validate_webhook_signature(
    payload: bytes,
    signature: str | None,
    secret: str,
) -> bool:
    """Validate HMAC-SHA256 webhook signature."""
    if not signature:
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/n8n/webhook", summary="Receive n8n webhook callback")
async def receive_webhook(
    body: N8nWebhookPayload,
    x_n8n_signature: str | None = Header(default=None, alias="X-N8N-Signature"),
) -> dict[str, Any]:
    """Receive event payloads from n8n workflows.

    Validates HMAC signature when N8N_WEBHOOK_SECRET is configured.
    Returns 200 on success, 401 on invalid signature.
    """
    settings = get_settings()
    webhook_secret = settings.n8n_webhook_secret
    if webhook_secret:
        secret_value = webhook_secret.get_secret_value()
        if secret_value:
            # Re-read raw body for signature validation
            import json
            raw_body = json.dumps(body.model_dump(exclude_none=True), sort_keys=True).encode()
            if not _validate_webhook_signature(raw_body, x_n8n_signature, secret_value):
                raise HTTPException(status_code=401, detail="Invalid webhook signature")

    logger.info("n8n webhook received: event_type=%s, workflow_id=%s", body.event_type, body.workflow_id)

    # Route payload to appropriate handler
    # For now, acknowledge receipt — extensible via event bus
    return {"status": "received", "event_type": body.event_type, "workflow_id": body.workflow_id}


@router.post("/n8n/trigger/{workflow_id}", summary="Trigger n8n workflow")
async def trigger_workflow(
    workflow_id: str,
    request: N8nTriggerRequest,
) -> dict[str, Any]:
    """Trigger an n8n workflow by ID.

    Requires N8N_BASE_URL and N8N_API_KEY to be configured.
    """
    if not _trigger_service:
        raise HTTPException(status_code=503, detail="n8n trigger service not configured")

    try:
        result = await _trigger_service.trigger_workflow(workflow_id, request.payload)
        return {"success": True, "data": result}
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="n8n unreachable — connection refused")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="n8n request timed out")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"n8n error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger workflow: {e}")
