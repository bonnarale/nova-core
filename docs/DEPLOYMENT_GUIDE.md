# NOVA CORE v1.0.0 — Deployment Guide

**Version:** 1.0.0
**Last Updated:** July 14, 2026

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Local Development Setup](#2-local-development-setup)
3. [Docker Compose Deployment](#3-docker-compose-deployment)
4. [Kubernetes Deployment](#4-kubernetes-deployment)
5. [Environment Configuration](#5-environment-configuration)
6. [Database Setup](#6-database-setup)
7. [Health Checks](#7-health-checks)
8. [Monitoring Setup](#8-monitoring-setup)
9. [Scaling Configuration](#9-scaling-configuration)
10. [Backup and Recovery](#10-backup-and-recovery)

---

## 1. Prerequisites

### Required Software

| Software | Minimum Version | Purpose |
|----------|----------------|---------|
| Docker | 24.0+ | Container runtime |
| Docker Compose | 2.20+ | Multi-container orchestration |
| kubectl | 1.28+ | Kubernetes CLI |
| Python | 3.12+ | Backend runtime |
| Node.js | 18+ | Frontend build |

### Verify Prerequisites

```bash
# Check Docker
docker --version
docker compose version

# Check kubectl
kubectl version --client

# Check Python
python3 --version

# Check Node.js
node --version
npm --version
```

### System Requirements

| Environment | CPU | RAM | Disk |
|-------------|-----|-----|------|
| Development | 2 cores | 4 GB | 20 GB |
| Staging | 4 cores | 8 GB | 50 GB |
| Production | 8+ cores | 16+ GB | 100+ GB SSD |

---

## 2. Local Development Setup

### Clone and Install

```bash
# Clone repository
git clone <repository-url> nova-core
cd nova-core

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -e ".[dev]"

# Install frontend dependencies
cd frontend && npm install && cd ..
```

### Start Local Services

```bash
# Start PostgreSQL, Redis, ChromaDB
docker compose -f docker-compose.dev.yml up -d

# Run database migrations
alembic upgrade head

# Start the backend
python -m nova_core.main

# Start the frontend (separate terminal)
cd frontend && npm run dev
```

### Verify Local Setup

```bash
# Backend health check
curl http://localhost:8000/health

# Frontend
open http://localhost:3000
```

---

## 3. Docker Compose Deployment

### Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: "3.9"

services:
  nova-api:
    image: nova-core/api:1.0.0
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://nova:${DB_PASSWORD}@postgres:5432/nova_core
      - REDIS_URL=redis://redis:6379/0
      - CHROMA_URL=http://chroma:8000
      - OLLAMA_URL=http://ollama:11434
      - JWT_SECRET=${JWT_SECRET}
      - API_KEY_SALT=${API_KEY_SALT}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      chroma:
        condition: service_started
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 2G
        reservations:
          cpus: "1"
          memory: 1G

  nova-frontend:
    image: nova-core/frontend:1.0.0
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - nova-api
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=nova_core
      - POSTGRES_USER=nova
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nova -d nova_core"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  chroma:
    image: chromadb/chroma:0.5.0
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  chroma_data:
  ollama_data:
```

### Deploy with Docker Compose

```bash
# Generate secrets
export DB_PASSWORD=$(openssl rand -hex 32)
export JWT_SECRET=$(openssl rand -hex 32)
export API_KEY_SALT=$(openssl rand -hex 16)

# Pull images
docker compose -f docker-compose.prod.yml pull

# Start all services
docker compose -f docker-compose.prod.yml up -d

# Verify
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs nova-api
```

---

## 4. Kubernetes Deployment

### Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: nova-core
  labels:
    app.kubernetes.io/name: nova-core
    app.kubernetes.io/version: "1.0.0"
```

### Secrets

```bash
kubectl create namespace nova-core

kubectl create secret generic nova-secrets \
  --namespace=nova-core \
  --from-literal=database-url="postgresql://nova:${DB_PASSWORD}@postgres:5432/nova_core" \
  --from-literal=jwt-secret="${JWT_SECRET}" \
  --from-literal=api-key-salt="${API_KEY_SALT}"
```

### Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nova-api
  namespace: nova-core
  labels:
    app: nova-api
    version: "1.0.0"
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nova-api
  template:
    metadata:
      labels:
        app: nova-api
        version: "1.0.0"
    spec:
      containers:
        - name: nova-api
          image: nova-core/api:1.0.0
          ports:
            - containerPort: 8000
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: nova-secrets
                  key: database-url
            - name: JWT_SECRET
              valueFrom:
                secretKeyRef:
                  name: nova-secrets
                  key: jwt-secret
            - name: REDIS_URL
              value: "redis://redis:6379/0"
            - name: CHROMA_URL
              value: "http://chroma:8000"
          resources:
            requests:
              cpu: "500m"
              memory: "512Mi"
            limits:
              cpu: "2"
              memory: "2Gi"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nova-api
  namespace: nova-core
spec:
  selector:
    app: nova-api
  ports:
    - port: 80
      targetPort: 8000
  type: ClusterIP
```

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: nova-api-hpa
  namespace: nova-core
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: nova-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

### Deploy

```bash
kubectl apply -f namespace.yaml
kubectl apply -f secrets.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f hpa.yaml

# Verify
kubectl get pods -n nova-core
kubectl logs -f deployment/nova-api -n nova-core
```

---

## 5. Environment Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `REDIS_URL` | Yes | — | Redis connection string |
| `CHROMA_URL` | No | `http://localhost:8000` | ChromaDB endpoint |
| `OLLAMA_URL` | No | `http://localhost:11434` | Ollama endpoint |
| `JWT_SECRET` | Yes | — | JWT signing secret (min 32 chars) |
| `API_KEY_SALT` | Yes | — | API key hashing salt |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `CORS_ORIGINS` | No | `*` | Allowed CORS origins |
| `RATE_LIMIT_PER_MINUTE` | No | `60` | API rate limit |
| `WORKERS` | No | `4` | Number of worker processes |

### Configuration Files

```
config/
├── settings.py          # Application settings
├── logging.json         # Logging configuration
├── prometheus.yml       # Prometheus configuration
└── alertmanager.yml     # Alertmanager configuration
```

---

## 6. Database Setup

### Initial Setup

```bash
# Create database
createdb nova_core

# Run migrations
alembic upgrade head

# Seed initial data (optional)
python -m nova_core.scripts.seed
```

### Migration Commands

```bash
# Check current revision
alembic current

# Upgrade to latest
alembic upgrade head

# Downgrade one step
alembic downgrade -1

# Generate new migration
alembic revision --autogenerate -m "description"
```

### Connection Pooling

Default pool settings in production:

```
pool_size: 20
max_overflow: 10
pool_timeout: 30
pool_recycle: 1800
pool_pre_ping: true
```

---

## 7. Health Checks

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Liveness check — returns 200 if service is running |
| `/ready` | GET | Readiness check — returns 200 if service can accept traffic |
| `/metrics` | GET | Prometheus metrics endpoint |

### Manual Verification

```bash
# Liveness
curl -s http://localhost:8000/health | jq .

# Readiness
curl -s http://localhost:8000/ready | jq .

# Metrics
curl -s http://localhost:8000/metrics
```

### Expected Responses

**Liveness:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 12345
}
```

**Readiness:**
```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "chroma": "ok"
  }
}
```

---

## 8. Monitoring Setup

### Prometheus Configuration

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "nova-api"
    static_configs:
      - targets: ["nova-api:8000"]
    metrics_path: "/metrics"
```

### Grafana Dashboards

Import the NOVA CORE dashboard using the provided `grafana/dashboard.json`:

1. Open Grafana at `http://localhost:3000`
2. Navigate to Dashboards → Import
3. Upload `grafana/dashboard.json`
4. Select Prometheus data source

### Key Metrics to Monitor

| Metric | Alert Threshold | Description |
|--------|----------------|-------------|
| `nova_api_requests_total` | >1000 req/s sustained | Request throughput |
| `nova_api_request_duration_seconds` | p99 > 2s | Response latency |
| `nova_api_errors_total` | >5% error rate | Error rate |
| `nova_memory_usage_bytes` | >80% of limit | Memory usage |
| `nova_cpu_usage_seconds_total` | >80% of limit | CPU usage |
| `nova_db_pool_active` | >80% pool exhausted | Database connection pool |

---

## 9. Scaling Configuration

### Horizontal Scaling

```bash
# Manual scale
kubectl scale deployment/nova-api --replicas=5 -n nova-core

# Auto-scaling (HPA)
kubectl get hpa -n nova-core
```

### Vertical Scaling

Update resource limits in the deployment manifest:

```yaml
resources:
  requests:
    cpu: "1"
    memory: "1Gi"
  limits:
    cpu: "4"
    memory: "4Gi"
```

### Worker Scaling

```bash
# Scale background workers
kubectl scale deployment/nova-workers --replicas=3 -n nova-core
```

### Scaling Thresholds

| Metric | Scale Up | Scale Down |
|--------|----------|------------|
| CPU | >70% for 5min | <30% for 10min |
| Memory | >80% for 5min | <40% for 10min |
| Request Queue | >100 pending | <10 pending |

---

## 10. Backup and Recovery

### Database Backups

```bash
# Manual backup
pg_dump -U nova -d nova_core > backup_$(date +%Y%m%d_%H%M%S).sql

# Automated backup (cron)
0 2 * * * pg_dump -U nova -d nova_core | gzip > /backups/nova_core_$(date +\%Y\%m\%d).sql.gz
```

### Redis Backups

```bash
# Trigger background save
redis-cli BGSAVE

# Copy dump file
cp /data/dump.rdb /backups/redis_$(date +%Y%m%d).rdb
```

### Recovery Procedures

```bash
# PostgreSQL recovery
psql -U nova -d nova_core < backup.sql

# Redis recovery
redis-cli SHUTDOWN NOSAVE
cp /backups/dump.rdb /data/dump.rdb
redis-server
```

### Backup Schedule

| Component | Frequency | Retention | Method |
|-----------|-----------|-----------|--------|
| PostgreSQL | Daily 02:00 UTC | 30 days | pg_dump |
| Redis | Every 6 hours | 7 days | BGSAVE |
| ChromaDB | Daily 03:00 UTC | 14 days | Volume snapshot |
| Config files | On change | Indefinite | Git |

### Disaster Recovery

1. **RTO (Recovery Time Objective):** < 1 hour
2. **RPO (Recovery Point Objective):** < 24 hours
3. **Failover:** Automated with health checks
4. **Data Replication:** PostgreSQL streaming replication (production)

---

## Appendix: Port Reference

| Service | Port | Protocol | Description |
|---------|------|----------|-------------|
| Frontend | 3000 | HTTP | Next.js application |
| API | 8000 | HTTP | NOVA CORE API |
| PostgreSQL | 5432 | TCP | Database |
| Redis | 6379 | TCP | Cache / Message broker |
| ChromaDB | 8001 | HTTP | Vector database |
| Ollama | 11434 | HTTP | LLM inference |
