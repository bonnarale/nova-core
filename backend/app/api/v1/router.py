from fastapi import APIRouter

from app.api.v1.routes.agents import router as agents_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.autonomy import router as autonomy_router
from app.api.v1.routes.autonomy_system import router as autonomy_system_router
from app.api.v1.routes.command_center import router as command_center_router
from app.api.v1.routes.database import router as database_router
from app.api.v1.routes.deployment import router as deployment_router
from app.api.v1.routes.enterprise import router as enterprise_router
from app.api.v1.routes.events import router as events_router
from app.api.v1.routes.future import router as future_router
from app.api.v1.routes.goals import router as goals_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.integration import router as integration_router
from app.api.v1.routes.kernel import router as kernel_router
from app.api.v1.routes.memory import router as memory_router
from app.api.v1.routes.n8n_integration import router as n8n_integration_router
from app.api.v1.routes.nova_web import router as nova_web_router
from app.api.v1.routes.observability import router as observability_router
from app.api.v1.routes.performance import router as performance_router
from app.api.v1.routes.plugins import router as plugins_router
from app.api.v1.routes.projects import router as projects_router
from app.api.v1.routes.resilience import router as resilience_router
from app.api.v1.routes.scaling import router as scaling_router
from app.api.v1.routes.scheduler import router as scheduler_router
from app.api.v1.routes.security import router as security_router
from app.api.v1.routes.tasks import router as tasks_router
from app.api.v1.routes.tools import router as tools_router
from app.api.v1.routes.user_profile import router as user_profile_router
from app.api.v1.routes.workflows import router as workflows_router
from app.api.v1.routes.activity import router as activity_router

router = APIRouter()

router.include_router(agents_router)
router.include_router(auth_router)
router.include_router(autonomy_router)
router.include_router(autonomy_system_router)
router.include_router(command_center_router)
router.include_router(database_router)
router.include_router(deployment_router)
router.include_router(enterprise_router)
router.include_router(events_router)
router.include_router(future_router)
router.include_router(goals_router)
router.include_router(health_router, tags=["health"])
router.include_router(integration_router)
router.include_router(kernel_router)
router.include_router(memory_router, tags=["memory"])
router.include_router(n8n_integration_router)
router.include_router(nova_web_router)
router.include_router(observability_router)
router.include_router(performance_router)
router.include_router(plugins_router)
router.include_router(projects_router)
router.include_router(resilience_router)
router.include_router(scaling_router)
router.include_router(scheduler_router)
router.include_router(security_router)
router.include_router(tasks_router)
router.include_router(tools_router)
router.include_router(user_profile_router)
router.include_router(workflows_router)
router.include_router(activity_router)
