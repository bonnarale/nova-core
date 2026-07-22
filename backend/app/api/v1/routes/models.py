"""Model Gateway API routes."""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/models", tags=["models"])


class ChatRequest(BaseModel):
    """Chat request model."""

    model: str = Field(..., description="Model name/identifier")
    messages: list[dict[str, str]] = Field(..., description="Chat messages")
    provider: Optional[str] = Field(None, description="Provider name")
    agent_id: Optional[str] = Field(None, description="Agent ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    user_id: Optional[str] = Field(None, description="User ID")
    use_cache: bool = Field(True, description="Use response cache")
    temperature: Optional[float] = Field(None, description="Temperature")
    max_tokens: Optional[int] = Field(None, description="Max tokens")
    stream: bool = Field(False, description="Stream response")


class ChatResponse(BaseModel):
    """Chat response model."""

    response: dict[str, Any]
    provider: str
    model: str
    latency_ms: float
    cache_hit: bool
    tokens_input: int
    tokens_output: int


class HealthResponse(BaseModel):
    """Health check response model."""

    providers: dict[str, dict[str, Any]]


class MetricsResponse(BaseModel):
    """Metrics response model."""

    summary: dict[str, Any]
    providers: dict[str, dict[str, Any]]


class ModelsResponse(BaseModel):
    """Models list response model."""

    models: list[str]
    provider: Optional[str] = None


class ProviderInfo(BaseModel):
    """Provider information model."""

    provider_id: str
    state: str
    is_healthy: bool
    is_available: bool
    capabilities: dict[str, Any]


class ProvidersResponse(BaseModel):
    """Providers list response model."""

    providers: list[ProviderInfo]
    total: int
    active: int


class CacheStatsResponse(BaseModel):
    """Cache statistics response model."""

    stats: dict[str, Any]


class TracesResponse(BaseModel):
    """Traces response model."""

    traces: list[dict[str, Any]]
    total: int


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    from app.models.gateway import ModelGateway
    from app.main import app_state
    gateway: ModelGateway = app_state["model_gateway"]
    try:
        kwargs: dict[str, Any] = {}
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        if request.max_tokens is not None:
            kwargs["max_tokens"] = request.max_tokens
        result = await gateway.chat(
            model=request.model,
            messages=request.messages,
            provider=request.provider,
            agent_id=request.agent_id,
            session_id=request.session_id,
            user_id=request.user_id,
            use_cache=request.use_cache,
            **kwargs,
        )
        return ChatResponse(
            response=result,
            provider=request.provider or "default",
            model=request.model,
            latency_ms=0.0,
            cache_hit=False,
            tokens_input=result.get("usage", {}).get("prompt_tokens", 0),
            tokens_output=result.get("usage", {}).get("completion_tokens", 0),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    from app.models.gateway import ModelGateway
    from app.main import app_state
    gateway: ModelGateway = app_state["model_gateway"]
    try:
        health = await gateway.health()
        return HealthResponse(providers=health)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics() -> MetricsResponse:
    from app.models.gateway import ModelGateway
    from app.main import app_state
    gateway: ModelGateway = app_state["model_gateway"]
    try:
        metrics = gateway.get_metrics_summary()
        return MetricsResponse(
            summary=metrics.get("metrics", {}),
            providers={},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=ModelsResponse)
async def list_models(provider: Optional[str] = None) -> ModelsResponse:
    from app.models.gateway import ModelGateway
    from app.main import app_state
    gateway: ModelGateway = app_state["model_gateway"]
    try:
        models = await gateway.list_models(provider)
        return ModelsResponse(models=models, provider=provider)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers", response_model=ProvidersResponse)
async def list_providers() -> ProvidersResponse:
    from app.models.gateway import ModelGateway
    from app.main import app_state
    gateway: ModelGateway = app_state["model_gateway"]
    try:
        providers = []
        for pid in gateway.registry.list_providers():
            lifecycle = gateway.registry.get_lifecycle(pid)
            caps = gateway.registry.get_capabilities(pid)
            providers.append(ProviderInfo(
                provider_id=pid,
                state=lifecycle.state.value if lifecycle else "unknown",
                is_healthy=lifecycle.is_healthy if lifecycle else False,
                is_available=lifecycle.is_available if lifecycle else False,
                capabilities={
                    "supported": [c.value for c in caps.supported] if caps else [],
                    "max_concurrent_requests": caps.max_concurrent_requests if caps else 0,
                },
            ))
        return ProvidersResponse(
            providers=providers,
            total=len(providers),
            active=sum(1 for p in providers if p.is_available),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats() -> CacheStatsResponse:
    from app.models.gateway import ModelGateway
    from app.main import app_state
    gateway: ModelGateway = app_state["model_gateway"]
    try:
        stats = gateway.cache.get_stats()
        return CacheStatsResponse(stats=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache")
async def clear_cache() -> dict[str, Any]:
    from app.models.gateway import ModelGateway
    from app.main import app_state
    gateway: ModelGateway = app_state["model_gateway"]
    try:
        count = gateway.cache.clear()
        return {"cleared": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traces", response_model=TracesResponse)
async def get_traces(limit: int = 100) -> TracesResponse:
    from app.models.gateway import ModelGateway
    from app.main import app_state
    gateway: ModelGateway = app_state["model_gateway"]
    try:
        traces = gateway.tracer.get_traces(limit)
        return TracesResponse(
            traces=[t.to_dict() for t in traces],
            total=gateway.tracer.get_trace_count(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
