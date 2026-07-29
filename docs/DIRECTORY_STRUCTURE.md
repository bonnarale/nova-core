# Directory Structure

## Project Root

```
nova-core/
├── backend/                 # Python backend application
│   ├── app/                 # Application source code
│   │   ├── agents/          # Multi-agent runtime (19 files)
│   │   │   ├── builtins/    # Built-in agent implementations
│   │   │   │   ├── coder_agent.py
│   │   │   │   ├── coordinator_agent.py
│   │   │   │   ├── executor_agent.py
│   │   │   │   ├── memory_agent.py
│   │   │   │   ├── planner_agent.py
│   │   │   │   ├── research_agent.py
│   │   │   │   └── reviewer_agent.py
│   │   │   ├── base.py      # Agent ABCs
│   │   │   ├── capabilities.py
│   │   │   ├── context.py
│   │   │   ├── coordinator.py
│   │   │   ├── dispatcher.py
│   │   │   ├── executor.py
│   │   │   ├── factory.py
│   │   │   ├── lifecycle.py
│   │   │   ├── metrics.py
│   │   │   ├── policies.py
│   │   │   ├── registry.py
│   │   │   ├── runtime.py
│   │   │   ├── scheduler.py
│   │   │   └── tracing.py
│   │   ├── api/             # FastAPI layer
│   │   │   └── v1/
│   │   │       ├── router.py   # Main router
│   │   │       └── routes/     # 23 route modules
│   │   ├── cognitive/       # Cognitive engine (7 files)
│   │   ├── core/            # Core utilities (4 files)
│   │   ├── db/              # Database layer (28 files)
│   │   ├── deployment/      # Deployment management (20 files)
│   │   ├── events/          # Event system (19 files)
│   │   ├── future/          # Future roadmap (18 files)
│   │   ├── knowledge_graph/ # Knowledge graph (16 files)
│   │   ├── learning/        # Learning engine (14 files)
│   │   ├── long_term_memory/ # Long-term memory (11 files)
│   │   ├── memory/          # Memory management (10 files)
│   │   ├── models/          # Model gateway (15 files)
│   │   ├── observability/   # Observability (22 files)
│   │   ├── orchestrator/    # Task orchestration (6 files)
│   │   ├── planner/         # Task planning (8 files)
│   │   ├── plugins/         # Plugin system (28 files)
│   │   ├── rag/             # RAG pipeline (20 files)
│   │   ├── reasoning/       # Reasoning engine (11 files)
│   │   ├── scaling/         # Scaling (23 files)
│   │   ├── scheduler/       # Job scheduler (17 files)
│   │   ├── schemas/         # Shared schemas (2 files)
│   │   ├── security/        # Security layer (21 files)
│   │   ├── services/        # Shared services (6 files)
│   │   ├── tools/           # Tool system (24 files)
│   │   ├── vector_memory/   # Vector storage (16 files)
│   │   └── workflows/       # Workflow engine (30 files)
│   ├── pyproject.toml
│   └── alembic/             # Database migrations
├── deployment/              # Deployment configurations
│   ├── docker/              # Docker files
│   ├── kubernetes/          # K8s manifests
│   ├── environments/        # Environment configs
│   ├── scripts/             # Operations scripts
│   ├── healthchecks/        # Health check scripts
│   └── monitoring/          # Prometheus config
├── docs/                    # Documentation (19 files)
├── tests/                   # Test suite
│   └── backend/             # Backend tests (57 test files + 17 support)
├── agents/                  # Agent documentation
├── memory/                  # Memory documentation
├── rag/                     # RAG documentation
├── workflows/               # Workflow documentation
├── config/                  # Configuration files
├── scripts/                 # Utility scripts
├── frontend/                # Frontend (if applicable)
├── home/                    # Home directory
├── docker-compose.yml       # Docker Compose
├── README.md                # Project README
├── .env.example             # Environment template
└── .gitignore
```

## Total Counts

| Category | Count |
|----------|-------|
| Backend Python files | 466 |
| API route modules | 23 |
| API endpoints | 179 |
| ORM model classes | 12 |
| Test files | 57 |
| Test support files | 17 |
| Documentation files | 19 |
| Deployment files | 29 |
| Kubernetes manifests | 7 |
| Deployment scripts | 10 |
