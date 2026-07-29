# NOVA CORE SDK Migration Guide

## Overview

The NOVA CORE SDK provides official client libraries for consuming the NOVA CORE API. This guide covers migration from direct HTTP API calls to the SDK.

## Python SDK Migration

### Before (Direct HTTP)
```python
import httpx

async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
    response = await client.post("/models/chat", json={
        "model": "llama3.2",
        "messages": [{"role": "user", "content": "Hello"}],
    })
    data = response.json()
```

### After (SDK)
```python
from nova_core_sdk import NovaClient, Configuration

client = NovaClient(Configuration(base_url="http://localhost:8000"))
data = await client.models.chat(
    model="llama3.2",
    messages=[{"role": "user", "content": "Hello"}],
)
```

## TypeScript SDK Migration

### Before (Direct Fetch)
```typescript
const response = await fetch("http://localhost:8000/models/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    model: "llama3.2",
    messages: [{ role: "user", content: "Hello" }],
  }),
});
const data = await response.json();
```

### After (SDK)
```typescript
import { NovaClient, createConfiguration } from "@novacore/sdk";

const client = new NovaClient(createConfiguration({
  baseUrl: "http://localhost:8000",
}));
const data = await client.models.chat({
  model: "llama3.2",
  messages: [{ role: "user", content: "Hello" }],
});
```

## CLI Migration

### Before (curl)
```bash
curl -X POST http://localhost:8000/models/chat \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3.2","messages":[{"role":"user","content":"Hello"}]}'
```

### After (CLI)
```bash
export NOVA_API_KEY=your-key
nova chat "Hello"
```

## Authentication

| Method | Direct API | SDK |
|--------|-----------|-----|
| API Key | `X-API-Key` header | `Configuration(api_key="...")` |
| Bearer | `Authorization: Bearer` header | `Configuration(bearer_token="...")` |
| Env | Set headers manually | `NOVA_API_KEY` env var |

## Error Handling

The SDK maps HTTP status codes to typed exceptions:

| Status | Exception |
|--------|-----------|
| 401 | `NovaAuthError` |
| 422 | `NovaValidationError` |
| 429 | `NovaRateLimitError` |
| 5xx | `NovaServerError` |
| Timeout | `NovaTimeoutError` |
| Connection | `NovaConnectionError` |

## Retry Behavior

The SDK automatically retries failed requests:
- Default: 3 retries
- Backoff: exponential (0.5s, 1s, 2s, ...)
- Retryable: 429, 500, 502, 503, 504

Configure via `Configuration(max_retries=5, retry_base_delay=1.0)`.

## Telemetry

Enable SDK telemetry to track request metrics:
```python
config = Configuration(telemetry_enabled=True)
```

The telemetry collector tracks:
- Total requests and errors
- Latency per request
- Requests by endpoint
- Error distribution by type
