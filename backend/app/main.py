from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.agent_manager import AgentManager
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
from app.db.postgres import close_database, init_database
from app.events import EventSystemFactory
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
    cognitive_engine = CognitiveEngine(
        goal_manager=goal_manager,
        task_manager=task_manager,
        agent_manager=agent_manager,
        profile_memory=profile_memory,
        conversation_memory=memory,
        event_publisher=event_bus,
        evolution_engine=evolution_engine,
    )
    app.state.cognitive_engine = cognitive_engine

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
    register_agent(PlannerAgent(gateway=gateway))
    register_agent(ExecutorAgent(gateway=gateway))
    register_agent(CoderAgent(gateway=gateway))
    register_agent(ResearchAgent(gateway=gateway))

    kernel = get_kernel(settings)
    await kernel.start()

    app.state.gateway = gateway
    app.state.kernel = kernel

    try:
        yield
    finally:
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


@app.get("/", summary="Root endpoint")
async def root() -> dict[str, str]:
    """Root endpoint returning service info."""
    return {"name": settings.project_name, "version": "0.1.0", "status": "ok"}


@app.get("/health", summary="Health check")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
