# Observability

## Overview

NOVA CORE provides comprehensive observability through metrics, distributed tracing, structured logging, health checks, diagnostics, and alerting.

## Components

| Component | Package | Description |
|-----------|---------|-------------|
| Metrics Provider | `app.observability.base` | Metrics collection ABC |
| Tracing Provider | `app.observability.base` | Distributed tracing ABC |
| Logging Provider | `app.observability.base` | Structured logging ABC |
| Health Provider | `app.observability.base` | Health checks ABC |
| Diagnostics Provider | `app.observability.base` | System diagnostics ABC |
| Alert Provider | `app.observability.base` | Alert management ABC |
| Exporter Provider | `app.observability.base` | Data export ABC |

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /observability/health` | Service health status |
| `GET /observability/readiness` | Kubernetes readiness probe |
| `GET /observability/liveness` | Kubernetes liveness probe |
| `GET /observability/metrics` | Aggregated metrics |
| `GET /observability/traces` | Recent traces |
| `GET /observability/logs` | Recent logs |
| `GET /observability/diagnostics` | System diagnostics |
| `GET /observability/alerts` | Active alerts |
| `GET /observability/statistics` | Observability statistics |
| `GET /observability/export/prometheus` | Prometheus format export |
| `GET /observability/export/json` | JSON format export |
| `GET /observability/export/csv` | CSV format export |

## Metrics

Each subsystem collects its own metrics:

| Subsystem | Metrics Module |
|-----------|----------------|
| Events | `app.events.metrics` |
| Workflows | `app.workflows.metrics` |
| Database | `app.db.metrics` |
| Deployment | `app.deployment.metrics` |
| Scaling | `app.scaling.metrics` |
| Tools | `app.tools.metrics` |
| Vector Memory | `app.vector_memory.metrics` |

## Tracing

Each subsystem implements distributed tracing with hierarchical spans:

```python
span_id = tracer.start_span("operation_name", parent_id=parent_span)
# ... perform operation
tracer.end_span(span_id, status="ok")
```

## Health Checks

Three probe types for Kubernetes:

| Probe | Path | Purpose |
|-------|------|---------|
| Health | `/observability/health` | Overall health |
| Readiness | `/observability/readiness` | Ready to accept traffic |
| Liveness | `/observability/liveness` | Process is alive |
