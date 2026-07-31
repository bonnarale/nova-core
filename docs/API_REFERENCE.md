# API Reference

## Base URL

All endpoints are served under `/api/v1/`.

## Authentication

Most endpoints require either:
- Bearer token in `Authorization` header
- API key in `X-API-Key` header

Public endpoints: `/health`

## Endpoints by Subsystem

### Health (`/health`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |

### Agents (`/agents`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/agents` | List all agents |
| GET | `/agents/{agent_id}` | Get agent by ID |
| POST | `/agents` | Create agent |
| PATCH | `/agents/{agent_id}` | Update agent |
| DELETE | `/agents/{agent_id}` | Delete agent |
| POST | `/agents/register` | Register agent |
| GET | `/agents/health` | Agent health check |
| GET | `/agents/capabilities` | Get agent capabilities |
| POST | `/agents/runtime/dispatch` | Dispatch runtime task |
| POST | `/agents/runtime/coordinate` | Coordinate runtime task |
| GET | `/agents/runtime/metrics` | Runtime metrics |
| GET | `/agents/runtime/traces` | Runtime traces |
| GET | `/agents/runtime/scheduler` | Runtime scheduler info |
| POST | `/agents/runtime/cancel/{task_id}` | Cancel runtime task |

### Events (`/events`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/events/publish` | Publish event |
| POST | `/events/replay` | Replay events |
| GET | `/events` | List events |
| GET | `/events/statistics` | Event statistics |
| GET | `/events/metrics` | Event metrics |
| GET | `/events/health` | Event health check |
| GET | `/events/traces` | Event traces |
| GET | `/events/{event_id}` | Get event by ID |

### Goals (`/goals`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/goals/{user_id}` | List goals |
| POST | `/goals/{user_id}` | Create goal |
| GET | `/goals/{user_id}/detail/{goal_id}` | Get goal |
| PATCH | `/goals/{user_id}/detail/{goal_id}` | Update goal |
| DELETE | `/goals/{user_id}/detail/{goal_id}` | Delete goal |
| GET | `/goals/{user_id}/next-actions` | Next actions |
| GET | `/goals/{user_id}/blocked` | Blocked goals |
| GET | `/goals/{user_id}/analyze` | Analyze goals |

### Knowledge Graph (`/knowledge-graph`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/knowledge-graph/entities` | Create entity |
| GET | `/knowledge-graph/entities` | List entities |
| GET | `/knowledge-graph/entities/{entity_id}` | Get entity |
| PUT | `/knowledge-graph/entities/{entity_id}` | Update entity |
| DELETE | `/knowledge-graph/entities/{entity_id}` | Delete entity |
| POST | `/knowledge-graph/relationships` | Create relationship |
| GET | `/knowledge-graph/relationships` | List relationships |
| GET | `/knowledge-graph/relationships/{rel_id}` | Get relationship |
| DELETE | `/knowledge-graph/relationships/{rel_id}` | Delete relationship |
| GET | `/knowledge-graph/entities/{entity_id}/relationships` | Entity relationships |
| POST | `/knowledge-graph/query/neighborhood` | Query neighborhood |
| POST | `/knowledge-graph/query/shortest-path` | Shortest path |
| POST | `/knowledge-graph/query/connected` | Connected entities |
| POST | `/knowledge-graph/search` | Search graph |
| POST | `/knowledge-graph/extract` | Extract from text |
| POST | `/knowledge-graph/merge` | Merge entities |
| GET | `/knowledge-graph/validate` | Validate graph |
| GET | `/knowledge-graph/types` | List types |

### Learning (`/learning`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/learning/extract` | Extract knowledge |
| POST | `/learning/search` | Search knowledge |
| GET | `/learning/artifacts` | List artifacts |
| GET | `/learning/artifacts/{artifact_id}` | Get artifact |
| DELETE | `/learning/artifacts/{artifact_id}` | Delete artifact |
| POST | `/learning/consolidate` | Consolidate knowledge |
| GET | `/learning/stats` | Learning statistics |

### Models (`/models`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/models/chat` | Chat with model |
| GET | `/models/health` | Model health |
| GET | `/models/metrics` | Model metrics |
| GET | `/models/list` | List models |
| GET | `/models/providers` | List providers |
| GET | `/models/cache/stats` | Cache stats |
| DELETE | `/models/cache` | Clear cache |
| GET | `/models/traces` | Model traces |

### Observability (`/observability`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/observability/health` | Observability health |
| GET | `/observability/readiness` | Readiness check |
| GET | `/observability/liveness` | Liveness check |
| GET | `/observability/metrics` | Metrics |
| GET | `/observability/traces` | Traces |
| GET | `/observability/logs` | Logs |
| GET | `/observability/diagnostics` | Diagnostics |
| GET | `/observability/alerts` | Active alerts |
| GET | `/observability/statistics` | Statistics |
| GET | `/observability/export/prometheus` | Prometheus export |
| GET | `/observability/export/json` | JSON export |
| GET | `/observability/export/csv` | CSV export |

### Plugins (`/plugins`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/plugins` | List plugins |
| GET | `/plugins/health` | Plugin health |
| GET | `/plugins/statistics` | Plugin statistics |
| GET | `/plugins/{plugin_id}` | Get plugin |
| POST | `/plugins` | Register plugin |
| DELETE | `/plugins/{plugin_id}` | Unregister plugin |
| POST | `/plugins/{plugin_id}/enable` | Enable plugin |
| POST | `/plugins/{plugin_id}/disable` | Disable plugin |
| POST | `/plugins/{plugin_id}/execute` | Execute plugin |
| GET | `/plugins/hooks/list` | List hooks |
| GET | `/plugins/hooks/statistics` | Hook statistics |
| GET | `/plugins/sandbox/stats` | Sandbox stats |
| GET | `/plugins/events/recent` | Recent events |

### RAG (`/rag`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/rag/query` | RAG query |
| POST | `/rag/retrieve` | RAG retrieve |
| POST | `/rag/index` | Index document |
| POST | `/rag/reindex` | Reindex |
| GET | `/rag/health` | RAG health |
| GET | `/rag/metrics` | RAG metrics |
| GET | `/rag/traces` | RAG traces |
| GET | `/rag/statistics` | RAG statistics |

### Scheduler (`/scheduler`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/scheduler/jobs` | Schedule job |
| GET | `/scheduler/jobs` | List jobs |
| GET | `/scheduler/jobs/{job_id}` | Get job |
| DELETE | `/scheduler/jobs/{job_id}` | Delete job |
| POST | `/scheduler/jobs/{job_id}/execute` | Execute job |
| POST | `/scheduler/jobs/{job_id}/cancel` | Cancel job |
| POST | `/scheduler/jobs/{job_id}/pause` | Pause job |
| POST | `/scheduler/jobs/{job_id}/resume` | Resume job |
| POST | `/scheduler/jobs/{job_id}/retry` | Retry job |
| POST | `/scheduler/run-pending` | Run pending |
| GET | `/scheduler/statistics` | Statistics |
| GET | `/scheduler/metrics` | Metrics |
| GET | `/scheduler/traces` | Traces |
| GET | `/scheduler/health` | Health |

### Security (`/security`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/security/health` | Security health |
| GET | `/security/headers` | Security headers |
| GET | `/security/statistics` | Security statistics |
| POST | `/security/auth/register` | Register user |
| POST | `/security/auth/login` | User login |
| POST | `/security/auth/token/verify` | Verify token |
| POST | `/security/auth/token/revoke` | Revoke token |
| POST | `/security/api-keys` | Create API key |
| GET | `/security/api-keys/{user_id}` | List API keys |
| DELETE | `/security/api-keys/{key_id}` | Revoke API key |
| GET | `/security/audit` | Audit log |
| GET | `/security/rbac/roles` | List roles |
| POST | `/security/rbac/check` | Check permission |

### Tasks (`/tasks`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/tasks` | Create task |
| GET | `/tasks` | List tasks |
| GET | `/tasks/{task_id}` | Get task |
| PATCH | `/tasks/{task_id}` | Update task |
| DELETE | `/tasks/{task_id}` | Delete task |
| POST | `/tasks/{task_id}/advance` | Advance step |
| POST | `/tasks/{task_id}/transition` | Transition state |

### Tools (`/tools`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/tools` | List tools |
| GET | `/tools/metrics` | Tool metrics |
| GET | `/tools/traces` | Tool traces |
| GET | `/tools/{tool_id}` | Get tool |
| POST | `/tools/register` | Register tool |
| DELETE | `/tools/{tool_id}` | Unregister tool |
| POST | `/tools/{tool_id}/execute` | Execute tool |
| GET | `/tools/{tool_id}/health` | Tool health |

### Vector Memory (`/vector-memory`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/vector-memory/store` | Store vector |
| POST | `/vector-memory/search` | Search vectors |
| POST | `/vector-memory/similarity` | Similarity search |
| POST | `/vector-memory/consolidate` | Consolidate |
| POST | `/vector-memory/reindex` | Reindex |
| DELETE | `/vector-memory/{vector_id}` | Delete vector |
| GET | `/vector-memory/statistics` | Statistics |
| GET | `/vector-memory/health` | Health |
| GET | `/vector-memory/metrics` | Metrics |
| GET | `/vector-memory/traces` | Traces |

### Workflows (`/workflows`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/workflows` | Create workflow |
| GET | `/workflows` | List workflows |
| GET | `/workflows/{workflow_id}` | Get workflow |
| PUT | `/workflows/{workflow_id}` | Update workflow |
| DELETE | `/workflows/{workflow_id}` | Delete workflow |
| POST | `/workflows/executions` | Create execution |
| GET | `/workflows/executions` | List executions |
| GET | `/workflows/executions/{execution_id}` | Get execution |
| POST | `/workflows/executions/{execution_id}/start` | Start execution |
| POST | `/workflows/executions/{execution_id}/action` | Execute action |
| GET | `/workflows/executions/{execution_id}/events` | Execution events |
| POST | `/workflows/import` | Import workflow |
| GET | `/workflows/export/{workflow_id}` | Export workflow |
| GET | `/workflows/templates` | List templates |
| GET | `/workflows/metrics` | Metrics |
| GET | `/workflows/statistics` | Statistics |
| GET | `/workflows/health` | Health |
| GET | `/workflows/traces` | Traces |

### Database (`/database`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/database/health` | Database health |
| GET | `/database/statistics` | Database statistics |
| GET | `/database/migrations` | Migration status |
| GET | `/database/schema` | Schema info |
| GET | `/database/metrics` | Database metrics |
| GET | `/database/traces` | Database traces |

### Deployment (`/deployment`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/deployment/health` | Deployment health |
| GET | `/deployment/readiness` | Readiness |
| GET | `/deployment/liveness` | Liveness |
| GET | `/deployment/environment` | Environment |
| GET | `/deployment/configuration` | Configuration |
| GET | `/deployment/diagnostics` | Diagnostics |
| GET | `/deployment/metrics` | Deployment metrics |
| GET | `/deployment/statistics` | Statistics |

### Scaling (`/scaling`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/scaling/health` | Scaling health |
| GET | `/scaling/metrics` | Scaling metrics |
| GET | `/scaling/statistics` | Statistics |
| GET | `/scaling/workers` | Worker pool |
| GET | `/scaling/queues` | Queue status |
| GET | `/scaling/cache` | Cache stats |
| GET | `/scaling/resources` | Resources |
| POST | `/scaling/scale-up` | Scale up |
| POST | `/scaling/scale-down` | Scale down |
| POST | `/scaling/cache/clear` | Clear cache |

### Future Roadmap (`/future`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/future/features` | Feature flags |
| GET | `/future/experiments` | Experiments |
| GET | `/future/capabilities` | Capabilities |
| GET | `/future/compatibility` | Compatibility report |
| GET | `/future/deprecations` | Deprecations |
| GET | `/future/roadmap` | Roadmap |
| GET | `/future/metrics` | Future metrics |
| GET | `/future/statistics` | Statistics |

## Endpoint Summary

| HTTP Method | Count |
|-------------|-------|
| GET | 105 |
| POST | 52 |
| PUT | 3 |
| PATCH | 3 |
| DELETE | 16 |
| **Total** | **179** |

## Response Format

All endpoints return JSON with the standard envelope:

```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

Error responses:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found"
  }
}
```
