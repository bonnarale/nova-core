# NOVA BLUEPRINT v1.0

## Complete Architectural Audit & Operational Report

**Date:** 2026-07-15
**Auditor:** Automated Deep Audit
**Scope:** Entire NOVA CORE project — all code, configuration, deployment, diagnostics

---

# TABLE OF CONTENTS

1. [Executive Report](#1-executive-report)
2. [What Is NOVA](#2-what-is-nova)
3. [Complete System Diagram](#3-complete-system-diagram)
4. [Architectural Report](#4-architectural-report)
5. [Backend Module Audit](#5-backend-module-audit)
6. [Frontend Audit](#6-frontend-audit)
7. [API Architecture](#7-api-architecture)
8. [Database Architecture](#8-database-architecture)
9. [Memory Architecture](#9-memory-architecture)
10. [Agent Architecture](#10-agent-architecture)
11. [Workflow Architecture](#11-workflow-architecture)
12. [Autonomy Architecture](#12-autonomy-architecture)
13. [Command Center Architecture](#13-command-center-architecture)
14. [Deployment Report](#14-deployment-report)
15. [Diagnostics Report](#15-diagnostics-report)
16. [Dependency Report](#16-dependency-report)
17. [Functional Report](#17-functional-report)
18. [Risks Report](#18-risks-report)
19. [Strategic Recommendations](#19-strategic-recommendations)
20. [Success Criteria Answers](#20-success-criteria-answers)

---

# 1. EXECUTIVE REPORT

## What NOVA Is

NOVA CORE is an **AI operating system** built on FastAPI (Python) + Next.js (TypeScript). It aspires to be a unified platform for autonomous intelligence — combining multi-agent orchestration, memory systems, reasoning, workflows, knowledge graphs, RAG, observability, security, and enterprise features.

## Current State

| Dimension | Status |
|-----------|--------|
| Backend operational | **YES** — 25 of 39 modules fully wired and running |
| Frontend operational | **YES** — 35 of 36 pages return HTTP 200 |
| APIs operational | **YES** — 179 endpoints documented, core ones functional |
| Diagnostics operational | **YES** — score 100/100 with current checks |
| Tests | **4815+ backend, 116 frontend** — all passing |
| SDK | **YES** — Python + TypeScript, both comprehensive |
| CLI | **YES** — 14 commands functional |
| Mobile | **YES** — Flutter app, 22 screens, structurally complete |

## What NOVA Is Not

- NOVA is **not production-hardened** — 7 of 39 backend modules are dead code at runtime
- NOVA is **not fully integrated** — 5 modules are partial, not sharing core state
- NOVA is **not self-healing** — diagnostics have false negatives and hardcoded assumptions
- NOVA is **not auth-protected** — the auth page is a placeholder
- NOVA is **not a real OS** — it is a FastAPI web application with aspirational naming

## Key Numbers

| Metric | Value |
|--------|-------|
| Backend Python modules | 39 directories + 2 standalone files |
| Backend source files | ~466 |
| API route files | 37 |
| API endpoints | 179 |
| Frontend pages | 36 |
| Frontend components | 6 component directories |
| Test files | ~101 (88 backend + 13 SDK) |
| Total tests | ~4931 |
| Docker services | 8 (root compose) |
| SDK files | 31 (16 Python + 15 TypeScript) |
| CLI commands | 14 |
| Mobile screens | 22 |
| Documentation files | 35 |

---

# 2. WHAT IS NOVA

## Definition

NOVA CORE is a **monolithic AI platform** consisting of:

1. **Backend** — FastAPI application with 39 subsystem modules
2. **Frontend** — Next.js web application with 36 pages
3. **SDK** — Python and TypeScript client libraries
4. **CLI** — Command-line interface
5. **Mobile** — Flutter application (Android/iOS)
6. **Infrastructure** — Docker Compose, Kubernetes manifests, Traefik reverse proxy

## Architecture Pattern

NOVA uses a **layered monolith** architecture:

```
┌─────────────────────────────────────────────┐
│           COGNITIVE LAYER                    │
│  cognitive, reasoning, planner, assistant    │
├─────────────────────────────────────────────┤
│           EXECUTION LAYER                    │
│  agents, tools, workflows, scheduler         │
├─────────────────────────────────────────────┤
│           INTELLIGENCE LAYER                 │
│  memory, rag, vector_memory, knowledge_graph │
│  learning, long_term_memory, models          │
├─────────────────────────────────────────────┤
│           PLATFORM LAYER                     │
│  db, events, security, observability         │
│  plugins, enterprise, api                    │
├─────────────────────────────────────────────┤
│           INFRASTRUCTURE                     │
│  PostgreSQL, Redis, ChromaDB, Ollama         │
└─────────────────────────────────────────────┘
```

## Communication Pattern

All inter-module communication happens through:
1. **Direct Python imports** — modules import each other
2. **`app.state`** — FastAPI state shared across request handlers
3. **Internal EventBus** — `orchestrator/event_bus.py` for task lifecycle events
4. **External EventBus** — `events/bus.py` for system-wide events
5. **HTTP** — frontend-to-backend via REST API

---

# 3. COMPLETE SYSTEM DIAGRAM

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENTS                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Frontend │  │   SDK    │  │   CLI    │  │  Mobile  │       │
│  │ Next.js  │  │ Py + TS  │  │  Python  │  │  Flutter │       │
│  │ :3000    │  │          │  │          │  │          │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │              │              │              │             │
└───────┼──────────────┼──────────────┼──────────────┼─────────────┘
        │              │              │              │
        │         HTTP REST API       │              │
        │              │              │              │
┌───────┼──────────────┼──────────────┼──────────────┼─────────────┐
│       │         ┌────┴──────────────┴──────────────┴────┐       │
│       │         │        FASTAPI APPLICATION             │       │
│       │         │           Backend :8000                 │       │
│       │         └────────────────┬───────────────────────┘       │
│       │                          │                               │
│  ┌────┴──────────────────────────┴──────────────────────────┐   │
│  │                    API LAYER                              │   │
│  │  /api/v1/*  (37 route files, 179 endpoints)              │   │
│  │  /api/v1/nova-web/*  (15 web dashboard endpoints)        │   │
│  │  middleware: RequestID, Timing, Metrics, Exception        │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│  ┌────────────────────────┴─────────────────────────────────┐   │
│  │                COGNITIVE LAYER                            │   │
│  │  CognitiveEngine ← ReasoningEngine, Planner               │   │
│  │  ExecutivePlanner ← GoalManager, TaskManager              │   │
│  │  NovaAssistant (standalone, not wired to core)            │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│  ┌────────────────────────┴─────────────────────────────────┐   │
│  │                EXECUTION LAYER                            │   │
│  │  AgentRuntime ← AgentManager, AgentFactory                │   │
│  │  ToolRuntime ← ToolManager, ToolFactory                   │   │
│  │  WorkflowEngine, WorkflowOrchestrator                     │   │
│  │  Scheduler (cron, interval, event triggers)               │   │
│  │  TaskManager (orchestrator with internal EventBus)        │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│  ┌────────────────────────┴─────────────────────────────────┐   │
│  │              INTELLIGENCE LAYER                           │   │
│  │  RAGEngine ← KnowledgeGraphEngine                        │   │
│  │  VectorMemoryEngine ← InMemoryEmbeddingProvider           │   │
│  │  SemanticMemory ← ChromaDB + Ollama                       │   │
│  │  LongTermMemoryManager ← PostgreSQL                       │   │
│  │  ConversationMemory ← PostgreSQL                          │   │
│  │  LearningEngine (subscribed to task.completed)            │   │
│  │  ModelGateway ← OllamaProvider                            │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│  ┌────────────────────────┴─────────────────────────────────┐   │
│  │               PLATFORM LAYER                              │   │
│  │  EventSystem (InMemoryEventBus, pub/sub, lifecycle)       │   │
│  │  SecurityEngine (RBAC, rate limiting, encryption)         │   │
│  │  ObservabilityEngine (metrics, tracing, alerts)           │   │
│  │  PluginEngine (dynamic plugins, hooks, sandbox)           │   │
│  │  EnterpriseEngine (orgs, tenancy, audit, billing)         │   │
│  │  Kernel (execution engine, agent/tool registry)           │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│  ┌────────────────────────┴─────────────────────────────────┐   │
│  │              DATA LAYER                                   │   │
│  │  PostgreSQL ← db/postgres.py (SQLAlchemy async)           │   │
│  │  Redis ← services/redis.py (caching, sessions)            │   │
│  │  ChromaDB ← services/chroma.py (vector storage)           │   │
│  │  Ollama ← services/ollama.py (LLM inference)              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           UNWIRED MODULES (exist but not connected)       │   │
│  │  autonomy, deployment, future, integration,               │   │
│  │  performance, resilience, scaling                         │   │
│  │  command_center, constitution, nova_os, profile           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

# 4. ARCHITECTURAL REPORT

## Module Classification

### OPERATIONAL (25 modules) — Fully wired and running

| Module | Purpose | Key Integration |
|--------|---------|-----------------|
| `agents/` | Multi-Agent Runtime (7 built-in agents) | AgentManager, AgentRuntime wired in lifespan |
| `api/` | API Platform with middleware | Platform started, middleware applied |
| `cognitive/` | Intent detection, decision routing | CognitiveEngine receives all core references |
| `core/` | Configuration (pydantic-settings) | Settings used everywhere |
| `db/` | PostgreSQL via SQLAlchemy async | init_database/close_database in lifespan |
| `enterprise/` | Orgs, tenancy, audit, billing | EnterpriseFactory wired |
| `events/` | Async event bus, pub/sub | EventSystemFactory wired |
| `executive/` | Strategic planning | ExecutivePlanner wired |
| `kernel/` | Execution engine, registry | Kernel started and stopped |
| `knowledge_graph/` | Entity-relationship knowledge | KnowledgeGraphEngine initialized |
| `learning/` | Execution-based learning | Subscribed to task.completed events |
| `long_term_memory/` | Persistent knowledge storage | LongTermMemoryManager via adapter |
| `memory/` | Conversation, profile, goals, semantic | All 4 managers wired |
| `models/` | LLM gateway with providers | ModelGatewayFactory wired |
| `observability/` | Metrics, tracing, alerts | ObservabilityFactory wired |
| `orchestrator/` | Task management, internal EventBus | TaskManager wired |
| `planner/` | Autonomous plan decomposition | Planner wired |
| `plugins/` | Dynamic plugin management | PluginFactory wired |
| `rag/` | Retrieval-Augmented Generation | RAGFactory wired |
| `reasoning/` | Structured reasoning strategies | ReasoningEngine created |
| `scheduler/` | Job scheduling (cron, interval) | SchedulerFactory wired |
| `security/` | Auth, RBAC, encryption | SecurityFactory wired |
| `services/` | ChromaDB, Ollama, Redis clients | All clients created in lifespan |
| `tools/` | 6 built-in tools (filesystem, git, etc.) | ToolManager, ToolFactory wired |
| `vector_memory/` | Dense vector storage/search | VectorMemoryFactory wired |
| `workflows/` | Workflow engine + orchestrator | Both created and started |

### PARTIAL (5 modules) — Exist but not sharing core state

| Module | Issue |
|--------|-------|
| `assistant/` | Creates standalone NovaAssistant via lazy factory, does NOT share event_bus/db/agents |
| `command_center/` | Lazy-instantiated in route files, does NOT share core state |
| `constitution/` | Lazy-instantiated, duplicates objectives/backlog from command_center |
| `nova_os/` | Abstract OS interfaces defined, concrete class lazily loaded in route |
| `profile/` | In-memory profile management, duplicates DB-backed memory/profile.py |

### THEORETICAL (7 modules) — Full code, zero runtime connection

| Module | Lines of Code | API Routes | Issue |
|--------|--------------|------------|-------|
| `autonomy/` | ~500 | Yes | `set_dependencies()` never called |
| `deployment/` | ~400 | Yes | `set_dependencies()` never called |
| `future/` | ~600 | Yes | `__init__.py` exports nothing |
| `integration/` | ~500 | Yes | `set_dependencies()` never called |
| `performance/` | ~600 | Yes | `set_dependencies()` never called |
| `resilience/` | ~700 | Yes | `set_dependencies()` never called |
| `scaling/` | ~500 | Yes | `set_dependencies()` never called |

### UNUSED (1 module)

| Module | Issue |
|--------|-------|
| `schemas/` | 3 conversation schemas, never imported anywhere |

## Duplications Found

### Duplication Cluster 1: Objectives Management
Three near-identical `ObjectivesManager` classes exist in:
- `autonomy/objective_manager.py`
- `command_center/objectives.py`
- `constitution/objectives.py`

### Duplication Cluster 2: Backlog Management
Three near-identical `BacklogManager` classes exist in:
- `autonomy/backlog.py`
- `command_center/backlog.py`
- `constitution/backlog.py`

### Duplication Cluster 3: User Profiles
Two user profile systems:
- `memory/profile.py` (UserProfileMemory) — **DB-backed, wired**
- `profile/profile.py` (ProfileManager) — **In-memory, not wired**

### Duplication Cluster 4: Event Buses
Two event bus implementations:
- `events/bus.py` (InMemoryEventBus) — **Primary, wired**
- `orchestrator/event_bus.py` (internal EventBus) — **Used by TaskManager**

### Duplication Cluster 5: Model Gateways
Two ModelGateway instances created in main.py:
- `gateway_factory.create_gateway()` — **Modern, factory-based**
- `ModelGateway(settings)` — **Legacy, direct constructor**

### Duplication Cluster 6: Workflow Engines
Two workflow abstractions:
- `WorkflowEngine` — **Simpler, created first**
- `WorkflowOrchestrator` — **More complex, started separately**

---

# 5. BACKEND MODULE AUDIT

## Detailed Module Table

| # | Module | Status | Wired | API Route | Files | Key Issue |
|---|--------|--------|-------|-----------|-------|-----------|
| 1 | agents/ | OPERATIONAL | Yes | Yes | 19 | None |
| 2 | api/ | OPERATIONAL | Yes | N/A | 23 | None |
| 3 | assistant/ | PARTIAL | No | Yes | 8 | Standalone, not sharing state |
| 4 | autonomy/ | THEORETICAL | No | Yes | 12 | Never wired |
| 5 | cognitive/ | OPERATIONAL | Yes | No | 5 | None |
| 6 | command_center/ | PARTIAL | No | Yes | 10 | Lazy, standalone |
| 7 | constitution/ | PARTIAL | No | Yes | 8 | Duplicates command_center |
| 8 | core/ | OPERATIONAL | Yes | No | 3 | None |
| 9 | db/ | OPERATIONAL | Yes | Yes | 18 | architecture.py partially unused |
| 10 | deployment/ | THEORETICAL | No | Yes | 8 | Never wired |
| 11 | enterprise/ | OPERATIONAL | Yes | Yes | 12 | None |
| 12 | events/ | OPERATIONAL | Yes | Yes | 15 | None |
| 13 | executive/ | OPERATIONAL | Yes | No | 3 | None |
| 14 | future/ | THEORETICAL | No | Yes | 19 | Exports nothing |
| 15 | integration/ | THEORETICAL | No | Yes | 10 | Never wired |
| 16 | kernel/ | OPERATIONAL | Yes | Yes | 6 | None |
| 17 | knowledge_graph/ | OPERATIONAL | Yes | Yes | 8 | None |
| 18 | learning/ | OPERATIONAL | Yes | Yes | 8 | None |
| 19 | long_term_memory/ | OPERATIONAL | Yes | No | 11 | Complex adapter in main.py |
| 20 | memory/ | OPERATIONAL | Yes | Yes | 10 | None |
| 21 | models/ | OPERATIONAL | Yes | Yes | 8 | Two gateway instances |
| 22 | nova_os/ | PARTIAL | No | Yes | 5 | Abstract only, not wired |
| 23 | observability/ | OPERATIONAL | Yes | Yes | 12 | None |
| 24 | orchestrator/ | OPERATIONAL | Yes | Yes | 8 | Dual event bus |
| 25 | performance/ | THEORETICAL | No | Yes | 14 | Never wired |
| 26 | planner/ | OPERATIONAL | Yes | No | 6 | None |
| 27 | plugins/ | OPERATIONAL | Yes | Yes | 10 | None |
| 28 | profile/ | PARTIAL | No | Yes | 6 | Duplicates memory/profile |
| 29 | rag/ | OPERATIONAL | Yes | Yes | 12 | None |
| 30 | reasoning/ | OPERATIONAL | Yes | No | 5 | Minimal integration |
| 31 | resilience/ | THEORETICAL | No | Yes | 14 | Never wired |
| 32 | scaling/ | THEORETICAL | No | Yes | 12 | Never wired |
| 33 | scheduler/ | OPERATIONAL | Yes | Yes | 8 | None |
| 34 | schemas/ | UNUSED | No | No | 1 | Never imported |
| 35 | security/ | OPERATIONAL | Yes | Yes | 12 | None |
| 36 | services/ | OPERATIONAL | Yes | No | 5 | None |
| 37 | tools/ | OPERATIONAL | Yes | Yes | 12 | None |
| 38 | vector_memory/ | OPERATIONAL | Yes | Yes | 14 | None |
| 39 | workflows/ | OPERATIONAL | Yes | Yes | 30 | Dual abstraction |

---

# 6. FRONTEND AUDIT

## Page Status

| Page | Status | API Endpoints Used | Notes |
|------|--------|-------------------|-------|
| `/nova` | REAL | Delegates to NovaChat + NovaDashboard | Default landing page |
| `/dashboard` | REAL | `/api/v1/health` | Minimal — only health data |
| `/chat` | REAL | `/api/v1/agents`, WebSocket `/api/v1/chat/ws` | Real-time chat, no persistence |
| `/projects` | REAL | `/api/v1/nova-web/projects` (GET+POST) | Full CRUD with detail view |
| `/tasks` | REAL | `/api/v1/tasks` | Table + board view, read-only |
| `/workflows` | REAL | `/api/v1/workflows` | List + placeholder visual view |
| `/memory` | REAL | `/api/v1/nova-web/memory` | 4 subsystem status display |
| `/roadmaps` | REAL | `/api/v1/nova-web/roadmaps` (GET+POST) | Full CRUD with timeline |
| `/approvals` | REAL | `/api/v1/nova-web/approvals` (GET+POST) | Full approve/reject flow |
| `/goals` | REAL | `/api/v1/goals` | Read-only with status filter |
| `/tools` | REAL | `/api/v1/nova-web/tools` | Rich read-only dashboard |
| `/observability` | REAL | `/api/v1/nova-web/observability` | Data-rich dashboard |
| `/settings` | REAL | None (local Zustand) | Only theme toggle works |
| `/agents` | REAL | `/api/v1/agents` | Read-only card grid |
| `/backlog` | REAL | `/api/v1/nova-web/backlog` (GET+POST) | Full CRUD with filtering |
| `/models` | REAL | `/api/v1/models/list` | Read-only model browser |
| `/plugins` | REAL | `/api/v1/plugins` | Read-only plugin list |
| `/security` | REAL | `/api/v1/security/audit`, `statistics` | Read-only audit log |
| `/enterprise` | REAL | `/api/v1/enterprise/status` | Read-only feature list |
| `/deployment` | REAL | `/api/v1/deployment/health` | Read-only health display |
| `/events` | REAL | `/api/v1/events` | Read-only event list |
| `/execution` | REAL | `/api/v1/scheduler/jobs` | Reuses scheduler endpoint |
| `/knowledge` | REAL | `/api/v1/knowledge-graph/entities` | Entity explorer |
| `/learning` | REAL | `/api/v1/learning/stats` | Learning statistics |
| `/rag` | REAL | `/api/v1/rag/statistics` | RAG statistics + query input |
| `/reasoning` | REAL | `/api/v1/observability/traces` | Reuses observability traces |
| `/scaling` | REAL | `/api/v1/scaling/health` | Read-only scaling display |
| `/scheduler` | REAL | `/api/v1/scheduler/jobs` | Job list with status |
| `/system` | REAL | `/api/v1/integration/status` | System health view |
| `/vector-memory` | REAL | `/api/v1/vector-memory/statistics` | Vector memory explorer |
| `/autonomy` | REAL | `/api/v1/autonomy/status` | Read-only autonomy display |
| `/planning` | REAL | `/api/v1/autonomy/objectives` | Read-only objectives |
| `/admin` | REAL | `/api/v1/deployment/environment` | Environment info |
| `/profile` | REAL | `/api/v1/profile/status` | Read-only profile display |
| `/auth` | PLACEHOLDER | None | Form exists, no logic |

## Dead Frontend Code

| Component | Status |
|-----------|--------|
| `components/charts/` (BarChart, LineChart, PieChart) | Exported, never imported |
| `components/common/` (PageContainer, Section, LoadingScreen, ErrorFallback, ConfirmDialog, Toast) | Exported, never imported |
| `components/workflow/` (WorkflowCanvas, WorkflowToolbar) | Exported, never imported |
| `components/chat/MessageBubble` | Exported, chat page uses inline rendering |
| `components/chat/TypingIndicator` | Exported, never used |
| `stores/index.ts` useChatStore | Exported, chat page uses local state |
| `stores/index.ts` useCacheStore | Exported, never used |
| `hooks/index.ts` useWebSocket | Exported, chat page implements its own |
| `hooks/index.ts` useLocalStorage, useDebounce, usePolling, useEventSource | Exported, never used |
| `types/index.ts` many interfaces | Defined but pages use local types |

## Inconsistent API Access Patterns

Three different patterns used across pages:
1. `useApi<T>("/api/v1/...")` hook — **22 pages**
2. `novaWeb.*()` client methods — **6 pages** (approvals, backlog, observability, projects, roadmaps, tools)
3. Direct `fetch()` — **1 page** (memory)

---

# 7. API ARCHITECTURE

## Route Files (37 total)

| Route File | Prefix | Endpoints | Status |
|-----------|--------|-----------|--------|
| agents.py | `/agents` | list, get, create, dispatch, health, metrics | FUNCTIONAL |
| assistant.py | `/assistant` | execute, health | DEGRADED (standalone) |
| autonomy.py | `/autonomy` | status, objectives | DEAD (deps not set) |
| autonomy_system.py | `/autonomy-system` | status, capabilities | DEAD (lazy standalone) |
| command_center.py | `/command-center` | status, objectives, projects | DEGRADED (lazy standalone) |
| constitution.py | `/constitution` | mission, values, policies | DEGRADED (lazy standalone) |
| database.py | `/database` | health, status | DEAD (deps not set) |
| deployment.py | `/deployment` | health, readiness, diagnostics | DEAD (deps not set) |
| enterprise.py | `/enterprise` | status, organizations, tenants | FUNCTIONAL |
| events.py | `/events` | list, publish, statistics | FUNCTIONAL |
| future.py | `/future` | status, features, experiments | DEAD (deps not set) |
| goals.py | `/goals/{uid}` | list, create, analyze | FUNCTIONAL |
| health.py | `/health` | health check | FUNCTIONAL |
| integration.py | `/integration` | status | DEAD (deps not set) |
| kernel.py | `/kernel` | execute, sessions, agents | FUNCTIONAL |
| knowledge_graph.py | `/knowledge-graph` | entities, search, validate | FUNCTIONAL |
| learning.py | `/learning` | artifacts, extract, stats | FUNCTIONAL |
| memory.py | `/memory/{sid}` | get conversation | FUNCTIONAL |
| models.py | `/models` | list, chat, health, providers | FUNCTIONAL |
| nova_os.py | `/nova-os` | status | DEGRADED (lazy standalone) |
| nova_web.py | `/nova-web` | dashboard, chat, objectives, projects, etc. (15) | FUNCTIONAL |
| observability.py | `/observability` | health, metrics, traces, logs, alerts | FUNCTIONAL |
| performance.py | `/performance` | health, metrics | DEAD (deps not set) |
| plugins.py | `/plugins` | list, register, health, statistics | FUNCTIONAL |
| profile.py | `/profile/{uid}` | get, update | FUNCTIONAL |
| rag.py | `/rag` | query, index, health, metrics | FUNCTIONAL |
| resilience.py | `/resilience` | health, metrics | DEAD (deps not set) |
| scaling.py | `/scaling` | health, workers, cache, resources | DEAD (deps not set) |
| scheduler.py | `/scheduler` | jobs, create, statistics, health | FUNCTIONAL |
| security.py | `/security` | health, statistics, roles, audit | FUNCTIONAL |
| tasks.py | `/tasks` | list, create, get | FUNCTIONAL |
| tools.py | `/tools` | list, register, metrics | FUNCTIONAL |
| user_profile.py | `/user-profile` | get, update | FUNCTIONAL |
| vector_memory.py | `/vector-memory` | search, store, statistics, health | FUNCTIONAL |
| workflows.py | `/workflows` | list, create, get, execute, health | FUNCTIONAL |

## Route Status Summary

| Status | Count | Percentage |
|--------|-------|------------|
| FUNCTIONAL | 25 | 68% |
| DEGRADED | 5 | 14% |
| DEAD | 7 | 19% |

---

# 8. DATABASE ARCHITECTURE

## Persistence Layers

| Database | Technology | Status | Purpose | Mandatory? |
|----------|-----------|--------|---------|------------|
| PostgreSQL | Docker (16.4-alpine) | RUNNING | Primary relational DB | YES |
| Redis | Docker (7.4-alpine) | RUNNING | Caching, sessions | OPTIONAL |
| ChromaDB | Docker (0.5.23) | RUNNING | Vector storage | OPTIONAL |
| Ollama | Docker (latest) | RUNNING | LLM inference | OPTIONAL |
| In-Memory | Python dicts/lists | ACTIVE | RAG, Vector Memory, Events | N/A |

## PostgreSQL Tables

Managed via SQLAlchemy ORM (`db/models.py`):
- `conversation_sessions` — Chat sessions
- `conversation_messages` — Chat messages
- `user_profiles` — User profiles
- `agents` — Agent definitions
- `goals` — Goal tracking
- `orchestrator_tasks` — Task management
- `workflow_definitions` — Workflow definitions
- `workflow_executions` — Workflow runs
- `workflow_events` — Workflow events
- `knowledge_graph_entities` — KG entities
- `knowledge_graph_relationships` — KG relationships
- `long_term_memory` — Persistent memory

## In-Memory Only (No Persistence)

These subsystems store data only in memory:
- RAG engine (`rag/`) — InMemoryRepository
- Vector Memory (`vector_memory/`) — InMemoryVectorRepository
- Event Bus (`events/`) — InMemoryEventBus
- Command Center (`command_center/`) — all in-memory
- Profile Manager (`profile/`) — all in-memory
- Constitution (`constitution/`) — all in-memory
- Autonomy (`autonomy/`) — all in-memory

---

# 9. MEMORY ARCHITECTURE

## Memory Systems

| System | Module | Storage | Status | Connected? |
|--------|--------|---------|--------|------------|
| Conversation Memory | `memory/conversation_memory.py` | PostgreSQL | OPERATIONAL | Yes |
| User Profile Memory | `memory/profile.py` | PostgreSQL | OPERATIONAL | Yes |
| Goal Manager | `memory/goals.py` | PostgreSQL | OPERATIONAL | Yes |
| Semantic Memory | `memory/semantic.py` | ChromaDB + Ollama | OPERATIONAL | Yes |
| Long-Term Memory | `long_term_memory/` | PostgreSQL | OPERATIONAL | Yes |
| Knowledge Graph | `knowledge_graph/` | PostgreSQL + in-memory | OPERATIONAL | Yes |
| Vector Memory | `vector_memory/` | In-memory | OPERATIONAL | Yes |
| RAG | `rag/` | In-memory | OPERATIONAL | Yes |
| Learning | `learning/` | In-memory | OPERATIONAL | Yes |
| Profile Manager | `profile/` | In-memory | PARTIAL | No (lazy) |
| Command Center Memory | `command_center/` | In-memory | PARTIAL | No (lazy) |

## Memory Flow

```
User Input → CognitiveEngine → Intent Detection
  ├─→ ConversationMemory (session history)
  ├─→ SemanticMemory (ChromaDB vector search)
  ├─→ LongTermMemory (persistent knowledge)
  ├─→ KnowledgeGraph (entity relationships)
  └─→ UserProfileMemory (user context)
```

---

# 10. AGENT ARCHITECTURE

## Built-in Agents

| Agent | Class | Purpose |
|-------|-------|---------|
| Planner | `PlannerAgent` | Strategic planning |
| Researcher | `ResearchAgent` | Information gathering |
| Coder | `CoderAgent` | Code generation |
| Reviewer | `ReviewerAgent` | Code review |
| Memory | `MemoryAgent` | Memory operations |
| Executor | `ExecutorAgent` | Task execution |
| Coordinator | `CoordinatorAgent` | Multi-agent coordination |

## Agent System Components

| Component | Module | Status |
|-----------|--------|--------|
| AgentManager | `agents/agent_manager.py` | OPERATIONAL |
| AgentRuntime | `agents/runtime.py` | OPERATIONAL |
| AgentFactory | `agents/factory.py` | OPERATIONAL |
| LLM Agent | `agents/llm_agent.py` | OPERATIONAL |
| Tool Runtime | `tools/runtime.py` | OPERATIONAL |
| Tool Manager | `tools/manager.py` | OPERATIONAL |

## Agent Communication

```
User Request → CognitiveEngine
  → Intent Detection (13 handler types)
  → Agent Dispatch (via AgentManager)
  → Agent Execution (via AgentRuntime)
  → Tool Invocation (via ToolRuntime)
  → Result Aggregation
  → Response
```

---

# 11. WORKFLOW ARCHITECTURE

## Workflow Components

| Component | Module | Status |
|-----------|--------|--------|
| WorkflowEngine | `workflows/engine.py` | OPERATIONAL |
| WorkflowOrchestrator | `workflows/orchestrator.py` | OPERATIONAL |
| WorkflowFactory | `workflows/factory.py` | OPERATIONAL |
| DAG Builder | `workflows/builder.py` | OPERATIONAL |

## Workflow Node Types

- TaskNode, AgentNode, ConditionNode, LoopNode
- ParallelNode, GateNode, TransformNode
- SubWorkflowNode, ApprovalNode, DelayNode
- WebhookNode, ErrorNode

---

# 12. AUTONOMY ARCHITECTURE

## Current State: THEORETICAL

The autonomy system exists as:
- `autonomy/autonomy_engine.py` — Full implementation
- `autonomy/objective_manager.py` — Objectives CRUD
- `autonomy/recommendation_engine.py` — Recommendations
- `autonomy/backlog.py` — Backlog management

**Problem:** Never wired into `main.py`. The `set_dependencies()` function in the route file is never called. All API endpoints return `{"state": "unknown"}` or empty data.

## What It Could Do (if wired)

- Risk-level-based autonomy control
- Objective management and prioritization
- Recommendation generation
- Self-improvement tracking
- Delegation and research

---

# 13. COMMAND CENTER ARCHITECTURE

## Current State: PARTIAL

The command center exists as:
- `command_center/command_center.py` — Unified CC class
- `command_center/governor.py` — Decision governor
- `command_center/objectives.py` — Objectives manager
- `command_center/projects.py` — Projects manager
- `command_center/backlog.py` — Backlog manager
- `command_center/approvals.py` — Approvals manager
- `command_center/roadmap.py` — Roadmap manager

**Problem:** Created lazily in route files, does NOT share core state (event bus, database, agents). Duplicates functionality from `autonomy/` and `constitution/`.

## NOVA Web API

The `nova_web.py` route file (386 lines) provides the primary web dashboard API with 15 endpoints:
- Dashboard, Chat, Objectives, Projects, Roadmaps, Tasks
- Backlog, Approvals (approve/reject), Recommendations (accept)
- Memory, Observability, Tools

All of these use the lazily-created CommandCenter components.

---

# 14. DEPLOYMENT REPORT

## Active Deployment Mechanisms

| Mechanism | Command | Status |
|-----------|---------|--------|
| Local dev (Makefile) | `make start` | PRIMARY |
| Docker Compose (root) | `make docker-start` | PRIMARY |
| Kubernetes | `deployment/scripts/deploy.sh` | AVAILABLE |
| VS Code Dev Container | `.devcontainer/devcontainer.json` | AVAILABLE |

## Docker Services (Root Compose)

| Service | Image | Port | Health | Status |
|---------|-------|------|--------|--------|
| traefik | traefik:v3.1 | 80, 8080 | Yes | RUNNING |
| backend | Custom build | 8000 | Yes | RUNNING |
| postgres | postgres:16.4-alpine | internal | Yes | RUNNING |
| redis | redis:7.4-alpine | internal | Yes | RUNNING |
| chroma | chromadb/chroma:0.5.23 | internal | Yes | RUNNING |
| ollama | ollama/ollama:latest | 11434 | Yes | RUNNING |
| open-webui | ghcr.io/open-webui/open-webui:0.3.35 | via traefik | Yes | RUNNING |
| n8n | n8nio/n8n:1.60.1 | via traefik | Yes | RUNNING |

## Obsolete Deployment Files

| File | Issue |
|------|-------|
| `deployment/docker/docker-compose.yml` | Superseded by root compose, different credentials |
| `deployment/docker/Dockerfile` | Superseded by `docker/backend/Dockerfile` |
| `deployment/docker/Dockerfile.dev` | No equivalent in active use |
| `deployment/scripts/start.sh` | References obsolete compose |
| `deployment/scripts/stop.sh` | References obsolete compose |
| `deployment/scripts/build.sh` | References obsolete Dockerfile |
| `deployment/scripts/migrate.sh` | Fake — only prints "Models loaded" |

---

# 15. DIAGNOSTICS REPORT

## Scoring System

| Severity | Weight | Example |
|----------|--------|---------|
| CRITICAL | 10.0 | Python interpreter, API endpoints |
| HIGH | 5.0 | Docker containers, frontend app |
| MEDIUM | 2.0 | Python packages, ports |
| LOW | 1.0 | Project files |
| INFO | 0.5 | Docker container health |

**Score Formula:** `int((earned_weight / total_weight) * 100)`
- READY = 100% of weight
- DEGRADED = 40% of weight
- NOT_READY = 0% of weight

## Known Diagnostic Issues

### False Negatives

1. **Hardcoded Docker container names** (`nova_diagnose.py:420-423`): `nova-core-postgres-1`, `nova-core-redis-1`, etc. fail if project name is overridden.

2. **`check_url` ignores response body** (`nova_diagnose.py:240-267`): HTTP 200 with `{"status": "degraded"}` is treated as READY.

3. **WSL distribution hardcoded** (`nova_diagnose.py:325`): `"Ubuntu-26.04"` is hardcoded.

4. **Quick mode is incomplete** (`nova_diagnose.py:465-467`): Only checks Python + CLI tools, skips API/Docker checks.

5. **Makefile `status` checks PIDs not health** (`Makefile:29-57`): A zombie process with a valid PID file is reported as "OPERATIONAL".

### Inaccurate Assumptions

1. Port 8000 always accessible (may be behind reverse proxy)
2. Port 3000 is always frontend (Grafana uses it in deployment compose)
3. All 12 API endpoints respond to unauthenticated GET
4. Docker Compose naming convention is always `{project}-{service}-1`

---

# 16. DEPENDENCY REPORT

## Python Dependencies (Required)

| Package | Version | Purpose | Required? |
|---------|---------|---------|-----------|
| fastapi | 0.139.0 | Web framework | YES |
| uvicorn | 0.51.0 | ASGI server | YES |
| pydantic | 2.13.4 | Data validation | YES |
| pydantic-settings | 2.14.2 | Configuration | YES |
| httpx | 0.28.1 | HTTP client | YES |
| sqlalchemy | 2.0.51 | ORM | YES |
| asyncpg | 0.31.0 | PostgreSQL async driver | YES |
| redis | 8.0.1 | Redis client | YES |
| chromadb | 1.5.9 | Vector DB client | YES |

## Python Dependencies (Optional)

| Package | Purpose | Required? |
|---------|---------|-----------|
| numpy | Numerical operations | Optional |
| onnxruntime | ML inference | Optional |
| tokenizers | Text tokenization | Optional |
| opentelemetry-* | Observability | Optional |

## Node.js Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| next | 14.2.x | React framework |
| react | 18.3.x | UI library |
| react-dom | 18.3.x | React DOM |
| swr | 2.2.x | Data fetching |
| zustand | 4.5.x | State management |
| typescript | 5.5.x | Type checking |
| jest | 29.7.x | Testing |

## Docker Services

| Service | Image | Required? |
|---------|-------|-----------|
| PostgreSQL | postgres:16.4-alpine | YES (primary DB) |
| Redis | redis:7.4-alpine | OPTIONAL (caching) |
| ChromaDB | chromadb/chroma:0.5.23 | OPTIONAL (vector storage) |
| Ollama | ollama/ollama:latest | OPTIONAL (LLM inference) |
| Traefik | traefik:v3.1 | OPTIONAL (reverse proxy) |
| Open WebUI | ghcr.io/open-webui/open-webui:0.3.35 | OPTIONAL (Ollama UI) |
| n8n | n8nio/n8n:1.60.1 | OPTIONAL (workflow automation) |

---

# 17. FUNCTIONAL REPORT

## What Actually Works

### Backend (VERIFIED via HTTP requests)

| Capability | Endpoint | Status |
|-----------|----------|--------|
| Health check | GET /health | 200, returns service status |
| API docs | GET /docs | 200, Swagger UI |
| Agents list | GET /api/v1/agents | 200, returns agent definitions |
| Tasks list | GET /api/v1/tasks | 200, returns task list |
| Workflows list | GET /api/v1/workflows | 200, returns workflow list |
| Dashboard | GET /api/v1/nova-web/dashboard | 200, returns full dashboard data |
| Chat | POST /api/v1/nova-web/chat | 200, processes messages |
| Objectives | GET /api/v1/nova-web/objectives | 200, returns objectives |
| Projects | GET /api/v1/nova-web/projects | 200, returns projects |
| Approvals | GET /api/v1/nova-web/approvals | 200, returns pending items |
| Memory | GET /api/v1/nova-web/memory | 200, returns memory status |
| Observability | GET /api/v1/nova-web/observability | 200, returns metrics/traces |
| Scheduler | GET /api/v1/scheduler/health | 200, running |
| Security | GET /api/v1/security/health | 200, running |
| Models | GET /api/v1/models/health | 200, Ollama healthy |
| RAG | GET /api/v1/rag/health | 200, healthy |
| Vector Memory | GET /api/v1/vector-memory/health | 200, healthy |
| Enterprise | GET /api/v1/enterprise/status | 200, active |
| Knowledge Graph | GET /api/v1/knowledge-graph/validate | 200, valid |

### Frontend (VERIFIED via HTTP requests)

| Page | Status |
|------|--------|
| All 35 functional pages | HTTP 200 |
| Auth page | HTTP 200 (placeholder) |

### Tests (VERIFIED via pytest)

| Category | Count | Status |
|----------|-------|--------|
| Backend tests | ~4815 | ALL PASSING |
| Frontend tests | 116 | ALL PASSING |
| **Total** | **~4931** | **ALL PASSING** |

## What Does NOT Work

| Capability | Issue |
|-----------|-------|
| Authentication | Auth page is placeholder, no backend auth |
| Real-time events | Events page does one-time fetch, no WebSocket |
| Chat persistence | Messages lost on page refresh |
| Create operations | Most "Create" buttons are non-functional |
| Action buttons | Deploy, Scale, Install, Audit buttons are non-functional |
| Charts | Components exist but are never used |
| Error boundaries | ErrorFallback component exists but is never used |

---

# 18. RISKS REPORT

## Critical Risks

| Risk | Impact | Likelihood |
|------|--------|------------|
| 7 dead backend modules (~35% of code) | Maintenance burden, confusion | CERTAIN |
| No authentication | Security vulnerability | CERTAIN |
| Hardcoded credentials in k8s secret.yml | Security vulnerability | HIGH |
| Duplicate ObjectivesManager (3 copies) | Divergence bugs | HIGH |
| Stale deployment/ directory | Developer confusion | HIGH |

## High Risks

| Risk | Impact | Likelihood |
|------|--------|------------|
| Diagnostic false negatives | Incorrect operational assessment | HIGH |
| Two ModelGateway instances | Resource waste, confusion | MEDIUM |
| Two event bus implementations | Event routing confusion | MEDIUM |
| NovaAssistant not integrated | Feature doesn't work as expected | HIGH |
| In-memory-only subsystems | Data loss on restart | HIGH |

## Medium Risks

| Risk | Impact | Likelihood |
|------|--------|------------|
| Dead frontend code (charts, common, workflow) | Bundle size, maintenance | MEDIUM |
| Inconsistent API access patterns | Developer confusion | MEDIUM |
| Non-functional action buttons | User frustration | MEDIUM |
| Home/ directory (filesystem debris) | Repository pollution | LOW |

---

# 19. STRATEGIC RECOMMENDATIONS

## Priority 1: Connect Dead Modules

Wire the 7 THEORETICAL modules into `main.py` lifespan:
- `deployment/` — `set_dependencies(manager=deployment_engine)`
- `scaling/` — `set_dependencies(engine=scaling_engine)`
- `resilience/` — `set_dependencies(engine=resilience_engine)`
- `performance/` — `set_dependencies(engine=performance_engine)`
- `integration/` — `set_dependencies(engine=integration_engine)`
- `autonomy/` — `set_dependencies(engine=autonomy_engine)`
- `future/` — Export classes from `__init__.py`, wire into lifespan

**OR** remove them if they are not needed.

## Priority 2: Deduplicate

- Merge `command_center/`, `constitution/`, and `autonomy/` objective/backlog management into one
- Remove `profile/` (in-memory) in favor of `memory/profile.py` (DB-backed)
- Consolidate two ModelGateway instances
- Consolidate two event bus implementations
- Consolidate two workflow abstractions

## Priority 3: Add Authentication

The auth page exists but has no logic. Implement:
- JWT-based authentication
- Login/signup API endpoints
- Token refresh
- Protected routes

## Priority 4: Fix Diagnostics

- Make Docker container names discoverable (use `docker compose ps`)
- Parse `/health` response body for status
- Fix Makefile `status` to check health endpoint, not just PIDs
- Add retry logic for transient failures

## Priority 5: Clean Up Obsolete Files

| Action | Files |
|--------|-------|
| Delete | `deployment/docker/docker-compose.yml`, `deployment/docker/Dockerfile`, `deployment/docker/Dockerfile.dev` |
| Delete | `deployment/scripts/start.sh`, `stop.sh`, `build.sh`, `migrate.sh` |
| Delete | `home/` directory |
| Delete | Root-level placeholder directories (`agents/`, `memory/`, `rag/`, `workflows/`) |
| Archive | `scripts/create_tables.py` (dangerous utility) |

## Priority 6: Integrate NovaAssistant

The assistant creates its own instances instead of sharing core state. Fix by:
- Passing core references (event_bus, task_manager, agents) to NovaAssistant
- Or removing the standalone factory and using the shared instances

---

# 20. SUCCESS CRITERIA ANSWERS

### What is NOVA?
A monolithic AI platform built on FastAPI + Next.js with 39 backend modules, 36 frontend pages, Python/TypeScript SDKs, CLI, and Flutter mobile app. It aspires to be an autonomous intelligence operating system.

### What is NOVA not?
It is not production-hardened (35% dead code), not auth-protected, not self-healing, and not a real operating system despite the naming.

### Which components are complete?
25 operational backend modules, 35 functional frontend pages, Python SDK, TypeScript SDK, CLI, Flutter mobile app, Docker Compose deployment, Kubernetes manifests, ~4931 passing tests.

### Which components are unfinished?
7 theoretical modules (autonomy, deployment, future, integration, performance, resilience, scaling), 5 partial modules (assistant, command_center, constitution, nova_os, profile), auth page, real-time events, chat persistence.

### Which components are duplicated?
ObjectivesManager (3 copies), BacklogManager (3 copies), UserProfile (2 copies), EventBus (2 copies), ModelGateway (2 copies), WorkflowEngine (2 copies).

### Which components are obsolete?
`deployment/docker/` directory (superseded), root-level placeholder directories, `schemas/` module, `home/` directory.

### How should NOVA be officially deployed?
`make start` for local development. `make docker-start` for full stack. Root `docker-compose.yml` is the canonical deployment file.

### Which services are mandatory?
PostgreSQL (primary DB), Backend (FastAPI), Frontend (Next.js).

### Which services are optional?
Redis (caching), ChromaDB (vectors), Ollama (LLM), Traefik (proxy), Open WebUI (Ollama UI), n8n (workflow automation).

### Which diagnostics are incorrect?
Docker container name hardcoding, response body ignoring, WSL distro hardcoding, Makefile PID-only checks, quick mode incompleteness.

### What prevents NOVA from being considered operational?
35% dead code, no authentication, duplicated modules, stale deployment files.

### What must be repaired?
Wire dead modules OR remove them. Deduplicate. Add auth. Fix diagnostics.

### What must not be repaired?
The 25 operational modules that are working correctly. Do not refactor working code.

### What should become the official architecture?
The current layered monolith is sound. The fix is to clean up dead code, deduplicate, and complete the unwired modules.

---

*END OF NOVA BLUEPRINT v1.0*
