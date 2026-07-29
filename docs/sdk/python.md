# NOVA CORE Python SDK

## Installation

```bash
pip install nova-core-sdk
```

## Quick Start

```python
from nova_core_sdk import NovaClient, Configuration

config = Configuration(
    base_url="http://localhost:8000",
    api_key="your-api-key",
)
client = NovaClient(config)

# Health check
health = await client.health()

# Chat with a model
response = await client.models.chat(
    model="llama3.2",
    messages=[{"role": "user", "content": "Hello!"}],
)

# Execute a task
result = await client.kernel.execute(
    task="Analyze sales data",
    agent_id="analyst",
)

# RAG query
results = await client.rag.query(
    query="What is NOVA CORE?",
    top_k=5,
)
```

## Services

The SDK provides typed service clients for all NOVA CORE API modules:

| Service | Access | Description |
|---------|--------|-------------|
| `client.agents` | Agent Management | CRUD, runtime dispatch, coordination |
| `client.models` | Model Gateway | Chat, health, provider management |
| `client.memory` | Conversation Memory | Session history retrieval |
| `client.kernel` | Kernel Execution | Task execution with full orchestration |
| `client.goals` | Goal Management | Create, track, analyze goals |
| `client.tasks` | Task Management | CRUD, state transitions |
| `client.workflows` | Workflow Engine | Definitions, executions, templates |
| `client.scheduler` | Scheduler | Job CRUD, pause/resume/retry |
| `client.tools` | Tool System | Register, execute, health |
| `client.rag` | RAG Engine | Query, retrieve, index, reindex |
| `client.vector_memory` | Vector Memory | Store, search, similarity |
| `client.events` | Event System | Publish, list, statistics |
| `client.plugins` | Plugin System | Register, enable, disable, execute |
| `client.learning` | Learning Engine | Extract, search, consolidate |
| `client.knowledge_graph` | Knowledge Graph | Entities, relationships, queries |
| `client.observability` | Observability | Metrics, traces, logs, alerts |
| `client.deployment` | Deployment | Health, readiness, config |
| `client.scaling` | Scaling | Workers, queues, cache |
| `client.security` | Security | Auth, API keys, RBAC |
| `client.enterprise` | Enterprise | Orgs, tenants, workspaces, roles |
| `client.profile` | User Profile | Profile retrieval |
| `client.database` | Database | Health, migrations, schema |
| `client.performance` | Performance | Benchmarks, diagnostics |
| `client.resilience` | Resilience | Circuit breakers, retries |
| `client.autonomy` | Autonomy | Objectives, recommendations |

## Authentication

```python
# API Key
config = Configuration(api_key="your-key")

# Bearer Token
config = Configuration(bearer_token="your-token")

# From factory
from nova_core_sdk import create_client
client = create_client(base_url="http://localhost:8000", api_key="your-key")
```

## Pagination

```python
# List items with pagination
items = await client.tasks.list(limit=20, offset=0)
```

## Error Handling

```python
from nova_core_sdk.exceptions import (
    NovaAPIError,
    NovaAuthError,
    NovaRateLimitError,
    NovaServerError,
    NovaTimeoutError,
)

try:
    result = await client.models.chat(model="llama3.2", messages=[...])
except NovaAuthError:
    print("Authentication failed")
except NovaRateLimitError as e:
    print(f"Rate limited, retry after {e.retry_after}s")
except NovaServerError:
    print("Server error")
except NovaTimeoutError:
    print("Request timed out")
```

## Retry Configuration

```python
config = Configuration(
    max_retries=5,
    retry_base_delay=1.0,
    retry_max_delay=60.0,
    retry_backoff=2.0,
)
```

## WebSocket

```python
ws = client.websocket("/ws/events")
ws.on("message", lambda msg: print(msg))
await ws.connect()
await ws.listen()
```

## Telemetry

```python
config = Configuration(telemetry_enabled=True)
client = NovaClient(config)
# ... make requests ...
metrics = client._telemetry.get_metrics()
```
