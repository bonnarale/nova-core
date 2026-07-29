# NOVA CORE SDK Examples

## Python Examples

### Basic Usage
```python
from nova_core_sdk import NovaClient, Configuration

config = Configuration(base_url="http://localhost:8000", api_key="key")
client = NovaClient(config)

# Health
health = await client.health()

# Chat
resp = await client.models.chat(model="llama3.2", messages=[{"role": "user", "content": "Hi"}])
print(resp["response"]["content"])
```

### Agent Management
```python
# Create an agent
agent = await client.agents.create(
    id="analyst",
    name="Data Analyst",
    role="analyst",
    description="Analyzes sales data",
    system_prompt="You are a data analyst.",
)

# Dispatch a task
result = await client.agents.dispatch(
    task="Analyze Q4 sales",
    context={"quarter": "Q4"},
    timeout=60.0,
)
```

### RAG Pipeline
```python
# Index a document
await client.rag.index(
    content="NOVA CORE is an AI operating system...",
    title="NOVA CORE Overview",
    source="docs",
)

# Query
results = await client.rag.query(query="What is NOVA CORE?", top_k=5)
for citation in results["citations"]:
    print(citation)
```

### Workflow Execution
```python
# Create a workflow
wf = await client.workflows.create(
    name="Data Pipeline",
    steps=[
        {"id": "extract", "handler": "extract_data"},
        {"id": "transform", "handler": "transform_data", "depends_on": ["extract"]},
        {"id": "load", "handler": "load_data", "depends_on": ["transform"]},
    ],
)

# Execute
execution = await client.workflows.execute(workflow_id=wf["id"], input={"source": "db"})
```

### Goal Tracking
```python
# Create a goal
goal = await client.goals.create(user_id="user-123", title="Launch v2.0", priority=5)

# Track progress
await client.goals.update(user_id="user-123", goal_id=goal["id"], progress=75)
```

## TypeScript Examples

### Basic Usage
```typescript
import { NovaClient, createConfiguration } from "@novacore/sdk";

const client = new NovaClient(createConfiguration({
  baseUrl: "http://localhost:8000",
  apiKey: "your-key",
}));

const health = await client.health();
const chat = await client.models.chat({
  model: "llama3.2",
  messages: [{ role: "user", content: "Hello!" }],
});
```

### Streaming
```typescript
import { createStream } from "@novacore/sdk";

const stream = await createStream(config, "/models/chat", {
  model: "llama3.2",
  messages: [{ role: "user", content: "Tell me a story" }],
  stream: true,
});

for await (const chunk of stream.iter()) {
  process.stdout.write(chunk.choices?.[0]?.delta?.content || "");
}
```

### Error Handling
```typescript
import { NovaClient, NovaAuthError, NovaRateLimitError } from "@novacore/sdk";

try {
  await client.models.chat({ model: "llama3.2", messages: [...] });
} catch (error) {
  if (error instanceof NovaAuthError) {
    console.error("Check your API key");
  } else if (error instanceof NovaRateLimitError) {
    console.log(`Retrying in ${error.retryAfter}s...`);
  }
}
```

## CLI Examples

```bash
# Health check
nova health

# Chat
nova chat "What is the weather?"

# Execute a task
nova execute "Create a summary report" --agent analyst

# Manage workflows
nova workflow list
nova workflow execute <id>

# Monitor
nova observability metrics
nova deployment health
```
