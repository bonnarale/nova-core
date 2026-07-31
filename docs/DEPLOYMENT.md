# Deployment

## Overview

NOVA CORE supports Docker, Docker Compose, and Kubernetes deployments.

## Docker

### Build
```bash
cd deployment/docker
docker build -t nova-core-backend -f Dockerfile ../backend
```

### Run
```bash
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://... \
  -e REDIS_URL=redis://localhost:6379 \
  nova-core-backend
```

### Multi-stage Build
The Dockerfile uses multi-stage builds:
1. **Builder stage** — Installs dependencies
2. **Runtime stage** — Copies only production artifacts

## Docker Compose

```bash
cd deployment/docker
docker-compose up -d
```

Services: `backend`, `postgres`, `chromadb`, `redis`, `prometheus`, `grafana`

## Kubernetes

### Manifests

| File | Purpose |
|------|---------|
| `deployment.yml` | Deployment with probes and resources |
| `service.yml` | ClusterIP service |
| `ingress.yml` | Ingress with TLS |
| `configmap.yml` | Configuration data |
| `secret.yml` | Secrets |
| `pvc.yml` | Persistent volume claims |
| `hpa.yml` | Horizontal Pod Autoscaler |

### Deploy
```bash
cd deployment/scripts
./deploy.sh
```

## Environments

| Environment | Config File |
|-------------|-------------|
| Development | `.env.development` |
| Testing | `.env.testing` |
| Staging | `.env.staging` |
| Production | `.env.production` |

## Health Checks

| Script | Purpose |
|--------|---------|
| `healthcheck.sh` | Container health check |
| `readiness.sh` | Readiness probe |
| `liveness.sh` | Liveness probe |

## Operations Scripts

| Script | Purpose |
|--------|---------|
| `build.sh` | Build Docker image |
| `start.sh` | Start development server |
| `stop.sh` | Stop development server |
| `test.sh` | Run test suite |
| `lint.sh` | Run linter |
| `format.sh` | Format code |
| `migrate.sh` | Run migrations |
| `backup.sh` | Backup database |
| `restore.sh` | Restore database |
| `deploy.sh` | Deploy to Kubernetes |
