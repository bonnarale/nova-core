# NOVA CORE TypeScript SDK

## Installation

```bash
npm install @novacore/sdk
# or
yarn add @novacore/sdk
# or
pnpm add @novacore/sdk
```

## Quick Start

```typescript
import { NovaClient, createConfiguration } from "@novacore/sdk";

const config = createConfiguration({
  baseUrl: "http://localhost:8000",
  apiKey: "your-api-key",
});

const client = new NovaClient(config);

// Health check
const health = await client.health();

// Chat with a model
const response = await client.models.chat({
  model: "llama3.2",
  messages: [{ role: "user", content: "Hello!" }],
});

// Execute a task
const result = await client.kernel.execute({
  task: "Analyze sales data",
  agent_id: "analyst",
});

// RAG query
const ragResults = await client.rag.query({
  query: "What is NOVA CORE?",
  top_k: 5,
});
```

## Services

All services are available as properties on the client:

```typescript
client.agents       // Agent Management
client.models       // Model Gateway
client.memory       // Conversation Memory
client.kernel       // Kernel Execution
client.goals        // Goal Management
client.tasks        // Task Management
client.workflows    // Workflow Engine
client.scheduler    // Scheduler
client.tools        // Tool System
client.rag          // RAG Engine
client.vectorMemory // Vector Memory
client.events       // Event System
client.plugins      // Plugin System
client.learning     // Learning Engine
client.knowledgeGraph // Knowledge Graph
client.observability  // Observability
client.deployment   // Deployment
client.scaling      // Scaling
client.security     // Security
client.enterprise   // Enterprise
client.profile      // User Profile
client.database     // Database
client.performance  // Performance
client.resilience   // Resilience
client.autonomy     // Autonomy
```

## Authentication

```typescript
import { createConfiguration } from "@novacore/sdk";

// API Key
const config = createConfiguration({ apiKey: "your-key" });

// Bearer Token
const config = createConfiguration({ bearerToken: "your-token" });
```

## Error Handling

```typescript
import {
  NovaAPIError,
  NovaAuthError,
  NovaRateLimitError,
  NovaServerError,
  NovaTimeoutError,
} from "@novacore/sdk";

try {
  const result = await client.models.chat({...});
} catch (error) {
  if (error instanceof NovaAuthError) {
    console.error("Authentication failed");
  } else if (error instanceof NovaRateLimitError) {
    console.error(`Rate limited, retry after ${error.retryAfter}s`);
  }
}
```

## Streaming

```typescript
import { createStream } from "@novacore/sdk";

const stream = await createStream(config, "/models/chat", {
  model: "llama3.2",
  messages: [{ role: "user", content: "Hello!" }],
  stream: true,
});

for await (const chunk of stream.iter()) {
  process.stdout.write(chunk.choices?.[0]?.delta?.content || "");
}
```

## WebSocket

```typescript
import { WebSocketClient } from "@novacore/sdk";

const ws = new WebSocketClient("ws://localhost:8000/ws/events");
ws.on("message", (msg) => console.log(msg));
await ws.connect();
```

## Retry Configuration

```typescript
const config = createConfiguration({
  maxRetries: 5,
  retryBaseDelay: 1000,
  retryMaxDelay: 60000,
  retryBackoff: 2,
});
```

## Telemetry

```typescript
const metrics = client.getMetrics();
console.log(`Total requests: ${metrics.totalRequests}`);
console.log(`Average latency: ${metrics.totalLatencyMs / metrics.totalRequests}ms`);
```
