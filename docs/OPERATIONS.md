# Operations

## Startup

```bash
# Docker Compose
cd deployment/docker && docker-compose up -d

# Kubernetes
cd deployment/scripts && ./deploy.sh

# Development
cd deployment/scripts && ./start.sh
```

## Shutdown

```bash
# Docker Compose
cd deployment/docker && docker-compose down

# Kubernetes
kubectl delete -f deployment/kubernetes/

# Development
cd deployment/scripts && ./stop.sh
```

## Monitoring

### Health Endpoints
- `/health` — Basic health
- `/observability/health` — Detailed health
- `/observability/readiness` — Kubernetes readiness
- `/observability/liveness` — Kubernetes liveness

### Metrics
- `/observability/metrics` — Aggregated metrics
- `/observability/export/prometheus` — Prometheus format

### Dashboards
- Grafana: `http://localhost:3000` (default)

## Backups

```bash
# Backup database
cd deployment/scripts && ./backup.sh

# Restore database
cd deployment/scripts && ./restore.sh
```

## Logging

Structured JSON logging via `python-json-logger`. Configure log level via `LOG_LEVEL` environment variable.

## Scaling

Scale workers via API:
```bash
# Scale up
curl -X POST /scaling/scale-up

# Scale down
curl -X POST /scaling/scale-down
```
