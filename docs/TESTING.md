# Testing

## Overview

NOVA CORE uses pytest with async-first testing. The test infrastructure includes fixtures, factories, builders, mocks, custom assertions, and specialized testing modules.

## Test Commands

```bash
# Run all tests
cd backend && python -m pytest ../tests/backend/ -v

# Run specific test file
cd backend && python -m pytest ../tests/backend/test_event_system.py -v

# Run with coverage
cd backend && python -m pytest ../tests/backend/ --cov=app --cov-report=html

# Run specific marker
cd backend && python -m pytest ../tests/backend/ -m "not slow"
```

## Test Structure

```
tests/backend/
├── conftest.py          # Core fixtures and configuration
├── fixtures.py          # Subsystem-specific fixtures
├── factories.py         # Object factories (13 factories)
├── builders.py          # Fluent builders (9 builders)
├── mocks.py             # Reusable mock classes (9 mocks)
├── helpers.py           # Async utilities and helpers
├── assertions.py        # Custom assertions (15 assertions)
├── performance.py       # Benchmark suites
├── stress.py            # Stress testing
├── load.py              # Load testing
├── integration.py       # Integration test helpers
├── regression.py        # Regression detection
├── property.py          # Property-based testing
├── lifecycle.py         # Lifecycle testing
├── metrics.py           # Metrics testing
├── reporting.py         # Test reporting
├── test_*.py            # 64 test modules
└── ...
```

## Available Fixtures

### Core
- `event_loop` — Session-scoped asyncio event loop
- `now` — Current UTC datetime
- `sample_id`, `sample_ids` — UUID strings
- `sample_text` — Sample text content
- `sample_embedding`, `sample_embeddings` — Embedding vectors

### Mocks
- `mock_llm_provider` — Mock LLM provider
- `mock_embedding_provider` — Mock embedding provider
- `mock_vector_store` — Mock vector store
- `mock_database` — Mock database session
- `mock_event_bus` — Mock event bus
- `mock_external_api` — Mock external API
- `mock_scheduler` — Mock scheduler
- `mock_tool`, `mock_plugin` — Mock tool/plugin
- `mock_app_state` — Full app state mock

### Subsystems
- `cognitive_engine`, `memory_provider`, `learning_store`
- `knowledge_store`, `reasoning_strategy`, `goal_store`
- `task_store`, `planner`, `executor`, `agent_registry`
- `workflow_engine`, `scheduler`, `tool_registry`
- `model_gateway`, `vector_memory`, `rag_engine`
- `event_bus`, `plugin_manager`, `security_engine`
- `observability`, `deployment_manager`, `scaling_engine`
- `db_session`, `full_engine_stack`, `api_test_client`

## Factories

13 factory classes for creating test objects:

- `EventBusFactory`, `EventFactory`, `SecurityFactory`
- `WorkflowFactory`, `PluginFactory`, `SchedulerFactory`
- `KnowledgeGraphFactory`, `LongTermMemoryFactory`
- `LearningFactory`, `ToolFactory`, `ScalingFactory`
- `DeploymentFactory`, `RAGFactory`

## Custom Markers

| Marker | Description |
|--------|-------------|
| `@pytest.mark.unit` | Pure unit tests |
| `@pytest.mark.integration` | Integration tests |
| `@pytest.mark.e2e` | End-to-end tests |
| `@pytest.mark.regression` | Regression tests |
| `@pytest.mark.performance` | Performance benchmarks |
| `@pytest.mark.load` | Load tests |
| `@pytest.mark.stress` | Stress tests |
| `@pytest.mark.concurrency` | Concurrency tests |
| `@pytest.mark.slow` | Slow tests (>1s) |
| `@pytest.mark.security` | Security tests |

## Test Counts

| Category | Count |
|----------|-------|
| Test files | 64 |
| Test support files | 17 |
| Total tests | ~3800+ |
| Passing | ~3595+ |
| Pre-existing failures | 2 (RAG), 33 (KG) |
