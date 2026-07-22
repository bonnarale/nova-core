from contextlib import asynccontextmanager
from typing import Any, AsyncIterator
from uuid import UUID

from fastapi import FastAPI

from app.agents import (
    AgentFactory,
    AgentManager,
    AgentRuntime,
    CoderAgent,
    CoordinatorAgent,
    ExecutorAgent,
    MemoryAgent,
    PlannerAgent,
    ResearchAgent,
    ReviewerAgent,
)
from app.agents.llm_agent import LLMAgent
from app.api.v1.router import router as api_v1_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.postgres import close_database, init_database
from app.executive import ExecutivePlanner
from app.kernel import get_kernel, register_agent
from app.cognitive.engine import CognitiveEngine
from app.db.long_term_memory_repository import LongTermMemoryRepository
from app.long_term_memory import LongTermMemoryManager
from app.memory import ConversationMemory, GoalManager, SemanticMemory, SemanticMemoryConfig, UserProfileMemory
from app.orchestrator import TaskManager
from app.planner import Planner
from app.reasoning import ReasoningEngine
from app.knowledge_graph import KnowledgeGraphEngine
from app.workflows import WorkflowEngine
from app.tools import default_tool_registry
from app.tools.manager import ToolManager
from app.tools.runtime import ToolRuntime
from app.tools.factory import ToolFactory
from app.learning.factory import LearningEngineFactory
from app.models.gateway import ModelGateway
from app.models.factory import ModelGatewayFactory
from app.rag import RAGEngine, RAGFactory, InMemoryEmbeddingProvider, InMemoryRepository
from app.services.chroma import ChromaService
from app.services.ollama import OllamaService
from app.services.redis import close_redis, init_redis
from app.vector_memory import (
    VectorMemoryEngine as VectorMemoryEngine_cls,
    VectorMemoryFactory,
)

settings = get_settings()
configure_logging(settings.log_level)

app_state: dict[str, Any] = {}

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

    # Memoria conversacional
    memory = ConversationMemory(app.state.database)
    app.state.memory = memory

    # Perfil de usuario
    profile_memory = UserProfileMemory(app.state.database)
    app.state.profile_memory = profile_memory

    # Goal manager
    goal_manager = GoalManager(app.state.database)
    app.state.goal_manager = goal_manager

    # Multi-Agent Runtime
    agent_manager = AgentManager(app.state.database)
    for _agent in [
        PlannerAgent(),
        ResearchAgent(),
        CoderAgent(),
        ReviewerAgent(),
        MemoryAgent(),
        ExecutorAgent(),
    ]:
        agent_manager.register_runtime_agent(_agent)
    app.state.agent_manager = agent_manager

    # Chapter 14 — Multi-Agent Runtime
    agent_runtime = AgentRuntime(max_concurrency=10, default_timeout=300.0)
    agent_factory = AgentFactory(runtime=agent_runtime)
    agent_factory.register_all_builtins()
    coordinator_agent = CoordinatorAgent()
    agent_runtime.register(coordinator_agent)
    app.state.agent_runtime = agent_runtime
    app.state.agent_factory = agent_factory

    # Chapter 15 — Tool System
    tool_manager = ToolManager()
    tool_factory = ToolFactory(manager=tool_manager)
    tool_factory.register_all_builtins()
    tool_runtime = ToolRuntime(manager=tool_manager, default_timeout=30.0)
    app.state.tool_manager = tool_manager
    app.state.tool_factory = tool_factory
    app.state.tool_runtime = tool_runtime

    # Task orchestrator (wired with agent_manager for dispatch)
    task_manager = TaskManager(app.state.database, agent_manager=agent_manager)
    app.state.task_manager = task_manager

    # Executive Planner
    executive_planner = ExecutivePlanner(
        goal_manager=goal_manager,
        task_manager=task_manager,
        agent_manager=agent_manager,
        profile_memory=profile_memory,
        conversation_memory=memory,
        event_bus=task_manager.event_bus,
    )
    app.state.executive_planner = executive_planner

    # Memoria semántica
    semantic_memory = SemanticMemory(
        app.state.chroma.client,
        app.state.ollama,
        top_k=settings.semantic_memory_top_k,
        config=SemanticMemoryConfig(
            top_k=settings.semantic_memory_top_k,
            relevance_threshold=settings.semantic_memory_relevance_threshold,
            auto_index=settings.semantic_memory_auto_index,
        ),
    )
    app.state.semantic_memory = semantic_memory

    # Long-Term Memory
    ltm_repo = LongTermMemoryRepository(app.state.database.session_factory)

    class LTMStoreAdapter:
        """Adapts LongTermMemoryRepository to the MemoryStore ABC."""

        def __init__(self, repo):
            self._repo = repo
            self._session_factory = repo._session_factory

        async def create(self, memory):
            from app.long_term_memory.models import MemoryStatus

            entry = self._to_orm(memory)
            created = await self._repo.create(entry)
            return self._from_orm(created)

        async def get(self, memory_id):
            from uuid import UUID
            entry = await self._repo.get(UUID(memory_id))
            return self._from_orm(entry) if entry else None

        async def update(self, memory):
            from app.db.models import LongTermMemoryEntry

            entry = self._to_orm(memory)
            existing = await self._repo.update(entry)
            return self._from_orm(existing) if existing else None

        async def delete(self, memory_id):
            from uuid import UUID
            return await self._repo.delete(UUID(memory_id))

        async def list_by_user(self, user_id, memory_type=None, status=None, limit=50, offset=0):
            from uuid import UUID
            entries = await self._repo.list_by_user(UUID(user_id), memory_type, status, limit, offset)
            return [self._from_orm(e) for e in entries]

        async def list_by_type(self, memory_type, status=None, limit=50):
            entries = await self._repo.list_by_type(memory_type, status, limit)
            return [self._from_orm(e) for e in entries]

        async def search_by_tags(self, tags, memory_type=None, limit=50):
            entries = await self._repo.search_by_tags(tags, memory_type, limit)
            return [self._from_orm(e) for e in entries]

        async def search_by_entity(self, entity, limit=50):
            entries = await self._repo.search_by_entity(entity, limit)
            return [self._from_orm(e) for e in entries]

        async def get_related(self, memory_id, limit=20):
            from uuid import UUID
            entries = await self._repo.get_related(UUID(memory_id), limit)
            return [self._from_orm(e) for e in entries]

        async def list_aging(self, age_days=30, limit=100):
            entries = await self._repo.list_aging(age_days, limit)
            return [self._from_orm(e) for e in entries]

        async def list_archivable(self, min_age_days=90, importance_below=30, limit=100):
            entries = await self._repo.list_archivable(min_age_days, importance_below, limit)
            return [self._from_orm(e) for e in entries]

        async def count_by_status(self):
            return await self._repo.count_by_status()

        @staticmethod
        def _to_orm(memory):
            from app.db.models import LongTermMemoryEntry

            return LongTermMemoryEntry(
                id=UUID(memory.id) if isinstance(memory.id, str) else memory.id,
                memory_type=memory.memory_type,
                content=memory.content,
                summary=memory.summary,
                tags=memory.tags or [],
                categories=memory.categories or [],
                entities=memory.entities or [],
                importance_score=int(memory.importance_score or 0),
                status=memory.status,
                linked_memory_ids=memory.linked_memory_ids or [],
                source=memory.source,
                source_id=memory.source_id,
                user_id=UUID(memory.user_id) if memory.user_id else None,
                project_id=memory.project_id,
                agent_id=memory.agent_id,
                access_count=memory.access_count,
                metadata_=memory.metadata or {},
            )

        @staticmethod
        def _from_orm(entry):
            from app.long_term_memory.models import LongTermMemory

            return LongTermMemory(
                id=str(entry.id),
                memory_type=entry.memory_type,
                content=entry.content,
                summary=entry.summary,
                tags=list(entry.tags or []),
                categories=list(entry.categories or []),
                entities=list(entry.entities or []),
                importance_score=float(entry.importance_score or 0),
                status=entry.status,
                linked_memory_ids=list(entry.linked_memory_ids or []),
                source=entry.source,
                source_id=entry.source_id,
                user_id=str(entry.user_id) if entry.user_id else None,
                project_id=entry.project_id,
                agent_id=entry.agent_id,
                access_count=entry.access_count,
                metadata=dict(entry.metadata_ or {}),
                created_at=entry.created_at.isoformat() if entry.created_at else "",
                accessed_at=entry.accessed_at.isoformat() if entry.accessed_at else "",
                updated_at=entry.updated_at.isoformat() if entry.updated_at else "",
            )

    ltm_store = LTMStoreAdapter(ltm_repo)
    long_term_memory = LongTermMemoryManager(store=ltm_store)
    app.state.long_term_memory = long_term_memory

    # Autonomous Planner
    planner = Planner(
        agent_manager=agent_manager,
    )
    app.state.planner = planner

    # Reasoning Engine
    reasoning_engine = ReasoningEngine()
    app.state.reasoning_engine = reasoning_engine

    # Workflow Engine
    workflow_engine = WorkflowEngine()
    app.state.workflow_engine = workflow_engine

    # Knowledge Graph Engine
    knowledge_graph_engine = KnowledgeGraphEngine()
    await knowledge_graph_engine.initialize()
    app.state.knowledge_graph_engine = knowledge_graph_engine

    # Learning Engine
    learning_engine = LearningEngineFactory.create(
        event_bus=task_manager.event_bus,
    )
    app.state.learning_engine = learning_engine

    # Subscribe learning engine to task completion events
    async def _on_task_completed(event_type: str, data: dict) -> None:
        task_id = data.get("task_id")
        if task_id is None:
            return
        try:
            task_dict = await task_manager.get_task(UUID(task_id)) if task_id else None
        except Exception:
            task_dict = None
        await learning_engine.learn_from_execution(
            execution_data={
                "id": task_id or "",
                "status": "COMPLETED",
                "user_id": (task_dict or {}).get("user_id"),
            },
            task_data=task_dict,
        )

    task_manager.event_bus.on("task.completed", _on_task_completed)

    # Chapter 17 — RAG & Retrieval
    rag_embedder = InMemoryEmbeddingProvider(dimension=384)
    rag_repository = InMemoryRepository()
    rag_factory = RAGFactory(embedder=rag_embedder, repository=rag_repository)
    rag_engine = rag_factory.create_engine()
    await rag_engine.initialize()
    rag_engine.set_knowledge_engine(knowledge_graph_engine)
    rag_engine.set_memory_provider(semantic_memory)
    app.state.rag_engine = rag_engine
    app_state["rag_engine"] = rag_engine

    # Chapter 18 — Vector Memory
    from app.vector_memory.embeddings import InMemoryEmbeddingProvider as VMEmbeddingProvider
    from app.vector_memory.repository import InMemoryVectorRepository
    vm_embedder = VMEmbeddingProvider(dimension=384)
    vm_repository = InMemoryVectorRepository()
    vm_factory = VectorMemoryFactory(embedder=vm_embedder, repository=vm_repository)
    vector_memory_engine = vm_factory.create_engine()
    await vector_memory_engine.initialize()
    vector_memory_engine.set_event_bus(task_manager.event_bus)
    vector_memory_engine.set_knowledge_engine(knowledge_graph_engine)
    vector_memory_engine.set_learning_engine(learning_engine)
    vector_memory_engine.set_rag_engine(rag_engine)
    vector_memory_engine.set_model_gateway(model_gateway)
    app.state.vector_memory_engine = vector_memory_engine
    app_state["vector_memory_engine"] = vector_memory_engine

    # Cognitive Engine
    cognitive_engine = CognitiveEngine(
        goal_manager=goal_manager,
        task_manager=task_manager,
        agent_manager=agent_manager,
        profile_memory=profile_memory,
        conversation_memory=memory,
        semantic_memory=semantic_memory,
        planner=planner,
        long_term_memory=long_term_memory,
        reasoning_engine=reasoning_engine,
        workflow_engine=workflow_engine,
        knowledge_graph_engine=knowledge_graph_engine,
        learning_engine=learning_engine,
        vector_memory_engine=vector_memory_engine,
    )
    app.state.cognitive_engine = cognitive_engine

    # Chapter 16 — Model Gateway
    gateway_factory = ModelGatewayFactory(settings)
    gateway_factory.create_ollama_provider()
    model_gateway = gateway_factory.create_gateway()
    await model_gateway.initialize()
    app.state.model_gateway = model_gateway
    app_state["model_gateway"] = model_gateway

    # Legacy Model Gateway (for LLMAgent)
    gateway = ModelGateway(settings)

    register_agent(
        LLMAgent(
            agent_id="assistant",
            gateway=gateway,
            system_prompt=SYSTEM_PROMPT,
        )
    )

    kernel = get_kernel(settings)
    await kernel.start()

    app.state.gateway = gateway
    app.state.kernel = kernel

    try:
        yield
    finally:
        # Shutdown Vector Memory
        if hasattr(app.state, "vector_memory_engine"):
            await app.state.vector_memory_engine.shutdown()

        # Shutdown RAG Engine
        if hasattr(app.state, "rag_engine"):
            await app.state.rag_engine.shutdown()

        # Shutdown Model Gateway
        if hasattr(app.state, "model_gateway"):
            await app.state.model_gateway.shutdown()

        # Shutdown Tool Runtime
        if hasattr(app.state, "tool_runtime"):
            await app.state.tool_runtime.shutdown()

        # Shutdown AgentRuntime
        if hasattr(app.state, "agent_runtime"):
            await app.state.agent_runtime.shutdown()

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

app.include_router(api_v1_router)


@app.get("/", summary="Root endpoint")
async def root() -> dict[str, str]:
    """Root endpoint returning service info."""
    return {"name": settings.project_name, "version": "0.1.0", "status": "ok"}


@app.get("/health", summary="Health check")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
