from fastapi import APIRouter

from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.kernel import router as kernel_router
from app.api.v1.routes.memory import router as memory_router

router = APIRouter()

router.include_router(health_router, tags=["health"])
router.include_router(kernel_router)
router.include_router(memory_router, tags=["memory"])
