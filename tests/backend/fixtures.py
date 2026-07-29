from __future__ import annotations

import pytest
import pytest_asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from collections.abc import AsyncGenerator, Generator

from app.cognitive.engine import CognitiveEngine
from app.memory.base import MemoryProvider
from app.learning.base import LearningStore
from app.knowledge_graph.base import EntityExtractor
from app.reasoning.base import ReasoningStrategy


@pytest.fixture
def cognitive_engine() -> Generator[CognitiveEngine, None, None]:
    engine = MagicMock(spec=CognitiveEngine)
    engine.process = AsyncMock(return_value={"result": "processed"})
    engine.analyze = AsyncMock(return_value={"analysis": "complete"})
    engine.reset = AsyncMock(return_value=None)
    yield engine


@pytest.fixture
def memory_provider() -> MagicMock:
    provider = MagicMock(spec=MemoryProvider)
    provider.store = AsyncMock(return_value=None)
    provider.retrieve = AsyncMock(return_value=None)
    provider.search = AsyncMock(return_value=[])
    provider.delete = AsyncMock(return_value=None)
    return provider


@pytest.fixture
def learning_store() -> MagicMock:
    store = MagicMock(spec=LearningStore)
    store.record = AsyncMock(return_value=None)
    store.get_patterns = AsyncMock(return_value=[])
    store.update = AsyncMock(return_value=None)
    store.clear = AsyncMock(return_value=None)
    return store


@pytest.fixture
def knowledge_store() -> MagicMock:
    store = MagicMock(spec=EntityExtractor)
    store.extract = AsyncMock(return_value=[])
    store.add_entity = AsyncMock(return_value=None)
    store.get_entity = AsyncMock(return_value=None)
    store.get_relations = AsyncMock(return_value=[])
    return store


@pytest.fixture
def reasoning_strategy() -> MagicMock:
    strategy = MagicMock(spec=ReasoningStrategy)
    strategy.reason = AsyncMock(return_value={"conclusion": "test"})
    strategy.evaluate = AsyncMock(return_value={"score": 1.0})
    strategy.get_steps = AsyncMock(return_value=[])
    return strategy


@pytest.fixture
def goal_store() -> MagicMock:
    store = MagicMock()
    store.create = AsyncMock(return_value={"id": "goal-1", "name": "test"})
    store.get = AsyncMock(return_value={"id": "goal-1", "name": "test"})
    store.update = AsyncMock(return_value={"id": "goal-1", "name": "updated"})
    store.delete = AsyncMock(return_value=True)
    store.list = AsyncMock(return_value=[])
    return store


@pytest.fixture
def task_store() -> MagicMock:
    store = MagicMock()
    store.create = AsyncMock(return_value={"id": "task-1", "title": "test"})
    store.get = AsyncMock(return_value={"id": "task-1", "title": "test"})
    store.update = AsyncMock(return_value={"id": "task-1", "title": "updated"})
    store.delete = AsyncMock(return_value=True)
    store.list = AsyncMock(return_value=[])
    return store


@pytest.fixture
def planner() -> MagicMock:
    planner = MagicMock()
    planner.create_plan = AsyncMock(return_value={"id": "plan-1", "steps": []})
    planner.execute_plan = AsyncMock(return_value={"status": "completed"})
    return planner


@pytest.fixture
def executor() -> MagicMock:
    executor = MagicMock()
    executor.execute = AsyncMock(return_value={"status": "running"})
    executor.cancel = AsyncMock(return_value=True)
    executor.get_status = AsyncMock(return_value={"status": "idle"})
    return executor


@pytest.fixture
def agent_registry() -> MagicMock:
    registry = MagicMock()
    registry.register = MagicMock(return_value=None)
    registry.get = MagicMock(return_value={"id": "agent-1", "name": "test"})
    registry.list = MagicMock(return_value=[])
    registry.unregister = MagicMock(return_value=True)
    return registry


@pytest.fixture
def workflow_engine() -> MagicMock:
    engine = MagicMock()
    engine.create_workflow = AsyncMock(return_value={"id": "wf-1", "name": "test"})
    engine.execute_workflow = AsyncMock(return_value={"status": "running"})
    engine.get_status = AsyncMock(return_value={"status": "completed"})
    return engine


@pytest.fixture
def scheduler() -> MagicMock:
    scheduler = MagicMock()
    scheduler.schedule = AsyncMock(return_value={"id": "job-1"})
    scheduler.cancel = AsyncMock(return_value=True)
    scheduler.get_jobs = AsyncMock(return_value=[])
    scheduler.list_jobs = AsyncMock(return_value=[])
    return scheduler


@pytest.fixture
def tool_registry() -> MagicMock:
    registry = MagicMock()
    registry.register = MagicMock(return_value=None)
    registry.execute = AsyncMock(return_value={"result": "done"})
    registry.list_tools = MagicMock(return_value=[])
    registry.get_tool = MagicMock(return_value={"name": "test-tool"})
    return registry


@pytest.fixture
def model_gateway() -> MagicMock:
    gateway = MagicMock()
    gateway.generate = AsyncMock(return_value={"text": "generated"})
    gateway.embed = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    gateway.chat = AsyncMock(return_value={"message": "response"})
    return gateway


@pytest.fixture
def vector_memory() -> MagicMock:
    memory = MagicMock()
    memory.add = AsyncMock(return_value="vec-1")
    memory.search = AsyncMock(return_value=[])
    memory.delete = AsyncMock(return_value=True)
    memory.count = AsyncMock(return_value=0)
    return memory


@pytest.fixture
def rag_engine() -> MagicMock:
    engine = MagicMock()
    engine.query = AsyncMock(return_value={"results": [], "answer": ""})
    engine.index_document = AsyncMock(return_value={"indexed": True})
    engine.get_stats = AsyncMock(return_value={"count": 0})
    return engine


@pytest.fixture
def event_bus() -> MagicMock:
    bus = MagicMock()
    bus.publish = AsyncMock(return_value=None)
    bus.subscribe = AsyncMock(return_value="sub-1")
    bus.unsubscribe = AsyncMock(return_value=True)
    bus.get_events = AsyncMock(return_value=[])
    return bus


@pytest.fixture
def plugin_manager() -> MagicMock:
    manager = MagicMock()
    manager.load = AsyncMock(return_value={"loaded": True})
    manager.unload = AsyncMock(return_value=True)
    manager.list_plugins = MagicMock(return_value=[])
    manager.get_plugin = MagicMock(return_value={"name": "test-plugin"})
    manager.health_check = AsyncMock(return_value={"status": "healthy"})
    return manager


@pytest.fixture
def security_engine() -> MagicMock:
    engine = MagicMock()
    engine.authenticate = AsyncMock(return_value={"user_id": "user-1", "token": "tok"})
    engine.authorize = AsyncMock(return_value=True)
    engine.create_token = AsyncMock(return_value="test-token")
    engine.validate_token = AsyncMock(return_value={"valid": True})
    return engine


@pytest.fixture
def observability() -> MagicMock:
    obs = MagicMock()
    obs.metrics = MagicMock()
    obs.metrics.record = MagicMock(return_value=None)
    obs.metrics.increment = MagicMock(return_value=None)
    obs.metrics.gauge = MagicMock(return_value=None)
    obs.tracing = MagicMock()
    obs.tracing.start_span = MagicMock(return_value=None)
    obs.tracing.end_span = MagicMock(return_value=None)
    obs.logging = MagicMock()
    obs.logging.info = MagicMock(return_value=None)
    obs.logging.error = MagicMock(return_value=None)
    obs.logging.warning = MagicMock(return_value=None)
    obs.health = AsyncMock(return_value={"status": "healthy"})
    return obs


@pytest.fixture
def deployment_manager() -> MagicMock:
    manager = MagicMock()
    manager.deploy = AsyncMock(return_value={"deployment_id": "dep-1"})
    manager.rollback = AsyncMock(return_value={"rolled_back": True})
    manager.health_check = AsyncMock(return_value={"status": "healthy"})
    manager.get_status = AsyncMock(return_value={"status": "active"})
    return manager


@pytest.fixture
def scaling_engine() -> MagicMock:
    engine = MagicMock()
    engine.scale_up = AsyncMock(return_value={"scaled": True})
    engine.scale_down = AsyncMock(return_value={"scaled": True})
    engine.get_metrics = AsyncMock(return_value={"cpu": 0.5, "memory": 0.6})
    engine.get_health = AsyncMock(return_value={"status": "healthy"})
    return engine


@pytest.fixture
def db_session() -> MagicMock:
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock())
    session.commit = AsyncMock(return_value=None)
    session.rollback = AsyncMock(return_value=None)
    session.close = AsyncMock(return_value=None)
    return session


@pytest.fixture
def full_engine_stack(
    cognitive_engine: MagicMock,
    memory_provider: MagicMock,
    event_bus: MagicMock,
    knowledge_store: MagicMock,
    reasoning_strategy: MagicMock,
    model_gateway: MagicMock,
    vector_memory: MagicMock,
    rag_engine: MagicMock,
    db_session: MagicMock,
) -> dict[str, Any]:
    return {
        "cognitive_engine": cognitive_engine,
        "memory": memory_provider,
        "event_bus": event_bus,
        "knowledge_store": knowledge_store,
        "reasoning": reasoning_strategy,
        "model_gateway": model_gateway,
        "vector_memory": vector_memory,
        "rag_engine": rag_engine,
        "db_session": db_session,
    }


@pytest.fixture
def api_test_client() -> MagicMock:
    client = MagicMock()
    client.get = AsyncMock(return_value=MagicMock(status_code=200, json=MagicMock(return_value={})))
    client.post = AsyncMock(return_value=MagicMock(status_code=201, json=MagicMock(return_value={})))
    client.put = AsyncMock(return_value=MagicMock(status_code=200, json=MagicMock(return_value={})))
    client.delete = AsyncMock(return_value=MagicMock(status_code=204, json=MagicMock(return_value={})))
    client.aclose = AsyncMock(return_value=None)
    return client
