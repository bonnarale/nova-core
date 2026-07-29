# NOVA CORE

> An intelligent, multi-agent cognitive platform built with Python 3.13, FastAPI, and async-first architecture.

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/fastapi-0.115.0-009688.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## Quick Start

### Prerequisites

- Python >= 3.12
- PostgreSQL (via asyncpg)
- Redis
- ChromaDB (vector storage)

### Development

```bash
# Install dependencies
cd backend && pip install -e .

# Run development server
cd deployment && ./scripts/start.sh

# Run tests
cd backend && python -m pytest ../tests/backend/ -v
```

### Docker

```bash
cd deployment/docker
docker-compose up -d
```

## Architecture

NOVA CORE follows a modular, clean-architecture design with 30 subsystems:

| Subsystem | Description |
|-----------|-------------|
| Cognitive Engine | Core reasoning and decision-making |
| Memory System | Short-term and long-term memory management |
| Learning Engine | Knowledge extraction and consolidation |
| Knowledge Engine | Knowledge graph operations |
| Reasoning Engine | Chain-of-thought and multi-strategy reasoning |
| Goal Engine | Goal decomposition and tracking |
| Task Engine | Task lifecycle management |
| Planning Engine | Task planning and replanning |
| Execution Engine | Step-by-step execution |
| Multi-Agent Runtime | Agent coordination and dispatch |
| Tool System | External tool integration |
| Model Gateway | LLM provider abstraction |
| RAG & Retrieval | Document retrieval and context building |
| Vector Memory | ChromaDB-backed vector storage |
| Event System | Pub/sub event bus with middleware |
| Scheduler | Cron and trigger-based job scheduling |
| Workflow Engine | Visual workflow execution |
| Plugin System | Hot-loadable plugin architecture |
| Security | Auth, RBAC, API keys, audit |
| Observability | Metrics, tracing, logging, alerts |
| API Platform | FastAPI REST endpoints |
| Database Architecture | SQLAlchemy async ORM |
| Deployment | Docker, Kubernetes, health checks |
| Scaling | Load balancing, worker pools, autoscaling |
| Testing | Comprehensive test infrastructure |
| Future Roadmap | Feature flags, experiments, compatibility |

## Project Structure

```
nova-core/
├── backend/              # Python backend (FastAPI)
│   ├── app/
│   │   ├── agents/       # Multi-agent runtime
│   │   ├── api/          # REST API (v1 routes)
│   │   ├── cognitive/    # Cognitive engine
│   │   ├── core/         # Core utilities
│   │   ├── db/           # Database layer
│   │   ├── deployment/   # Deployment management
│   │   ├── events/       # Event system
│   │   ├── future/       # Future roadmap infrastructure
│   │   ├── knowledge_graph/  # Knowledge graph
│   │   ├── learning/     # Learning engine
│   │   ├── long_term_memory/ # Long-term memory
│   │   ├── memory/       # Memory management
│   │   ├── models/       # Model gateway
│   │   ├── observability/# Metrics, tracing, logging
│   │   ├── plugins/      # Plugin system
│   │   ├── rag/          # RAG pipeline
│   │   ├── reasoning/    # Reasoning engine
│   │   ├── scaling/      # Scaling infrastructure
│   │   ├── scheduler/    # Job scheduler
│   │   ├── security/     # Security layer
│   │   ├── tools/        # Tool system
│   │   ├── vector_memory/# Vector storage
│   │   └── workflows/    # Workflow engine
│   └── pyproject.toml
├── deployment/           # Deployment configs
│   ├── docker/           # Docker & Docker Compose
│   ├── kubernetes/       # K8s manifests
│   ├── environments/     # Environment configs
│   ├── scripts/          # Operations scripts
│   └── monitoring/       # Prometheus config
├── docs/                 # Documentation
├── tests/                # Test suite
│   └── backend/          # Backend tests
└── README.md
```

## Documentation

- [Architecture](ARCHITECTURE.md) — System design and patterns
- [System Overview](SYSTEM_OVERVIEW.md) — High-level component map
- [Directory Structure](DIRECTORY_STRUCTURE.md) — Full project tree
- [API Reference](API_REFERENCE.md) — REST endpoint documentation
- [Database](DATABASE.md) — ORM models and persistence
- [Security](SECURITY.md) — Authentication and authorization
- [Observability](OBSERVABILITY.md) — Monitoring and alerting
- [Deployment](DEPLOYMENT.md) — Production deployment guide
- [Scaling](SCALING.md) — Scaling strategies
- [Testing](TESTING.md) — Test infrastructure guide
- [Contributing](CONTRIBUTING.md) — Development guidelines
- [Development](DEVELOPMENT.md) — Local development setup
- [Operations](OPERATIONS.md) — Operational procedures
- [Troubleshooting](TROUBLESHOOTING.md) — Common issues
- [Changelog](CHANGELOG.md) — Version history
- [Roadmap](ROADMAP.md) — Feature roadmap
- [Glossary](GLOSSARY.md) — Terminology
- [FAQ](FAQ.md) — Frequently asked questions

## License

MIT License — See [LICENSE](../LICENSE) for details.
