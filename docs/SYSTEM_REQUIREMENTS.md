# NOVA CORE v1.0.0 — System Requirements

**Version:** 1.0.0
**Last Updated:** July 14, 2026

---

## Hardware Requirements

### Minimum (Development)

| Resource | Requirement |
|----------|-------------|
| CPU | 2 cores |
| RAM | 4 GB |
| Disk | 20 GB |
| Network | 100 Mbps |

### Recommended (Staging / Small Production)

| Resource | Requirement |
|----------|-------------|
| CPU | 4 cores |
| RAM | 8 GB |
| Disk | 50 GB |
| Network | 1 Gbps |

### Production (High Availability)

| Resource | Requirement |
|----------|-------------|
| CPU | 8+ cores |
| RAM | 16+ GB |
| Disk | 100+ GB SSD |
| Network | 1 Gbps+ |

---

## Software Requirements

### Runtime

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.12+ | Backend runtime |
| Node.js | 18+ | Frontend build / SDK |
| npm | 9+ | Package management |

### Container Runtime

| Software | Version | Purpose |
|----------|---------|---------|
| Docker | 24.0+ | Container runtime |
| Docker Compose | 2.20+ | Multi-container orchestration |

### Orchestration

| Software | Version | Purpose |
|----------|---------|---------|
| kubectl | 1.28+ | Kubernetes CLI |
| Helm | 3.12+ | Package management (optional) |

### Development Tools

| Software | Version | Purpose |
|----------|---------|---------|
| Git | 2.40+ | Version control |
| Python venv | — | Virtual environments |
| pytest | 8.0+ | Testing framework |
| Alembic | 1.12+ | Database migrations |

---

## Network Requirements

### Ports

| Port | Service | Protocol | Direction |
|------|---------|----------|-----------|
| 80 | Frontend (production) | HTTP | Inbound |
| 443 | Frontend (TLS) | HTTPS | Inbound |
| 3000 | Frontend (development) | HTTP | Inbound |
| 8000 | NOVA CORE API | HTTP | Inbound |
| 5432 | PostgreSQL | TCP | Internal |
| 6379 | Redis | TCP | Internal |
| 8001 | ChromaDB | HTTP | Internal |
| 11434 | Ollama | HTTP | Internal |
| 9090 | Prometheus | HTTP | Internal |
| 3001 | Grafana | HTTP | Internal |

### Network Policies

- API port (8000) must be accessible from the load balancer
- Database port (5432) must be restricted to internal network only
- Redis port (6379) must be restricted to internal network only
- External access should go through HTTPS (port 443)

---

## External Services

### Required

| Service | Version | Purpose | Connection |
|---------|---------|---------|------------|
| PostgreSQL | 16+ | Primary database | `DATABASE_URL` |
| Redis | 7+ | Cache, message broker, rate limiting | `REDIS_URL` |
| ChromaDB | 0.5+ | Vector database for RAG | `CHROMA_URL` |

### Optional

| Service | Version | Purpose | Connection |
|---------|---------|---------|------------|
| Ollama | Latest | Local LLM inference | `OLLAMA_URL` |
| Prometheus | 2.45+ | Metrics collection | Scraping endpoint |
| Grafana | 10.0+ | Metrics visualization | HTTP |

### External API Dependencies

| Provider | Purpose | Required |
|----------|---------|----------|
| Ollama | LLM inference | Yes (default provider) |
| OpenAI | LLM inference (optional) | No |
| Anthropic | LLM inference (optional) | No |

---

## Browser Requirements (Frontend)

| Browser | Minimum Version |
|---------|----------------|
| Chrome | 100+ |
| Firefox | 100+ |
| Safari | 15+ |
| Edge | 100+ |

### Mobile Requirements (Flutter)

| Platform | Minimum Version |
|----------|----------------|
| iOS | 14.0+ |
| Android | API 21+ (5.0) |

---

## Performance Baselines

| Metric | Target | Measured |
|--------|--------|----------|
| App Startup | <5.0s | 2.3s |
| NOVA OS Boot | <1.0ms | 0.14ms |
| Event Throughput | >100K events/sec | >500K events/sec |
| RAG Query Latency | <10ms | 2.49ms |
| API Token Operations | <1.0ms | 0.14ms |
| API Response Time (p95) | <200ms | <100ms |
| Database Query (p95) | <50ms | <30ms |

---

## Resource Sizing Guide

### Small Deployment (1–50 users)

| Component | CPU | RAM | Instances |
|-----------|-----|-----|-----------|
| API | 1 core | 1 GB | 1 |
| Frontend | 0.5 core | 512 MB | 1 |
| PostgreSQL | 1 core | 2 GB | 1 |
| Redis | 0.5 core | 512 MB | 1 |
| **Total** | **3 cores** | **4 GB** | — |

### Medium Deployment (50–500 users)

| Component | CPU | RAM | Instances |
|-----------|-----|-----|-----------|
| API | 2 cores | 2 GB | 3 |
| Frontend | 1 core | 1 GB | 2 |
| PostgreSQL | 2 cores | 4 GB | 1 (+ replica) |
| Redis | 1 core | 1 GB | 1 |
| ChromaDB | 1 core | 2 GB | 1 |
| **Total** | **13 cores** | **16 GB** | — |

### Large Deployment (500+ users)

| Component | CPU | RAM | Instances |
|-----------|-----|-----|-----------|
| API | 4 cores | 4 GB | 10 |
| Frontend | 2 cores | 2 GB | 5 |
| PostgreSQL | 4 cores | 8 GB | 3 (HA cluster) |
| Redis | 2 cores | 2 GB | 3 (Sentinel) |
| ChromaDB | 2 cores | 4 GB | 3 |
| Workers | 2 cores | 2 GB | 5 |
| **Total** | **56 cores** | **80 GB** | — |
