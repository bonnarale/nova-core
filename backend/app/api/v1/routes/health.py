from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from app.db.postgres import database_ready
from app.services.redis import redis_ready

router = APIRouter()


@router.get("/health", summary="Service health")
async def health(request: Request) -> JSONResponse:
    checks: dict[str, bool] = {
        "postgres": await database_ready(request.app.state.database),
        "redis": await redis_ready(request.app.state.redis),
        "chroma": request.app.state.chroma.ready(),
        "ollama": await request.app.state.ollama.ready(),
    }
    healthy = all(checks.values())
    payload: dict[str, Any] = {"status": "ok" if healthy else "degraded", "checks": checks}
    return JSONResponse(
        status_code=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=payload,
    )

