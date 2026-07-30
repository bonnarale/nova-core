from contextlib import asynccontextmanager
from typing import AsyncIterator
from uuid import UUID

import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

from app.agents.agent_manager import AgentManager
from app.command_center.approvals import ApprovalsManager
from app.agents.builtins.planner_agent import PlannerAgent
from app.agents.builtins.executor_agent import ExecutorAgent
from app.agents.builtins.coder_agent import CoderAgent
from app.agents.builtins.research_agent import ResearchAgent
from app.agents.builtins.meta_agent import MetaAgent
from app.agents.capability_auditor import CapabilityAuditor
from app.agents.llm_agent import LLMAgent
from app.api.v1.router import router as api_v1_router
from app.cognitive.engine import CognitiveEngine
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.activity_log_repository import ActivityLogRepository
from app.db.postgres import close_database, init_database
from app.events import EventSystemFactory
from app.security.factory import SecurityFactory
from app.kernel import get_kernel, register_agent
from app.learning.evolution_engine import EvolutionEngine
from app.learning.outcome_tracker import InMemoryOutcomeStore
from app.learning.success_tracker import SuccessTracker
from app.memory import ConversationMemory
from app.memory.goals import GoalManager
from app.memory.profile import UserProfileMemory
from app.models.gateway import ModelGateway
from app.orchestrator.task_executor import TaskExecutor
from app.orchestrator.task_manager import TaskManager
from app.scheduler.factory import SchedulerFactory
from app.autonomy.manager import AutonomyManager
from app.autonomy.autonomous_handler import AutonomousReviewHandler
from app.services.chroma import ChromaService
from app.services.ollama import OllamaService
from app.services.redis import close_redis, init_redis

settings = get_settings()
configure_logging(settings.log_level)

SYSTEM_PROMPT = (
    "You are NOVA CORE, an AI operating system. "
    "Answer concisely and accurately using the conversation history."
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Infraestructura
    app.state.database = await init_database(settings)
    app.state.redis = await init_redis(settings)
    app.state.chroma = ChromaService(settings)
    app.state.ollama = OllamaService(settings)

    # Security Engine
    security_engine = SecurityFactory.create_engine()
    await security_engine.start()
    app.state.security_engine = security_engine

    # Event System
    event_factory = EventSystemFactory(default_source="nova-core")
    event_bus = event_factory.create_bus()
    await event_bus.start()
    app.state.event_bus = event_bus

    # Agent Manager
    agent_manager = AgentManager()
    app.state.agent_manager = agent_manager

    # Task Manager
    task_manager = TaskManager(event_bus=event_bus)
    app.state.task_manager = task_manager

    # Task Executor
    task_executor = TaskExecutor(
        event_bus=event_bus,
        task_manager=task_manager,
        agent_manager=agent_manager,
    )
    await task_executor.start()
    app.state.task_executor = task_executor

    # Memoria conversacional
    memory = ConversationMemory(app.state.database)
    app.state.memory = memory

    # SuccessTracker (for CapabilityAuditor)
    outcome_store = InMemoryOutcomeStore()
    success_tracker = SuccessTracker(store=outcome_store)

    # CapabilityAuditor
    auditor = CapabilityAuditor(
        agent_manager=agent_manager,
        success_tracker=success_tracker,
    )

    # MetaAgent
    meta_agent = MetaAgent(auditor=auditor)

    # EvolutionEngine
    evolution_engine = EvolutionEngine(
        bus=event_bus,
        meta_agent=meta_agent,
    )
    app.state.evolution_engine = evolution_engine

    # CognitiveEngine
    goal_manager = GoalManager(database=app.state.database)
    app.state.goal_manager = goal_manager
    profile_memory = UserProfileMemory(database=app.state.database)
    app.state.profile_memory = profile_memory
    from app.memory.semantic import SemanticMemory
    semantic_memory = SemanticMemory(app.state.chroma.client, app.state.ollama)
    app.state.semantic_memory = semantic_memory
    from app.workflows.engine import WorkflowEngine
    workflow_engine = WorkflowEngine()
    app.state.workflow_engine = workflow_engine
    from app.tools.manager import ToolManager
    from app.tools.factory import ToolFactory
    from app.tools.runtime import ToolRuntime
    tool_manager = ToolManager()
    tool_factory = ToolFactory(manager=tool_manager)
    tool_factory.register_all_builtins()
    tool_runtime = ToolRuntime(manager=tool_manager)
    app.state.tool_manager = tool_manager
    app.state.tool_factory = tool_factory
    app.state.tool_runtime = tool_runtime
    
    # API-level metrics and tracing (global, accumulates across all requests)
    from app.api.metrics import APIMetricsCollector
    from app.api.tracing import APITracer

    api_metrics = APIMetricsCollector()
    api_tracer = APITracer()
    app.state.api_metrics = api_metrics
    app.state.api_tracer = api_tracer
    
    # ProjectsManager with optional DB repository
    from app.command_center.projects import ProjectsManager
    projects_manager = ProjectsManager()
    app.state.projects_manager = projects_manager

    # ApprovalsManager (shared between CognitiveEngine and API endpoints)
    approvals_manager = ApprovalsManager(projects_mgr=projects_manager)
    app.state.approvals_manager = approvals_manager

    # ProjectGoalBridge — coordinates Goals, Projects, Workflows
    from app.command_center.project_goal_bridge import ProjectGoalBridge
    project_goal_bridge = ProjectGoalBridge(
        projects_mgr=projects_manager,
        goal_manager=goal_manager,
        workflow_engine=workflow_engine,
        approvals_mgr=approvals_manager,
    )
    app.state.project_goal_bridge = project_goal_bridge

    cognitive_engine = CognitiveEngine(
        goal_manager=goal_manager,
        task_manager=task_manager,
        agent_manager=agent_manager,
        profile_memory=profile_memory,
        conversation_memory=memory,
        semantic_memory=semantic_memory,
        event_publisher=event_bus,
        evolution_engine=evolution_engine,
        approvals_manager=approvals_manager,
        workflow_engine=workflow_engine,
    )
    app.state.cognitive_engine = cognitive_engine

    # Inject bridge into CognitiveEngine
    cognitive_engine.inject_project_bridge(project_goal_bridge)

    # --- Auto-index semantic memory at startup ---
    try:
        # Index any existing user profiles
        default_user_id = None
        if default_user_id:
            profile = await profile_memory.get_profile(default_user_id)
            if profile:
                await semantic_memory.auto_index(profile=profile)
        import logging as _logging
        _logging.getLogger("nova.startup").info("Semantic memory auto-index complete")
    except Exception as exc:
        import logging as _logging
        _logging.getLogger("nova.startup").warning("Semantic memory auto-index failed: %s", exc)

    # Modelo y Kernel
    gateway = ModelGateway(settings)

    register_agent(
        LLMAgent(
            agent_id="assistant",
            gateway=gateway,
            system_prompt=SYSTEM_PROMPT,
        )
    )
    # Register LLM-powered builtin agents
    planner = PlannerAgent(gateway=gateway)
    executor = ExecutorAgent(gateway=gateway)
    coder = CoderAgent(gateway=gateway)
    researcher = ResearchAgent(gateway=gateway)

    register_agent(planner)
    register_agent(executor)
    register_agent(coder)
    register_agent(researcher)

    # Also register in AgentManager so /api/v1/agents can list them
    agent_manager.register("planner", planner)
    agent_manager.register("executor", executor)
    agent_manager.register("coder", coder)
    agent_manager.register("researcher", researcher)

    kernel = get_kernel(settings)
    await kernel.start()

    app.state.gateway = gateway
    app.state.kernel = kernel

    # --- Scheduler ---
    scheduler = SchedulerFactory.create_scheduler()
    await scheduler.start()
    app.state.scheduler = scheduler

    # --- Activity Log Repository ---
    activity_repository = ActivityLogRepository(app.state.database.session_factory)
    app.state.activity_repository = activity_repository

    # --- Autonomous Handler + Scheduler Job ---
    app.state.autonomous_loop = None
    if settings.nova_autonomous_enabled and settings.nova_autonomous_user_id:
        autonomy_manager = AutonomyManager()
        await autonomy_manager.start()
        app.state.autonomy_manager = autonomy_manager

        user_id = UUID(settings.nova_autonomous_user_id)
        autonomous_handler = AutonomousReviewHandler(
            goal_repository=GoalManager(database=app.state.database)._repo,
            autonomy_manager=autonomy_manager,
            approvals_manager=approvals_manager,
            activity_repository=activity_repository,
            event_bus=event_bus,
            user_id=user_id,
            max_goals_per_cycle=settings.nova_autonomous_max_goals_per_cycle,
        )

        # Register handler with scheduler executor
        scheduler._executor.register_handler(
            "autonomous_review", autonomous_handler.handle
        )

        # Create and schedule the autonomous review job
        from app.scheduler.schemas import CreateJobRequest, TriggerConfig, JobType, JobPriority, TriggerType
        job_request = CreateJobRequest(
            name="autonomous_review",
            description="Autonomous review of active goals",
            job_type=JobType.INTERVAL,
            trigger=TriggerConfig(
                trigger_type=TriggerType.INTERVAL,
                interval_seconds=settings.nova_autonomous_interval_seconds,
            ),
            priority=JobPriority.NORMAL,
        )
        created_job = await scheduler.schedule_job(job_request)
        logger.info(
            "Autonomous review job registered (job_id=%s, interval=%ds)",
            created_job.job_id,
            settings.nova_autonomous_interval_seconds,
        )

        # Store reference for shutdown
        app.state.autonomous_loop = created_job.job_id

    try:
        yield
    finally:
        # Shutdown autonomous review job
        if hasattr(app.state, "autonomous_loop") and app.state.autonomous_loop is not None:
            job_id = app.state.autonomous_loop
            if isinstance(job_id, str):
                await scheduler.cancel_job(job_id)
                logger.info("Autonomous review job cancelled: %s", job_id)
            else:
                # Legacy asyncio.Task path
                job_id.cancel()
                try:
                    await job_id
                except asyncio.CancelledError:
                    pass

        # Shutdown autonomy manager
        if hasattr(app.state, "autonomy_manager"):
            await app.state.autonomy_manager.shutdown()

        # Shutdown scheduler
        if hasattr(app.state, "scheduler"):
            await app.state.scheduler.stop()

        # Shutdown TaskExecutor
        if hasattr(app.state, "task_executor"):
            await app.state.task_executor.stop()

        # Shutdown EventBus
        if hasattr(app.state, "event_bus"):
            await app.state.event_bus.stop()

        await kernel.stop()
        await gateway.close()

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

app.include_router(api_v1_router, prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.middleware import (
    APIMetricsMiddleware,
    ExceptionHandlingMiddleware,
    RequestIDMiddleware,
    TimingMiddleware,
)

# Middleware order: last added = outermost (runs first on request, last on response).
# TimingMiddleware must be inner relative to APIMetricsMiddleware so that
# request.state.response_time_ms is set before APIMetricsMiddleware reads it.
app.add_middleware(TimingMiddleware)
app.add_middleware(APIMetricsMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(ExceptionHandlingMiddleware)


@app.get("/", summary="Root endpoint")
async def root() -> dict[str, str]:
    """Root endpoint returning service info."""
    return {"name": settings.project_name, "version": "0.1.0", "status": "ok"}


@app.get("/health", summary="Health check")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
