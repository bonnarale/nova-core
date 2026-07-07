from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.v1.router import router as api_v1_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.postgres import close_database, init_database
from app.services.chroma import ChromaService
from app.services.ollama import OllamaService
from app.services.redis import close_redis, init_redis

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.database = await init_database(settings)
    app.state.redis = await init_redis(settings)
    app.state.chroma = ChromaService(settings)
    app.state.ollama = OllamaService(settings)
    yield
    await close_redis(app.state.redis)
    await close_database(app.state.database)
    await app.state.ollama.close()


app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
    description="NOVA CORE AI operating system API.",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(api_v1_router)


@app.get("/", summary="Root endpoint")
async def root() -> dict[str, str]:
    """Root endpoint returning service info."""
    return {"name": settings.project_name, "version": "0.1.0", "status": "ok"}


@app.get("/health", summary="Health check")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
