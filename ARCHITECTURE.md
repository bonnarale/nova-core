# NOVA CORE — Architecture Document (Honest Assessment)

> Auto-generated map of the real codebase. No optimism — only what actually exists and works.

---

## 1. Backend Directory Map (`backend/app/`)

| Folder | What it does | Status |
|--------|-------------|--------|
| `agents/` | Multi-Agent Runtime — register, dispatch, schedule, and coordinate specialized AI agents (Planner, Researcher, Coder, etc.) | ✅ Wired in lifespan |
| `api/` | REST API layer — 35 versioned routers (`/api/v1/...`), middleware, pagination, filtering, OpenAPI docs | ✅ Active |
| `assistant/` | NOVA Assistant — conversational AI interface with autonomous execution, memory, planning, reasoning | ⚠️ Exists but NOT wired in lifespan |
| `autonomy/` | Autonomy Engine — self-governance: delegation, approvals, objectives, optimization, self-improvement | ✅ Wired in lifespan |
| `cognitive/` | Cognitive Engine — the "brain": intent detection, decision routing, state management | ✅ Wired in lifespan (master coordinator) |
| `command_center/` | Command Center — project management hub: objectives, backlogs, milestones, roadmaps, Governor | ✅ Used via `CommandCenterFactory` in nova_web routes |
| `constitution/` | Constitution — mission, values, policies, priorities, approval rules | ✅ Wired in lifespan |
| `core/` | Config + logging — `get_settings()`, logging setup | ✅ Used everywhere |
| `db/` | Database layer — PostgreSQL, repositories, sessions, migrations, connection pooling | ✅ Wired in lifespan |
| `deployment/` | Deployment Manager — env management, secrets, readiness/liveness probes, diagnostics | ✅ Wired in lifespan |
| `enterprise/` | Enterprise — orgs, tenants, workspaces, teams, roles, permissions, billing, licensing | ✅ Wired in lifespan |
| `events/` | Event System — async event bus, pub/sub, dispatcher, replay, persistence | ✅ Wired in lifespan |
| `executive/` | Executive Planner — decomposes goals into tasks using strategies | ✅ Wired in lifespan |
| `future/` | Future Roadmap — feature flags, experiments, extension points, deprecation, versioning | ✅ Wired in lifespan |
| `integration/` | System Integration — dependency graphs, compatibility checks, health aggregation | ✅ Wired in lifespan |
| `kernel/` | Kernel — core execution engine: agent/tool registry, session management, event system | ✅ Wired in lifespan (last component started) |
| `knowledge_graph/` | Knowledge Graph — entity/relationship extraction, dedup, traversal, search, validation | ✅ Wired in lifespan |
| `learning/` | Learning Engine — extracts knowledge from executions, consolidation, ranking | ✅ Wired in lifespan |
| `long_term_memory/` | Long-Term Memory — durable memories with consolidation, dedup, importance scoring | ✅ Wired in lifespan |
| `memory/` | Memory services — conversation memory, profile memory, goal manager, semantic memory | ✅ Wired in lifespan |
| `models/` | Model Gateway — LLM provider abstraction: Ollama/Mock/OpenAI, caching, load balancing | ✅ Wired in lifespan |
| `nova_os/` | NOVA OS — AI Operating System abstraction: runtime, intelligence, governor, orchestration | ⚠️ Exists but NOT directly wired in lifespan |
| `observability/` | Observability — metrics, tracing, logging, health checks, alerting, profiling | ✅ Wired in lifespan |
| `orchestrator/` | Task Orchestrator — task lifecycle, planner, worker, internal event bus | ✅ Wired in lifespan |
| `performance/` | Performance — profiling, benchmarking, cache/query/RAG/vector optimizers | ✅ Wired in lifespan |
| `planner/` | Autonomous Planner — decomposes objectives into executable plans, reviews, replans | ✅ Wired in lifespan |
| `plugins/` | Plugin Engine — dynamic plugin lifecycle: discovery, loading, sandboxing, hooks | ✅ Wired in lifespan |
| `profile/` | User Profile — preferences, priorities, objectives, projects, roadmap, history | ⚠️ Exists, partially wired |
| `rag/` | RAG & Retrieval — chunking, embeddings, indexing, query rewriting, reranking, citations | ✅ Wired in lifespan |
| `reasoning/` | Reasoning Engine — multi-step reasoning with strategies (analytical, comparative, self-critique) | ✅ Wired in lifespan |
| `resilience/` | Resilience — circuit breakers, bulkheads, retry, timeout, failover, fallback, watchdog | ✅ Wired in lifespan |
| `scaling/` | Scaling — autoscaler, load balancer, worker pool, queue manager, caching, sharding | ✅ Wired in lifespan |
| `scheduler/` | Scheduler — cron/interval/event/dependency triggers, job queue, dispatch, persistence | ✅ Wired in lifespan |
| `schemas/` | Shared Pydantic schemas (conversation) | ✅ Used by API |
| `security/` | Security — auth, RBAC, API keys, tokens, sessions, crypto, rate limiting, audit | ✅ Wired in lifespan |
| `services/` | External clients — ChromaDB, Ollama, Redis, content extractor wrappers | ✅ Wired in lifespan |
| `tools/` | Tool Runtime — filesystem, git, docker, Python, HTTP, web tools with permissions | ✅ Wired in lifespan |
| `vector_memory/` | Vector Memory — dense vector storage, similarity search, consolidation, indexing | ✅ Wired in lifespan |
| `workflows/` | Workflow Engine — DAG graphs, conditions, loops, parallel branches, state machines | ✅ Wired in lifespan |

**Summary:** 37 subdirectories, ~430 Python files. Most engines ARE wired in `lifespan()`. The main exceptions are `assistant/` and `nova_os/` which exist but are not directly initialized in the lifespan function.

---

## 2. All Engines, Managers, and Governor Classes

### 2.1 Engines initialized in `lifespan()` (main.py:83-613)

| # | Engine | Stored at | Factory/Source |
|---|--------|-----------|----------------|
| 1 | Event Bus + Dispatcher + Publisher + Subscriber + Replay + Lifecycle | `app.state.event_*` | `EventSystemFactory` |
| 2 | Scheduler | `app.state.scheduler` | `SchedulerFactory` |
| 3 | Agent Manager + Runtime + Factory | `app.state.agent_*` | Direct + `AgentFactory` |
| 4 | Tool Manager + Factory + Runtime | `app.state.tool_*` | Direct + `ToolFactory` |
| 5 | Task Manager | `app.state.task_manager` | Direct |
| 6 | Executive Planner | `app.state.executive_planner` | Direct |
| 7 | Semantic Memory | `app.state.semantic_memory` | Direct |
| 8 | Long-Term Memory | `app.state.long_term_memory` | `LTMStoreAdapter` |
| 9 | Autonomous Planner | `app.state.planner` | Direct |
| 10 | Reasoning Engine | `app.state.reasoning_engine` | Direct |
| 11 | Workflow Engine + Orchestrator | `app.state.workflow_*` | Direct + `WorkflowFactory` |
| 12 | Knowledge Graph Engine | `app.state.knowledge_graph_engine` | Direct |
| 13 | Learning Engine | `app.state.learning_engine` | `LearningEngineFactory` |
| 14 | Observability Engine | `app.state.observability_engine` | `ObservabilityFactory` |
| 15 | Plugin Engine | `app.state.plugin_engine` | `PluginFactory` |
| 16 | Security Engine | `app.state.security_engine` | `SecurityFactory` |
| 17 | Enterprise Engine | `app.state.enterprise_engine` | `EnterpriseFactory` |
| 18 | Autonomy Engine | `app.state.autonomy_engine` | `AutonomyFactory` |
| 19 | Deployment Manager | `app.state.deployment_manager` | `DeploymentFactory` |
| 20 | Scaling Engine | `app.state.scaling_engine` | `ScalingFactory` |
| 22 | Resilience Engine | `app.state.resilience_engine` | `ResilienceFactory` |
| 23 | Performance Engine | `app.state.performance_engine` | `PerformanceFactory` |
| 24 | Integration Engine | `app.state.integration_engine` | `IntegrationFactory` |
| 25 | Future Registry | `app.state.future_registry` | `FutureFactory` |
| 26 | DB Architecture (7 sub-components) | `app.state.db_architecture` | `DatabaseFactory` |
| 27 | Model Gateway | `app.state.model_gateway` | `ModelGatewayFactory` |
| 28 | RAG Engine | `app.state.rag_engine` | `RAGFactory` |
| 29 | Vector Memory Engine | `app.state.vector_memory_engine` | `VectorMemoryFactory` |
| 30 | Cognitive Engine | `app.state.cognitive_engine` | Direct (master coordinator) |
| 31 | Kernel | `app.state.kernel` | `get_kernel()` |
| 32 | API Platform | `app.state.api_platform` | Direct |

### 2.2 Engines that exist but are NOT wired in lifespan

| Engine | File | Status |
|--------|------|--------|
| `AutonomyEngine` | `autonomy/autonomy_engine.py` | ❌ Not used anywhere |
| `ApprovalEngine` | `autonomy/approval_engine.py` | ❌ Not used anywhere |
| `RecommendationEngine` | `autonomy/recommendation_engine.py` | ❌ Not used anywhere |
| `OptimizationEngine` | `autonomy/optimization_engine.py` | ❌ Not used anywhere |
| `DelegationEngine` | `autonomy/delegation_engine.py` | ❌ Not used anywhere |
| `NovaOperatingSystem` | `nova_os/operating_system.py` | ❌ Not wired (nova_os/ folder is largely unused) |
| `Assistant` | `assistant/assistant.py` | ❌ Not wired (assistant routes use CommandCenterFactory directly) |

### 2.3 Manager classes

| Manager | File | Wired? | Used by |
|---------|------|--------|---------|
| `AgentManager` | `agents/agent_manager.py` | ✅ | lifespan, agents router |
| `TaskManager` | `orchestrator/task_manager.py` | ✅ | lifespan, tasks router |
| `GoalManager` | `memory/goals.py` | ✅ | lifespan, goals router |
| `ToolManager` | `tools/manager.py` | ✅ | lifespan, tools router |
| `ObjectiveManager` | `autonomy/objective_manager.py` | ✅ | CommandCenterFactory |
| `ProjectManager` | `autonomy/project_manager.py` | ✅ | CommandCenterFactory |
| `ResearchManager` | `autonomy/research_manager.py` | ⚠️ | Created in autonomy system, not directly in lifespan |
| `RoadmapManager` | `autonomy/roadmap_manager.py` | ⚠️ | Created in autonomy system, not directly in lifespan |
| `TokenManager` | `security/token_manager.py` | ⚠️ | Security engine internal |
| `SandboxManager` | `plugins/sandbox_manager.py` | ⚠️ | Plugin engine internal |
| `ResourceManager` | `scaling/resource_manager.py` | ⚠️ | Scaling engine internal |
| `QueueManager` | `scaling/queue_manager.py` | ⚠️ | Scaling engine internal |
| `SessionManager` | `db/session_manager.py` | ✅ | DB architecture |

### 2.4 Built-in Agents (amBotHs Integration)

| Agent | File | agent_id | Role | Intents | Source |
|-------|------|----------|------|---------|--------|
| `PlannerAgent` | `agents/builtins/planner_agent.py` | `planner` | planning | planning, decomposition | nova-core native |
| `ResearchAgent` | `agents/builtins/research_agent.py` | `researcher` | research | research, search, lookup | nova-core native |
| `CoderAgent` | `agents/builtins/coder_agent.py` | `coder` | coder | coding, implementation, write | nova-core native |
| `ReviewerAgent` | `agents/builtins/reviewer_agent.py` | `reviewer` | reviewer | review, validate, check | nova-core native |
| `MemoryAgent` | `agents/builtins/memory_agent.py` | `memory` | memory | memory, recall, store | nova-core native |
| `ExecutorAgent` | `agents/builtins/executor_agent.py` | `executor` | execution | execution, run, deploy | nova-core native |
| `CoordinatorAgent` | `agents/builtins/coordinator_agent.py` | `coordinator` | coordination | orchestration, coordinate | nova-core native |
| **`CodeReviewerAgent`** | `agents/builtins/code_reviewer_agent.py` | `code-reviewer` | reviewer | code-review, audit-code | **amBotHs port** |
| **`PrompterAgent`** | `agents/builtins/prompter_agent.py` | `prompter` | prompt-engineering | prompt-improvement, prompt-engineering | **amBotHs port** |
| **`CriticPremortemAgent`** | `agents/builtins/critic_premortem_agent.py` | `critic-premortem` | risk-analysis | risk-analysis, premortem, failure-analysis | **amBotHs port** |

**Registration:** `AgentFactory.register_all_builtins()` — 9 agents total (7 native + 3 amBotHs ports).
**Routing:** `AgentCapability` with intent/task_type/tag matching via `CapabilityRegistry`.
**Dispatch:** `runtime.dispatch(agent_id, task, context)` or capability-based `runtime.dispatcher.score_agents(intent=...)`.

---

## 3. The 4 Governor Classes — Deep Analysis

There are **4 distinct Governor classes** in the codebase. Here's exactly what each one does and which one matters:

### 3.1 `command_center/governor.py` — THE PRODUCTION GOVERNOR ✅

- **Class:** `Governor` (line 85)
- **File:** `backend/app/command_center/governor.py` (630 lines)
- **Docstring:** *"The strategic decision-maker for NOVA Command Center."*
- **What it does:** Deep async analysis of objectives — categorization, risk detection, dependency analysis, complexity estimation, execution strategy, tool orchestration, strategic recommendations.
- **How it's used:**
  - `CommandCenter` (command_center/command_center.py:26) creates it directly
  - `CommandCenterFactory` (command_center/factory.py:9) aliases it as `RichGovernor`
  - **nova_web.py routes** (`/api/v1/nova-web/chat`, `/think`, etc.) access it via `comps.get("governor")` from CommandCenterFactory
  - **command_center routes** (`/api/v1/command-center/analyze`, `/plan`) use it via CommandCenter instance
- **This is the one that actually runs in production** when users hit `/api/v1/nova-web/chat`.

### 3.2 `command_center/orchestrator.py` — DEAD CODE / DUPLICATE ❌

- **Class:** `Governor` (line 17)
- **File:** `backend/app/command_center/orchestrator.py` (~60 lines)
- **What it does:** Minimal sync version — basic keyword matching, complexity by word count. Same class name, different implementation.
- **How it's used:**
  - Re-exported from `command_center/__init__.py` (line 14: `from .orchestrator import Governor, Orchestrator`)
  - The `Orchestrator` class takes a `Governor` param, but the factory wires the **rich** Governor (from governor.py), not this one
  - Only imported in tests (`test_command_center.py:41`)
- **Verdict:** Dead code. The `__init__.py` exports it but nobody uses the exported version. The factory and CommandCenter import directly from `governor.py`.

### 3.3 `autonomy/governor.py` — DIFFERENT CONCERN, DEAD ❌

- **Class:** `AutonomyGovernor` (line 12)
- **File:** `backend/app/autonomy/governor.py` (79 lines)
- **Docstring:** *"Controls the degree of autonomous behavior allowed."*
- **What it does:** Thread-safe concurrency limiter — controls autonomy levels (SUPERVISED, GUIDED, FULL), max concurrent actions, approval requirements.
- **How it's used:**
  - Created by `AutonomyManager` (autonomy/manager.py:33)
  - `AutonomyManager` is NOT wired in lifespan — it's created by `AutonomyFactory` which creates `AutonomyEngine`, not `AutonomyManager`
- **Verdict:** Dead code in practice. The autonomy routes use the factory-created engine, not this manager/governor combo.

### 3.4 `nova_os/governor.py` — DIFFERENT CONCERN, DEAD ❌

- **Class:** `NovaGovernor` (line 35)
- **File:** `backend/app/nova_os/governor.py` (198 lines)
- **Docstring:** *"Policy enforcement engine and resource governance manager."*
- **What it does:** Async policy enforcement — safety modes, resource limits, high-risk action approval, autonomy ceiling.
- **How it's used:**
  - Created by `NovaOSFactory` (nova_os/factory.py:59)
  - `NovaOSFactory` is NOT called in lifespan. The `nova_os/` module is never initialized.
- **Verdict:** Dead code. The entire `nova_os/` module exists as an unused abstraction layer.

### Governor Summary

| Governor | File | Lines | In lifespan? | In routes? | Verdict |
|----------|------|-------|-------------|------------|---------|
| `Governor` (command_center/governor.py) | command_center/governor.py | 630 | Indirectly via CommandCenterFactory | ✅ nova_web + command_center | **PRODUCTION** |
| `Governor` (command_center/orchestrator.py) | command_center/orchestrator.py | ~60 | NO | NO | Dead code |
| `AutonomyGovernor` | autonomy/governor.py | 79 | NO | NO | Dead code |
| `NovaGovernor` | nova_os/governor.py | 198 | NO | NO | Dead code |

---

## 4. All Backend Endpoints (grouped by section)

**Total: ~415 endpoints across 35 route modules + 2 root endpoints.**

### 4.1 Root (main.py)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/` | Returns project name, version, status | NO |
| GET | `/health` | Probes Postgres, Redis, ChromaDB, Ollama | NO |

### 4.2 Health (`/api/v1/health`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/api/v1/health` | Service health check | NO |

### 4.3 Agents (`/api/v1/agents`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/agents` | List agent definitions | NO |
| GET | `/agents/{id}` | Get agent by ID | NO |
| POST | `/agents` | Create agent definition | NO |
| PATCH | `/agents/{id}` | Update agent definition | NO |
| DELETE | `/agents/{id}` | Delete agent definition | NO |
| POST | `/agents/register` | Register agent definition | NO |
| GET | `/agents/health` | Agent health check | NO |
| GET | `/agents/capabilities` | Agent capabilities metadata | NO |
| POST | `/agents/runtime/dispatch` | Dispatch task to AgentRuntime → LLMAgent → Ollama | **YES** |
| POST | `/agents/runtime/coordinate` | Multi-agent coordination via AgentRuntime | **YES** |
| GET | `/agents/runtime/metrics` | Runtime metrics | NO |
| GET | `/agents/runtime/traces` | Runtime execution traces | NO |
| GET | `/agents/runtime/scheduler` | Scheduler status | NO |
| POST | `/agents/runtime/cancel/{task_id}` | Cancel scheduled task | NO |

### 4.4 Events (`/api/v1/events`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| POST | `/events/publish` | Publish event to bus | NO |
| POST | `/events/replay` | Replay events from history | NO |
| GET | `/events` | List events with filtering | NO |
| GET | `/events/statistics` | Event bus statistics | NO |
| GET | `/events/metrics` | Event metrics | NO |
| GET | `/events/health` | Event bus health | NO |
| GET | `/events/traces` | Event traces | NO |
| GET | `/events/{id}` | Get event by ID | NO |

### 4.5 Goals (`/api/v1/goals`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/goals/{user_id}` | List user goals | NO |
| POST | `/goals/{user_id}` | Create a goal | NO |
| GET | `/goals/{user_id}/detail/{goal_id}` | Get goal details | NO |
| PATCH | `/goals/{user_id}/detail/{goal_id}` | Update a goal | NO |
| DELETE | `/goals/{user_id}/detail/{goal_id}` | Delete a goal | NO |
| GET | `/goals/{user_id}/next-actions` | Get next action recommendations | NO |
| GET | `/goals/{user_id}/blocked` | Get blocked goals | NO |
| GET | `/goals/{user_id}/analyze` | Analyze goal progress (rule-based) | NO |

### 4.6 Kernel (`/api/v1/kernel`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| POST | `/kernel/execute` | **Core AI endpoint** — CognitiveEngine + LLMAgent → Ollama qwen2.5-coder:7b | **YES** |

### 4.7 Learning (`/api/v1/learning`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| POST | `/learning/extract` | Extract knowledge from execution data | NO |
| POST | `/learning/search` | Search knowledge artifacts | NO |
| GET | `/learning/artifacts` | List learning artifacts | NO |
| GET | `/learning/artifacts/{id}` | Get artifact by ID | NO |
| DELETE | `/learning/artifacts/{id}` | Delete artifact | NO |
| POST | `/learning/consolidate` | Consolidate duplicate artifacts | NO |
| GET | `/learning/stats` | Learning engine statistics | NO |

### 4.8 Memory (`/api/v1/memory`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/memory/{session_id}` | Get conversation history | NO |

### 4.9 Models (`/api/v1/models`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| POST | `/models/chat` | **Direct LLM call** — ModelGateway → Ollama/OpenAI | **YES** |
| GET | `/models/health` | Model provider health | NO |
| GET | `/models/metrics` | Model gateway metrics | NO |
| GET | `/models/list` | List available models | NO |
| GET | `/models/providers` | List model providers | NO |
| GET | `/models/cache/stats` | Response cache statistics | NO |
| DELETE | `/models/cache` | Clear response cache | NO |
| GET | `/models/traces` | Model gateway traces | NO |

### 4.10 Profile (`/api/v1/profile`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/profile/{user_id}` | Get user identity profile | NO |

### 4.11 RAG (`/api/v1/rag`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| POST | `/rag/query` | Full RAG pipeline (embedding + retrieval + HyDE) | **EMBEDDINGS** |
| POST | `/rag/retrieve` | Retrieval-only vector similarity | **EMBEDDINGS** |
| POST | `/rag/index` | Index documents with embeddings | **EMBEDDINGS** |
| POST | `/rag/reindex` | Re-index documents | **EMBEDDINGS** |
| GET | `/rag/health` | RAG engine health | NO |
| GET | `/rag/metrics` | RAG metrics | NO |
| GET | `/rag/traces` | RAG traces | NO |
| GET | `/rag/statistics` | RAG document/chunk statistics | NO |

### 4.12 Scheduler (`/api/v1/scheduler`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| POST | `/scheduler/jobs` | Schedule a new job | NO |
| GET | `/scheduler/jobs` | List scheduled jobs | NO |
| GET | `/scheduler/jobs/{id}` | Get job by ID | NO |
| DELETE | `/scheduler/jobs/{id}` | Delete a job | NO |
| POST | `/scheduler/jobs/{id}/execute` | Execute job immediately | NO |
| POST | `/scheduler/jobs/{id}/cancel` | Cancel a job | NO |
| POST | `/scheduler/jobs/{id}/pause` | Pause a job | NO |
| POST | `/scheduler/jobs/{id}/resume` | Resume a paused job | NO |
| POST | `/scheduler/jobs/{id}/retry` | Retry a failed job | NO |
| POST | `/scheduler/run-pending` | Run all pending jobs | NO |
| GET | `/scheduler/statistics` | Scheduler statistics | NO |
| GET | `/scheduler/metrics` | Scheduler metrics | NO |
| GET | `/scheduler/traces` | Scheduler traces | NO |
| GET | `/scheduler/health` | Scheduler health | NO |

### 4.13 Tasks (`/api/v1/tasks`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| POST | `/tasks` | Create a task | NO |
| GET | `/tasks` | List tasks with filters | NO |
| GET | `/tasks/{id}` | Get task by ID | NO |
| PATCH | `/tasks/{id}` | Update a task | NO |
| DELETE | `/tasks/{id}` | Delete a task | NO |
| POST | `/tasks/{id}/advance` | Advance task step | NO |
| POST | `/tasks/{id}/transition` | Transition task state | NO |

### 4.14 Knowledge Graph (`/api/v1/knowledge-graph`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| POST | `/knowledge-graph/entities` | Create entity | NO |
| GET | `/knowledge-graph/entities` | List entities | NO |
| GET | `/knowledge-graph/entities/{id}` | Get entity | NO |
| PUT | `/knowledge-graph/entities/{id}` | Update entity | NO |
| DELETE | `/knowledge-graph/entities/{id}` | Delete entity | NO |
| POST | `/knowledge-graph/relationships` | Create relationship | NO |
| GET | `/knowledge-graph/relationships` | List relationships | NO |
| GET | `/knowledge-graph/relationships/{id}` | Get relationship | NO |
| DELETE | `/knowledge-graph/relationships/{id}` | Delete relationship | NO |
| GET | `/knowledge-graph/entities/{id}/relationships` | Get entity relationships | NO |
| POST | `/knowledge-graph/query/neighborhood` | Graph traversal | NO |
| POST | `/knowledge-graph/query/shortest-path` | Shortest path | NO |
| POST | `/knowledge-graph/query/connected` | Find connected entities | NO |
| POST | `/knowledge-graph/search` | Search graph entities | NO |
| POST | `/knowledge-graph/extract` | Entity extraction from text | **POSSIBLE** |
| POST | `/knowledge-graph/merge` | Merge duplicate entities | NO |
| GET | `/knowledge-graph/validate` | Validate graph integrity | NO |
| GET | `/knowledge-graph/types` | List entity/relationship types | NO |

### 4.15 Tools (`/api/v1/tools`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/tools` | List registered tools | NO |
| GET | `/tools/metrics` | Tool execution metrics | NO |
| GET | `/tools/traces` | Tool execution traces | NO |
| GET | `/tools/{id}` | Get tool by ID | NO |
| POST | `/tools/register` | Register a new tool | NO |
| DELETE | `/tools/{id}` | Unregister a tool | NO |
| POST | `/tools/{id}/execute` | Execute a registered tool | NO |
| GET | `/tools/{id}/health` | Tool health check | NO |

### 4.16 Vector Memory (`/api/v1/vector-memory`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| POST | `/vector-memory/store` | Store with embedding | **EMBEDDINGS** |
| POST | `/vector-memory/search` | Vector similarity search | **EMBEDDINGS** |
| POST | `/vector-memory/similarity` | Direct embedding similarity | **EMBEDDINGS** |
| POST | `/vector-memory/consolidate` | Deduplicate vectors | NO |
| POST | `/vector-memory/reindex` | Re-embed vectors | **EMBEDDINGS** |
| DELETE | `/vector-memory/{id}` | Delete a vector | NO |
| GET | `/vector-memory/statistics` | Statistics | NO |
| GET | `/vector-memory/health` | Health check | NO |
| GET | `/vector-memory/metrics` | Metrics | NO |
| GET | `/vector-memory/traces` | Traces | NO |

### 4.17 Workflows (`/api/v1/workflows`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| POST | `/workflows` | Create workflow definition | NO |
| GET | `/workflows` | List workflows | NO |
| GET | `/workflows/{id}` | Get workflow | NO |
| PUT | `/workflows/{id}` | Update workflow | NO |
| DELETE | `/workflows/{id}` | Delete workflow | NO |
| POST | `/workflows/executions` | Create execution | NO |
| GET | `/workflows/executions` | List executions | NO |
| GET | `/workflows/executions/{id}` | Get execution | NO |
| POST | `/workflows/executions/{id}/start` | Start execution | NO |
| POST | `/workflows/executions/{id}/action` | Pause/resume/cancel/rollback | NO |
| GET | `/workflows/executions/{id}/events` | Get execution events | NO |
| POST | `/workflows/import` | Import workflow | NO |
| GET | `/workflows/export/{id}` | Export workflow | NO |
| GET | `/workflows/templates` | List templates | NO |
| GET | `/workflows/metrics` | Metrics | NO |
| GET | `/workflows/statistics` | Statistics | NO |
| GET | `/workflows/health` | Health | NO |
| GET | `/workflows/traces` | Traces | NO |

### 4.18 Observability (`/api/v1/observability`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/observability/health` | Health | NO |
| GET | `/observability/readiness` | Readiness | NO |
| GET | `/observability/liveness` | Liveness | NO |
| GET | `/observability/metrics` | Metrics | NO |
| GET | `/observability/traces` | Traces | NO |
| GET | `/observability/logs` | Logs | NO |
| GET | `/observability/diagnostics` | Diagnostics | NO |
| GET | `/observability/alerts` | Alerts | NO |
| GET | `/observability/statistics` | Statistics | NO |
| GET | `/observability/export/prometheus` | Export Prometheus | NO |
| GET | `/observability/export/json` | Export JSON | NO |
| GET | `/observability/export/csv` | Export CSV | NO |

### 4.19 Plugins (`/api/v1/plugins`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/plugins/` | List plugins | NO |
| GET | `/plugins/health` | Health | NO |
| GET | `/plugins/statistics` | Statistics | NO |
| GET | `/plugins/{id}` | Get plugin | NO |
| POST | `/plugins/` | Register plugin | NO |
| DELETE | `/plugins/{id}` | Unregister plugin | NO |
| POST | `/plugins/{id}/enable` | Enable plugin | NO |
| POST | `/plugins/{id}/disable` | Disable plugin | NO |
| POST | `/plugins/{id}/execute` | Execute plugin | NO |
| GET | `/plugins/hooks/list` | List hooks | NO |
| GET | `/plugins/hooks/statistics` | Hook statistics | NO |
| GET | `/plugins/sandbox/stats` | Sandbox stats | NO |
| GET | `/plugins/events/recent` | Recent events | NO |

### 4.20 Security (`/api/v1/security`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/security/health` | Health | NO |
| GET | `/security/headers` | Security headers | NO |
| GET | `/security/statistics` | Statistics | NO |
| POST | `/security/auth/register` | User registration | NO |
| POST | `/security/auth/login` | User authentication | NO |
| POST | `/security/auth/token/verify` | Token verification | NO |
| POST | `/security/auth/token/revoke` | Token revocation | NO |
| POST | `/security/api-keys` | Create API key | NO |
| GET | `/security/api-keys/{user_id}` | List API keys | NO |
| DELETE | `/security/api-keys/{id}` | Revoke API key | NO |
| GET | `/security/audit` | Audit log | NO |
| GET | `/security/rbac/roles` | List RBAC roles | NO |
| POST | `/security/rbac/check` | Check permission | NO |

### 4.21 Database (`/api/v1/database`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/database/health` | Database health | NO |
| GET | `/database/statistics` | Statistics | NO |
| GET | `/database/migrations` | Migration status | NO |
| GET | `/database/schema` | Schema info | NO |
| GET | `/database/metrics` | Metrics | NO |
| GET | `/database/traces` | Traces | NO |

### 4.22 Deployment (`/api/v1/deployment`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/deployment/health` | Health | NO |
| GET | `/deployment/readiness` | Readiness | NO |
| GET | `/deployment/liveness` | Liveness | NO |
| GET | `/deployment/environment` | Environment variables | NO |
| GET | `/deployment/configuration` | Configuration | NO |
| GET | `/deployment/diagnostics` | Diagnostics | NO |
| GET | `/deployment/metrics` | Metrics | NO |
| GET | `/deployment/statistics` | Statistics | NO |

### 4.23 Scaling (`/api/v1/scaling`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/scaling/health` | Health | NO |
| GET | `/scaling/metrics` | Metrics | NO |
| GET | `/scaling/statistics` | Statistics | NO |
| GET | `/scaling/workers` | Worker pool status | NO |
| GET | `/scaling/queues` | Queue status | NO |
| GET | `/scaling/cache` | Cache statistics | NO |
| GET | `/scaling/resources` | Resource utilization | NO |
| POST | `/scaling/scale-up` | Scale up workers | NO |
| POST | `/scaling/scale-down` | Scale down workers | NO |
| POST | `/scaling/cache/clear` | Clear cache | NO |

### 4.24 Future (`/api/v1/future`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/future/features` | Feature flags | NO |
| GET | `/future/experiments` | Experiments | NO |
| GET | `/future/capabilities` | Capabilities | NO |
| GET | `/future/compatibility` | Compatibility report | NO |
| GET | `/future/deprecations` | Deprecations | NO |
| GET | `/future/roadmap` | Roadmap | NO |
| GET | `/future/metrics` | Metrics | NO |
| GET | `/future/statistics` | Statistics | NO |

### 4.25 Integration (`/api/v1/integration`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/integration/health` | Unified health | NO |
| GET | `/integration/status` | Status | NO |
| GET | `/integration/components` | List components | NO |
| GET | `/integration/dependencies` | Dependency graph | NO |
| GET | `/integration/diagnostics` | Diagnostics | NO |
| GET | `/integration/compatibility` | Compatibility report | NO |
| GET | `/integration/metrics` | Metrics | NO |
| GET | `/integration/traces` | Traces | NO |
| POST | `/integration/validate` | Validate integrations | NO |
| POST | `/integration/reinitialize` | Reinitialize components | NO |

### 4.26 Performance (`/api/v1/performance`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/performance/health` | Health | NO |
| GET | `/performance/profile` | Profiling sessions | NO |
| GET | `/performance/benchmarks` | Benchmark results | NO |
| GET | `/performance/diagnostics` | Diagnostics | NO |
| GET | `/performance/recommendations` | Optimization recommendations | NO |
| GET | `/performance/metrics` | Metrics | NO |
| GET | `/performance/traces` | Traces | NO |
| POST | `/performance/profile/start` | Start profiling | NO |
| POST | `/performance/profile/stop` | Stop profiling | NO |
| POST | `/performance/benchmark/run` | Run benchmark | NO |

### 4.27 Resilience (`/api/v1/resilience`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/resilience/health` | Health | NO |
| GET | `/resilience/status` | Status | NO |
| GET | `/resilience/circuit-breakers` | Circuit breaker status | NO |
| GET | `/resilience/retries` | Retry statistics | NO |
| GET | `/resilience/failovers` | Failover events | NO |
| GET | `/resilience/recoveries` | Recovery history | NO |
| GET | `/resilience/diagnostics` | Diagnostics | NO |
| GET | `/resilience/metrics` | Metrics | NO |
| GET | `/resilience/traces` | Traces | NO |
| POST | `/resilience/reset` | Reset state | NO |
| POST | `/resilience/recover` | Recover component | NO |

### 4.28 Autonomy (`/api/v1/autonomy`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/autonomy/status` | Status | NO |
| GET | `/autonomy/objectives` | List objectives | NO |
| GET | `/autonomy/recommendations` | List recommendations | NO |
| GET | `/autonomy/reflections` | List reflections | NO |
| GET | `/autonomy/policies` | List policies | NO |
| GET | `/autonomy/metrics` | Metrics | NO |
| GET | `/autonomy/traces` | Traces | NO |
| POST | `/autonomy/evaluate` | Evaluate objectives (rule-based) | NO |
| POST | `/autonomy/recommend` | Generate recommendations (rule-based) | NO |
| POST | `/autonomy/approve` | Approve recommendation | NO |
| POST | `/autonomy/reject` | Reject recommendation | NO |

### 4.29 Enterprise (`/api/v1/enterprise`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/enterprise/status` | Status | NO |
| GET | `/enterprise/organizations` | List organizations | NO |
| GET | `/enterprise/tenants` | List tenants | NO |
| GET | `/enterprise/workspaces` | List workspaces | NO |
| GET | `/enterprise/teams` | List teams | NO |
| GET | `/enterprise/roles` | List roles | NO |
| GET | `/enterprise/permissions` | List permissions | NO |
| GET | `/enterprise/policies` | List policies | NO |
| GET | `/enterprise/licenses` | License info | NO |
| GET | `/enterprise/quotas` | Quota info | NO |
| GET | `/enterprise/audit` | Audit events | NO |
| GET | `/enterprise/metrics` | Metrics | NO |
| GET | `/enterprise/traces` | Traces | NO |
| POST | `/enterprise/organizations` | Create organization | NO |
| POST | `/enterprise/workspaces` | Create workspace | NO |
| POST | `/enterprise/teams` | Create team | NO |
| POST | `/enterprise/roles` | Create role | NO |
| POST | `/enterprise/policies` | Create policy | NO |

### 4.30 NOVA OS (`/api/v1/nova-os`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/nova-os/status` | Status | NO |
| GET | `/nova-os/health` | Health | NO |
| GET | `/nova-os/runtime` | Runtime components | NO |
| GET | `/nova-os/lifecycle` | Lifecycle state | NO |
| GET | `/nova-os/components` | List components | NO |
| GET | `/nova-os/intelligence` | Intelligence metrics | NO |
| GET | `/nova-os/orchestration` | Orchestration status | NO |
| GET | `/nova-os/diagnostics` | Diagnostics | NO |
| GET | `/nova-os/metrics` | Metrics | NO |
| GET | `/nova-os/traces` | Traces | NO |
| GET | `/nova-os/synchronization` | Sync status | NO |
| GET | `/nova-os/statistics` | Statistics | NO |
| POST | `/nova-os/boot` | Boot NOVA OS | NO |
| POST | `/nova-os/synchronize` | Synchronize | NO |
| POST | `/nova-os/optimize` | Optimize | NO |
| POST | `/nova-os/recover` | Recover | NO |
| POST | `/nova-os/shutdown` | Shutdown | NO |

### 4.31 Assistant (`/api/v1/assistant`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/assistant/status` | Status | NO |
| GET | `/assistant/context` | Session context | NO |
| GET | `/assistant/memory` | Memory retrieval | NO |
| GET | `/assistant/goals` | List goals | NO |
| GET | `/assistant/tasks` | List tasks | NO |
| GET | `/assistant/workflows` | List workflows | NO |
| GET | `/assistant/metrics` | Metrics | NO |
| GET | `/assistant/traces` | Traces | NO |
| POST | `/assistant/chat` | **RULE-BASED** keyword detection + canned responses | NO |
| POST | `/assistant/execute` | Rule-based execution with approval | NO |
| POST | `/assistant/plan` | Rule-based planning | NO |
| POST | `/assistant/research` | Rule-based research | NO |
| POST | `/assistant/reason` | Rule-based reasoning | NO |
| POST | `/assistant/approve` | Approval action | NO |
| POST | `/assistant/reject` | Rejection action | NO |

### 4.32 Constitution (`/api/v1/constitution`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/constitution/status` | Status | NO |
| GET | `/constitution/mission` | Get mission | NO |
| POST | `/constitution/mission` | Set mission | NO |
| GET | `/constitution/values` | List values | NO |
| POST | `/constitution/values` | Add value | NO |
| GET | `/constitution/priorities` | List priorities | NO |
| POST | `/constitution/priorities` | Add priority | NO |
| GET | `/constitution/objectives` | List objectives | NO |
| POST | `/constitution/objectives` | Add objective | NO |
| GET | `/constitution/backlog` | List backlog | NO |
| POST | `/constitution/backlog` | Add backlog item | NO |
| GET | `/constitution/approvals/pending` | Pending approvals | NO |
| POST | `/constitution/approvals/request` | Request approval | NO |
| POST | `/constitution/approvals/{id}/approve` | Approve action | NO |
| POST | `/constitution/approvals/{id}/reject` | Reject action | NO |
| GET | `/constitution/policies` | Get policies | NO |
| GET | `/constitution/autonomy` | Get autonomy level | NO |
| POST | `/constitution/autonomy/level` | Set autonomy level | NO |
| GET | `/constitution/lifecycle` | Get lifecycle | NO |

### 4.33 User Profile (`/api/v1/profile`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/profile/status` | Profile system status | NO |
| POST | `/profile/users` | Create user profile | NO |
| GET | `/profile/users/{id}` | Get user profile | NO |
| PUT | `/profile/users/{id}` | Update user profile | NO |
| GET | `/profile/users/{id}/preferences` | Get preferences | NO |
| POST | `/profile/users/{id}/preferences` | Set preference | NO |
| GET | `/profile/projects` | List projects | NO |
| POST | `/profile/projects` | Create project | NO |
| GET | `/profile/objectives` | List objectives | NO |
| POST | `/profile/objectives` | Create objective | NO |
| GET | `/profile/priorities` | List priorities | NO |
| POST | `/profile/priorities` | Create priority | NO |
| GET | `/profile/history` | Get history | NO |
| GET | `/profile/roadmaps` | List roadmaps | NO |
| POST | `/profile/roadmaps` | Create roadmap | NO |

### 4.34 Autonomy System (`/api/v1/autonomy-system`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/autonomy-system/status` | Status | NO |
| GET | `/autonomy-system/autonomy` | Get autonomy level | NO |
| POST | `/autonomy-system/autonomy/level` | Set level | NO |
| GET | `/autonomy-system/autonomy/capabilities` | Get capabilities | NO |
| POST | `/autonomy-system/objectives/analyze` | Analyze objective (rule-based) | NO |
| POST | `/autonomy-system/objectives` | Create objective | NO |
| GET | `/autonomy-system/objectives` | List objectives | NO |
| POST | `/autonomy-system/projects` | Create project | NO |
| GET | `/autonomy-system/projects` | List projects | NO |
| POST | `/autonomy-system/roadmaps` | Create roadmap | NO |
| GET | `/autonomy-system/roadmaps` | List roadmaps | NO |
| GET | `/autonomy-system/recommendations` | List recommendations | NO |
| POST | `/autonomy-system/recommendations` | Create recommendation | NO |
| POST | `/autonomy-system/recommendations/{id}/accept` | Accept recommendation | NO |
| GET | `/autonomy-system/optimization` | List optimizations | NO |
| GET | `/autonomy-system/self-improvement` | List improvements | NO |
| POST | `/autonomy-system/self-improvement` | Identify improvement | NO |
| POST | `/autonomy-system/self-improvement/{id}/approve` | Approve improvement | NO |
| GET | `/autonomy-system/approvals/pending` | Pending approvals | NO |
| POST | `/autonomy-system/approvals/request` | Request approval | NO |
| POST | `/autonomy-system/approvals/{id}/approve` | Approve action | NO |
| POST | `/autonomy-system/delegation` | Delegate task | NO |
| GET | `/autonomy-system/delegation` | List delegations | NO |
| POST | `/autonomy-system/research` | Submit research | NO |
| GET | `/autonomy-system/research` | List research | NO |

### 4.35 Command Center (`/api/v1/command-center`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/command-center/status` | Status | NO |
| GET | `/command-center/lifecycle` | Lifecycle state | NO |
| GET | `/command-center/objectives` | List objectives | NO |
| POST | `/command-center/objectives` | Create objective | NO |
| GET | `/command-center/objectives/active` | List active objectives | NO |
| GET | `/command-center/objectives/backlog` | List backlog objectives | NO |
| POST | `/command-center/objectives/{id}/complete` | Complete objective | NO |
| POST | `/command-center/objectives/{id}/progress` | Update progress | NO |
| GET | `/command-center/projects` | List projects | NO |
| POST | `/command-center/projects` | Create project | NO |
| POST | `/command-center/projects/{id}/complete` | Complete project | NO |
| GET | `/command-center/roadmap` | List roadmaps | NO |
| POST | `/command-center/roadmap` | Create roadmap | NO |
| GET | `/command-center/backlog` | List backlog | NO |
| POST | `/command-center/backlog` | Add backlog item | NO |
| POST | `/command-center/backlog/{id}/approve` | Approve backlog item | NO |
| GET | `/command-center/milestones` | List milestones | NO |
| POST | `/command-center/milestones` | Create milestone | NO |
| POST | `/command-center/milestones/{id}/complete` | Complete milestone | NO |
| GET | `/command-center/approvals/pending` | Pending approvals | NO |
| POST | `/command-center/approvals/request` | Request approval | NO |
| POST | `/command-center/approvals/{id}/approve` | Approve action | NO |
| POST | `/command-center/approvals/{id}/reject` | Reject action | NO |
| POST | `/command-center/analyze` | **RULE-BASED** Governor keyword analysis | NO |
| POST | `/command-center/plan` | **RULE-BASED** Governor rule-based planning | NO |
| POST | `/command-center/orchestrate` | **RULE-BASED** Orchestrator logic | NO |
| GET | `/command-center/decisions` | List decisions | NO |
| GET | `/command-center/recommendations` | List recommendations | NO |
| POST | `/command-center/recommendations` | Create recommendation | NO |
| POST | `/command-center/recommendations/{id}/accept` | Accept recommendation | NO |
| GET | `/command-center/optimization` | List optimizations | NO |
| POST | `/command-center/optimization` | Create optimization | NO |
| GET | `/command-center/metrics` | Metrics | NO |
| GET | `/command-center/traces` | Traces | NO |

### 4.36 NOVA Web (`/api/v1/nova-web`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/nova-web/dashboard` | Dashboard aggregation | NO |
| POST | `/nova-web/chat` | **RULE-BASED** keyword command + Governor keyword analysis | NO |
| GET | `/nova-web/objectives` | List objectives | NO |
| GET | `/nova-web/projects` | List projects | NO |
| GET | `/nova-web/roadmaps` | List roadmaps | NO |
| GET | `/nova-web/tasks` | List tasks | NO |
| GET | `/nova-web/backlog` | List backlog | NO |
| GET | `/nova-web/approvals` | List pending approvals | NO |
| POST | `/nova-web/approvals/{id}/approve` | Approve item | NO |
| POST | `/nova-web/approvals/{id}/reject` | Reject item | NO |
| GET | `/nova-web/recommendations` | List recommendations | NO |
| POST | `/nova-web/recommendations/{id}/accept` | Accept recommendation | NO |
| GET | `/nova-web/memory` | Memory status | NO |
| GET | `/nova-web/observability` | Observability data | NO |
| GET | `/nova-web/tools` | Tools status | NO |
| POST | `/nova-web/roadmaps` | Create roadmap | NO |
| POST | `/nova-web/backlog` | Create backlog item | NO |
| POST | `/nova-web/bootstrap` | Bootstrap NOVA self-project | NO |
| GET | `/nova-web/daily` | Daily assessment (rule-based) | NO |
| GET | `/nova-web/self-optimize` | Self-optimization (rule-based) | NO |
| POST | `/nova-web/think` | **RULE-BASED** Governor keyword-based reasoning | NO |
| GET | `/nova-web/status` | Unified status | NO |

### 4.37 API Documentation (`/api/v1/api/docs`)

| Method | Path | What it does | AI? |
|--------|------|-------------|-----|
| GET | `/api/docs/catalog` | Endpoint catalog | NO |
| GET | `/api/docs/openapi-spec` | OpenAPI JSON spec | NO |
| GET | `/api/docs/info` | Documentation info | NO |
| GET | `/api/docs/endpoints-by-tag/{tag}` | Endpoints filtered by tag | NO |

---

## 5. AI vs Rule-Based — Honest Classification

### 5.1 Endpoints that use REAL AI (LLM)

| Endpoint | How it works | Model |
|----------|-------------|-------|
| `POST /api/v1/kernel/execute` | CognitiveEngine → LLMAgent → ModelGateway → Ollama | qwen2.5-coder:7b |
| `POST /api/v1/models/chat` | Direct ModelGateway.chat() → Ollama/OpenAI | Configurable |
| `POST /api/v1/agents/runtime/dispatch` | AgentRuntime → LLMAgent → ModelGateway → Ollama | Configurable |

### 5.2 Endpoints that use EMBEDDINGS (AI-adjacent)

| Endpoint | How it works |
|----------|-------------|
| `POST /api/v1/rag/query` | Embedding + vector retrieval + HyDE query rewriting |
| `POST /api/v1/rag/retrieve` | Vector similarity search via embeddings |
| `POST /api/v1/rag/index` | Document embedding + indexing |
| `POST /api/v1/rag/reindex` | Re-embedding documents |
| `POST /api/v1/vector-memory/store` | Store with embedding generation |
| `POST /api/v1/vector-memory/search` | Vector similarity search |
| `POST /api/v1/vector-memory/similarity` | Direct embedding similarity |
| `POST /api/v1/vector-memory/reindex` | Re-embed vectors |

### 5.3 Endpoints that are RULE-BASED but present themselves as AI

| Endpoint | What it actually does |
|----------|----------------------|
| `POST /api/v1/nova-web/chat` | Keyword matching ("create project" → project creation, "analyze" → Governor keyword analysis). **No LLM call.** |
| `POST /api/v1/nova-web/think` | Governor keyword categorization + 10-step reasoning template. **No LLM call.** |
| `POST /api/v1/command-center/analyze` | Governor keyword matching analysis. **No LLM call.** |
| `POST /api/v1/command-center/plan` | Governor rule-based planning. **No LLM call.** |
| `POST /api/v1/command-center/orchestrate` | Orchestrator rule-based logic. **No LLM call.** |
| `POST /api/v1/assistant/chat` | Keyword-based intent detection + canned response templates. **No LLM call.** |
| `POST /api/v1/assistant/execute` | Rule-based execution with approval flow |
| `POST /api/v1/assistant/plan` | Rule-based planning |
| `POST /api/v1/assistant/research` | Rule-based research |
| `POST /api/v1/assistant/reason` | Rule-based reasoning |
| `POST /api/v1/autonomy/evaluate` | Rule-based objective evaluation |
| `POST /api/v1/autonomy/recommend` | Rule-based recommendation generation |
| `POST /api/v1/autonomy-system/objectives/analyze` | Rule-based keyword matching |

### 5.4 The core problem

**The chat endpoint that the frontend actually uses (`/api/v1/nova-web/chat`) does NOT call any LLM.** It does keyword matching. The real LLM endpoints exist (`/kernel/execute`, `/models/chat`) but the frontend's primary chat interface doesn't use them.

---

## 6. Frontend Module Status — What's Connected, What's Broken

### 6.1 Frontend Tech Stack

- **Framework:** Next.js 14.2.0 (App Router)
- **Language:** TypeScript 5.5
- **State:** Zustand 4.5
- **Styling:** Tailwind CSS 3.4
- **API Client:** Custom `NovaAPI` class (`lib/api.ts`) + `NovaWebAPI` (`lib/nova-api.ts`)

### 6.2 Pages that work (endpoint exists and is reachable)

| Page | File | Endpoint Called | Status |
|------|------|----------------|--------|
| NOVA (Chat + Dashboard) | `app/nova/page.tsx` | `POST /nova-web/chat`, `GET /nova-web/dashboard` | ✅ Connected |
| Agents | `app/agents/page.tsx` | `GET /api/v1/agents` | ✅ Connected |
| Tasks | `app/tasks/page.tsx` | `GET /api/v1/tasks` | ✅ Connected |
| Workflows | `app/workflows/page.tsx` | `GET /api/v1/workflows` | ✅ Connected |
| Models | `app/models/page.tsx` | `GET /api/v1/models/list` | ✅ Connected |
| Scheduler | `app/scheduler/page.tsx` | `GET /api/v1/scheduler/jobs` | ✅ Connected |
| Deployment | `app/deployment/page.tsx` | `GET /api/v1/deployment/health` | ✅ Connected |
| Tools | `app/tools/page.tsx` | `GET /api/v1/tools` | ✅ Connected |
| RAG | `app/rag/page.tsx` | `GET /api/v1/rag/statistics` | ✅ Connected |
| Vector Memory | `app/vector-memory/page.tsx` | `GET /api/v1/vector-memory/statistics` | ✅ Connected |
| Events | `app/events/page.tsx` | `GET /api/v1/events` | ✅ Connected |
| Plugins | `app/plugins/page.tsx` | `GET /api/v1/plugins` | ✅ Connected |
| Knowledge | `app/knowledge/page.tsx` | `GET /api/v1/knowledge-graph/entities` | ✅ Connected |
| Learning | `app/learning/page.tsx` | `GET /api/v1/learning/stats` | ✅ Connected |
| Observability | `app/observability/page.tsx` | `GET /api/v1/observability/health` | ✅ Connected |
| Security | `app/security/page.tsx` | `GET /api/v1/security/audit` | ✅ Connected |
| Scaling | `app/scaling/page.tsx` | `GET /api/v1/scaling/health` | ✅ Connected |
| Enterprise | `app/enterprise/page.tsx` | `GET /api/v1/enterprise/status` | ✅ Connected |
| Dashboard | `app/dashboard/page.tsx` | `GET /api/v1/health` | ✅ Connected |
| Chat (standalone) | `app/chat/page.tsx` | `POST /api/v1/nova-web/chat` | ✅ Connected |
| Memory | `app/memory/page.tsx` | `GET /api/v1/nova-web/memory` | ✅ Connected |
| Autonomy | `app/autonomy/page.tsx` | `GET /api/v1/autonomy/status` | ✅ Connected |
| Reasoning | `app/reasoning/page.tsx` | `GET /api/v1/observability/traces` | ✅ Connected |
| Planning | `app/planning/page.tsx` | `GET /api/v1/autonomy/objectives` | ⚠️ Response shape mismatch |
| Execution | `app/execution/page.tsx` | `GET /api/v1/scheduler/jobs` | ✅ Connected |
| Projects | `app/projects/page.tsx` | `GET /nova-web/projects` | ✅ Connected |
| Roadmaps | `app/roadmaps/page.tsx` | `GET /nova-web/roadmaps` | ✅ Connected |
| Backlog | `app/backlog/page.tsx` | `GET /nova-web/backlog` | ✅ Connected |
| Approvals | `app/approvals/page.tsx` | `GET /nova-web/approvals` | ✅ Connected |
| Profile | `app/profile/page.tsx` | `GET /api/v1/profile/status` | ✅ Connected |
| Admin | `app/admin/page.tsx` | `GET /api/v1/deployment/environment` | ⚠️ Response shape mismatch |

### 6.3 Broken frontend → backend connections

| Page | Problem | Severity |
|------|---------|----------|
| `app/goals/page.tsx` | Calls `GET /api/v1/goals` but backend requires `/{user_id}` — returns 404 | 🔴 HIGH |
| `app/planning/page.tsx` | Backend returns `{success: true, data: [...]}` but frontend expects plain array | 🟡 MEDIUM |
| `app/admin/page.tsx` | Backend returns `{success: true, data: {variables, count}}` but frontend expects `{environment, version}` | 🟡 MEDIUM |
| `app/auth/page.tsx` | Login/signup form with no API calls — purely cosmetic | 🟡 MEDIUM |

### 6.4 Broken API client methods (lib/api.ts)

| Method | Problem |
|--------|---------|
| `goals.analyze(uid)` | Calls `GET /goals/{uid}/analyze` — route exists but requires user_id format match |
| `enterprise.metrics()` | Calls `GET /enterprise/metrics` — **route does not exist** |
| `enterprise.audit()` | Calls `GET /enterprise/audit` — **route does not exist** |

### 6.5 Broken API client methods (lib/nova-api.ts)

| Method | Problem |
|--------|---------|
| `novaWeb.createProject()` | Calls `POST /nova-web/projects` — **only GET exists** |
| `novaWeb.approvalHistory()` | Calls `GET /nova-web/approvals/history` — **route does not exist** |

### 6.6 Legacy services (services/index.ts) — ALL BROKEN

The entire `services/index.ts` file is dead code. It contains 15+ broken endpoint references. No active page imports from it. It should be deleted.

### 6.7 WebSocket — Infrastructure exists, completely unused

- `hooks/index.ts` defines `useWebSocket()` and `useEventSource()` hooks
- `next.config.js` configures `NEXT_PUBLIC_WS_URL = ws://localhost:8000`
- Tests mock `WebSocket` and `EventSource`
- **No page or component actually uses these hooks**
- **No WebSocket or SSE endpoint exists in the backend**
- The `ws://localhost:8000` configuration is dead

### 6.8 Architectural issues in frontend

1. **Two parallel API clients:** `lib/api.ts` (NovaAPI) and `services/index.ts` (legacy). Pages use NovaAPI. Legacy is dead.
2. **Two pages bypass the API client:** `chat/page.tsx` and `memory/page.tsx` use raw `fetch()` with their own `API_BASE`, duplicating base URL logic.
3. **Response shape mismatch:** Many backend endpoints wrap responses in `{success: true, data: ...}` but frontend sometimes expects unwrapped data.
4. **No error handling:** Most pages use `useApi()` which doesn't handle errors gracefully — a failed fetch shows nothing.

---

## 7. Honest Completeness Assessment

### What's COMPLETE and WORKING

- **Backend infrastructure:** Event bus, scheduler, DB, Redis, ChromaDB, Ollama — all properly initialized with degraded mode
- **35 API routers:** All mounted, all returning data
- **CRUD operations:** Goals, tasks, workflows, agents, tools, plugins, knowledge graph, etc. — all functional
- **Model Gateway:** Ollama provider connected, can generate text
- **RAG pipeline:** Embeddings, indexing, retrieval — functional
- **Vector memory:** Store, search, similarity — functional
- **Event system:** Pub/sub, dispatcher, replay — functional
- **Security engine:** Auth, RBAC, API keys, tokens — functional
- **Observability:** Metrics, tracing, logging, health — functional
- **Frontend pages:** 30+ pages connected to real endpoints

### What's HALF-DONE

- **`/nova-web/chat`:** The main user-facing chat endpoint uses keyword matching, NOT the LLM. The real LLM endpoints exist but aren't wired to the chat UI.
- **`/assistant/*`:** The entire assistant module is rule-based. The codebase has a full `assistant/` module with LLM integration that's never used.
- **`nova_os/`:** 18 files, complete OS abstraction layer — never initialized.
- **`assistant/`:** 20+ files, complete assistant implementation — never initialized.
- **Frontend WebSocket:** Hooks defined, mocks in tests, config set — no actual usage.
- **Goals page:** Frontend calls wrong endpoint shape.
- **Admin page:** Response shape mismatch.
- **Auth page:** UI exists but no API integration.

### What's PLACEHOLDER / MOCK

- **`/nova-web/chat` responses:** Returns pre-formatted text with keyword-matched actions, not AI-generated responses
- **`/assistant/chat`:** Returns canned response templates based on intent keywords
- **`/nova-web/think`:** Returns a 10-step reasoning template filled with keyword-extracted data
- **`/nova-web/daily`:** Returns threshold-based assessments, not AI analysis
- **`/nova-web/self-optimize`:** Returns rule-based threshold checks
- **Mock LLM provider:** `models/providers/mock.py` exists for testing
- **Most "analytics" endpoints:** Return in-memory counters that reset on restart

### What's DEAD CODE

- `command_center/orchestrator.py:Governor` (minimal duplicate)
- `autonomy/governor.py:AutonomyGovernor` (unused)
- `nova_os/governor.py:NovaGovernor` (unused)
- `nova_os/` entire module (never initialized)
- `assistant/` entire module (never initialized, routes use CommandCenterFactory instead)
- `autonomy/approval_engine.py`, `recommendation_engine.py`, `optimization_engine.py`, `delegation_engine.py`, `autonomy_engine.py` (none wired)
- `services/index.ts` in frontend (15+ broken references)
- `hooks/index.ts` WebSocket/EventSource hooks (never imported)
- `next.config.js` WebSocket URL config
- Test mocks for WebSocket/EventSource

---

## 8. Priority Fix List

### P0 — Critical (user-facing broken)

1. **Wire `/nova-web/chat` to the real LLM** — currently returns keyword-matched text, not AI responses. The infrastructure exists (kernel/execute, models/chat), just needs to be connected.
2. **Fix goals page** — `GET /api/v1/goals` needs a default user_id or the frontend needs to pass one.

### P1 — High (broken functionality)

3. **Fix `enterprise.metrics()` and `enterprise.audit()`** — frontend calls endpoints that don't exist
4. **Fix `novaWeb.createProject()`** — frontend calls POST that doesn't exist
5. **Fix `novaWeb.approvalHistory()`** — frontend calls endpoint that doesn't exist
6. **Fix planning page response shape** — unwrap `{success, data}` in frontend
7. **Fix admin page response shape** — adapt to actual backend response

### P2 — Medium (dead code cleanup)

8. **Delete `services/index.ts`** — entirely broken legacy code
9. **Delete or fix WebSocket hooks** — either implement WS endpoints or remove the dead infrastructure
10. **Clean up `nova_os/`** — either wire it or remove it
11. **Clean up `assistant/`** — either wire it or remove it
12. **Remove dead Governor classes** — orchestrator.py Governor, AutonomyGovernor, NovaGovernor

### P3 — Low (improvements)

13. **Unify API response shapes** — backend wraps in `{success, data}`, some frontend code expects raw data
14. **Remove raw fetch() in chat/memory pages** — use the NovaAPI client consistently
15. **Add proper error handling** in frontend `useApi()` hook
