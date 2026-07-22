from fastapi import APIRouter

from app.api.v1.routes.agents import router as agents_router
from app.api.v1.routes.goals import router as goals_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.kernel import router as kernel_router
from app.api.v1.routes.learning import router as learning_router
from app.api.v1.routes.memory import router as memory_router
from app.api.v1.routes.models import router as models_router
from app.api.v1.routes.profile import router as profile_router
from app.api.v1.routes.rag import router as rag_router
from app.api.v1.routes.tasks import router as tasks_router
from app.api.v1.routes.knowledge_graph import router as knowledge_graph_router
from app.api.v1.routes.tools import router as tools_router
from app.api.v1.routes.vector_memory import router as vector_memory_router
from app.api.v1.routes.workflows import router as workflows_router

router = APIRouter()

router.include_router(agents_router)
router.include_router(goals_router)
router.include_router(health_router, tags=["health"])
router.include_router(kernel_router)
router.include_router(learning_router)
router.include_router(memory_router, tags=["memory"])
router.include_router(models_router)
router.include_router(profile_router)
router.include_router(rag_router)
router.include_router(tasks_router)
router.include_router(knowledge_graph_router)
router.include_router(tools_router)
router.include_router(vector_memory_router)
router.include_router(workflows_router)
