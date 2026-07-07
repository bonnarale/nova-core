# NOVA CORE

Production foundation for NOVA CORE, an AI operating system built on FastAPI, PostgreSQL, Redis, ChromaDB, Ollama, Open WebUI, n8n, Docker Compose, and Traefik.

## Requirements

- Docker Engine
- Docker Compose v2

## Quick Start

```bash
cp .env.example .env
docker compose up -d
```

## Services

| Service | URL | Purpose |
| --- | --- | --- |
| Traefik | http://localhost:8080 | Reverse proxy dashboard |
| Backend API | http://api.localhost | FastAPI application |
| Backend Docs | http://api.localhost/docs | OpenAPI documentation |
| Frontend | http://app.localhost | Frontend placeholder |
| Open WebUI | http://webui.localhost | Ollama UI |
| n8n | http://n8n.localhost | Workflow automation |

## Backend

The FastAPI service includes:

- Structured JSON logging
- Environment-driven configuration
- PostgreSQL connectivity
- Redis connectivity
- ChromaDB HTTP client
- Ollama HTTP client
- Readiness and health checks
- OpenAPI documentation at `/docs`

## Operations

Persistent state is stored in named Docker volumes:

- `postgres_data`
- `redis_data`
- `chroma_data`
- `ollama_data`
- `open_webui_data`
- `n8n_data`

All application services run on the private `nova_internal` Docker network and are exposed through Traefik on `nova_public` where needed.

