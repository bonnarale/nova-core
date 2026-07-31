# NOVA CORE v1.0.0 — Maintenance Guide

**Version:** 1.0.0
**Last Updated:** July 14, 2026

---

## Table of Contents

1. [Monitoring and Alerting](#1-monitoring-and-alerting)
2. [Log Management](#2-log-management)
3. [Database Maintenance](#3-database-maintenance)
4. [Cache Management](#4-cache-management)
5. [Performance Tuning](#5-performance-tuning)
6. [Security Updates](#6-security-updates)
7. [Backup Procedures](#7-backup-procedures)
8. [Recovery Procedures](#8-recovery-procedures)
9. [Scaling Operations](#9-scaling-operations)
10. [Version Upgrades](#10-version-upgrades)

---

## 1. Monitoring and Alerting

### Prometheus Metrics

Access metrics at `http://localhost:9090` (Prometheus) or `http://localhost:3000` (Grafana).

**Key Metrics:**

```bash
# Request rate (requests/second)
rate(nova_api_requests_total[5m])

# Error rate (%)
rate(nova_api_errors_total[5m]) / rate(nova_api_requests_total[5m]) * 100

# Response time (p99)
histogram_quantile(0.99, rate(nova_api_request_duration_seconds_bucket[5m]))

# Memory usage (bytes)
nova_memory_usage_bytes

# Database connection pool
nova_db_pool_active / nova_db_pool_total * 100
```

### Alert Rules

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| HighErrorRate | Error rate >5% for 5min | P2 | Investigate logs |
| HighLatency | p99 >2s for 5min | P2 | Check resource usage |
| HighMemory | Usage >80% for 10min | P3 | Scale or investigate leak |
| DatabasePoolExhausted | Pool >90% for 5min | P1 | Scale database |
| PodRestart | >3 restarts in 1 hour | P2 | Check logs, restart |
| DiskSpaceLow | <20% remaining | P2 | Clean up or expand |

### Health Check Schedule

| Check | Frequency | Endpoint | Expected |
|-------|-----------|----------|----------|
| Liveness | Every 10s | `/health` | 200 OK |
| Readiness | Every 5s | `/ready` | 200 OK |
| Database | Every 30s | `/ready` | `database: ok` |
| Redis | Every 30s | `/ready` | `redis: ok` |
| ChromaDB | Every 60s | `/ready` | `chroma: ok` |

---

## 2. Log Management

### Log Levels

| Level | Usage | Retention |
|-------|-------|-----------|
| ERROR | System errors, exceptions | 30 days |
| WARN | Deprecations, potential issues | 30 days |
| INFO | Request logs, state changes | 90 days |
| DEBUG | Development debugging | 7 days |

### Log Commands

```bash
# View API logs (Docker)
docker compose logs -f nova-api

# View logs with grep
docker compose logs nova-api 2>&1 | grep ERROR

# View logs (Kubernetes)
kubectl logs -f deployment/nova-api -n nova-core

# View previous container logs
kubectl logs --previous deployment/nova-api -n nova-core
```

### Log Rotation

Configure log rotation to prevent disk exhaustion:

```json
{
  "version": 1,
  "rotation": {
    "max_size": "100MB",
    "max_files": 10,
    "compress": true
  }
}
```

### Structured Logging

All logs are structured JSON for easy parsing:

```bash
# Filter by request ID
cat app.log | jq 'select(.request_id == "req_abc123")'

# Filter by error level
cat app.log | jq 'select(.level == "ERROR")'

# Filter by timestamp range
cat app.log | jq 'select(.timestamp > "2026-07-14T00:00:00Z" and .timestamp < "2026-07-15T00:00:00Z")'
```

---

## 3. Database Maintenance

### Routine Tasks

#### Weekly

```bash
# Analyze table statistics
psql -U nova -d nova_core -c "ANALYZE;"

# Check for bloat
psql -U nova -d nova_core -c "
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

#### Monthly

```bash
# Vacuum full (reclaim space)
psql -U nova -d nova_core -c "VACUUM (VERBOSE, ANALYZE);"

# Reindex
psql -U nova -d nova_core -c "REINDEX SCHEMA public;"
```

### Connection Pool Monitoring

```bash
# Check active connections
psql -U nova -d nova_core -c "
SELECT count(*), state 
FROM pg_stat_activity 
WHERE datname = 'nova_core' 
GROUP BY state;"

# Check for long-running queries
psql -U nova -d nova_core -c "
SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
FROM pg_stat_activity 
WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '5 minutes';"
```

### Migration Management

```bash
# Check current migration
alembic current

# View migration history
alembic history

# Generate new migration
alembic revision --autogenerate -m "description"

# Apply pending migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

### Database Cleanup

```bash
# Clean old session data (older than 30 days)
psql -U nova -d nova_core -c "
DELETE FROM sessions WHERE created_at < NOW() - INTERVAL '30 days';"

# Clean expired API keys
psql -U nova -d nova_core -c "
DELETE FROM api_keys WHERE expires_at < NOW();"

# Clean audit logs (older than 1 year)
psql -U nova -d nova_core -c "
DELETE FROM audit_logs WHERE created_at < NOW() - INTERVAL '1 year';"
```

---

## 4. Cache Management

### Redis Operations

```bash
# Check Redis memory
redis-cli INFO memory | grep used_memory_human

# Check key count
redis-cli DBSIZE

# Monitor cache hit rate
redis-cli INFO stats | grep keyspace

# Flush cache (careful!)
redis-cli FLUSHDB

# Flush specific namespace
redis-cli KEYS "nova:cache:*" | xargs redis-cli DEL
```

### Cache Invalidation

```bash
# Invalidate user cache
redis-cli DEL "nova:cache:user:<user_id>"

# Invalidate session cache
redis-cli DEL "nova:cache:session:<session_id>"

# Invalidate all cache (nuclear option)
redis-cli FLUSHDB
```

### Cache Warming

After deployment or cache flush, warm critical caches:

```bash
# Warm user sessions
python -m nova_core.scripts.warm_cache --type=sessions

# Warm knowledge graph
python -m nova_core.scripts.warm_cache --type=knowledge

# Warm all caches
python -m nova_core.scripts.warm_cache --type=all
```

---

## 5. Performance Tuning

### API Performance

```bash
# Profile slow endpoints
python -m nova_core.scripts.profile --threshold=100ms

# Check database query performance
python -m nova_core.scripts.query_stats

# Analyze request patterns
python -m nova_core.scripts.request_analysis
```

### Database Tuning

```postgresql
-- Optimize query plans
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET work_mem = '256MB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';

-- Reload configuration
SELECT pg_reload_conf();
```

### Worker Tuning

```bash
# Scale workers based on load
kubectl scale deployment/nova-workers --replicas=<count> -n nova-core

# Monitor worker queue
redis-cli LLEN "nova:queue:tasks"
```

### Memory Optimization

| Setting | Default | Recommended |
|---------|---------|-------------|
| Python GC threshold | 700 | 1000 |
| Max workers | 4 | 2 * CPU cores |
| DB pool size | 10 | 20 |
| Redis maxmemory | 1GB | 4GB |

---

## 6. Security Updates

### Dependency Updates

```bash
# Check for vulnerable dependencies
pip-audit

# Update Python dependencies
pip install --upgrade -r requirements.txt

# Update frontend dependencies
cd frontend && npm audit fix

# Update Docker base images
docker compose pull
```

### Security Patches

```bash
# Check for OS security updates (Ubuntu)
sudo apt update && sudo apt list --upgradable

# Apply security updates
sudo apt upgrade -y
```

### Certificate Renewal

```bash
# Check certificate expiry
openssl x509 -in /etc/letsencrypt/live/nova.example.com/cert.pem -noout -dates

# Renew Let's Encrypt
sudo certbot renew

# Verify renewal
curl -vI https://nova.example.com 2>&1 | grep "expire date"
```

### Secret Rotation

Rotate secrets quarterly:

```bash
# Generate new secrets
export NEW_JWT_SECRET=$(openssl rand -hex 32)
export NEW_DB_PASSWORD=$(openssl rand -hex 32)

# Update secrets
kubectl create secret generic nova-secrets \
  --namespace=nova-core \
  --from-literal=jwt-secret="$NEW_JWT_SECRET" \
  --from-literal=database-password="$NEW_DB_PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -

# Rolling restart to pick up new secrets
kubectl rollout restart deployment/nova-api -n nova-core
```

---

## 7. Backup Procedures

### Automated Backups

```bash
# PostgreSQL (daily cron)
0 2 * * * /opt/nova-core/scripts/backup-db.sh

# Redis (every 6 hours)
0 */6 * * * /opt/nova-core/scripts/backup-redis.sh

# Full system (weekly)
0 3 * * 0 /opt/nova-core/scripts/backup-full.sh
```

### Manual Backups

```bash
# PostgreSQL
pg_dump -U nova -d nova_core -F c -f /backups/nova_core_$(date +%Y%m%d).dump

# Redis
redis-cli BGSAVE
cp /data/dump.rdb /backups/redis_$(date +%Y%m%d).rdb

# ChromaDB
docker compose exec chroma tar czf /backups/chroma_$(date +%Y%m%d).tar.gz /chroma/chroma

# Configuration
tar czf /backups/config_$(date +%Y%m%d).tar.gz config/ docker-compose.prod.yml .env
```

### Backup Verification

```bash
# Verify PostgreSQL backup
pg_restore -l /backups/nova_core_20260714.dump

# Test restore to temp database
createdb nova_core_test
pg_restore -d nova_core_test /backups/nova_core_20260714.dump
psql -d nova_core_test -c "SELECT count(*) FROM users;"
dropdb nova_core_test
```

### Backup Retention

| Backup Type | Frequency | Retention | Storage |
|-------------|-----------|-----------|---------|
| PostgreSQL | Daily | 30 days | Local + S3 |
| Redis | Every 6 hours | 7 days | Local |
| ChromaDB | Weekly | 4 weeks | S3 |
| Configuration | On change | Indefinite | Git |

---

## 8. Recovery Procedures

### PostgreSQL Recovery

```bash
# Stop the application
kubectl scale deployment/nova-api --replicas=0 -n nova-core

# Drop and recreate database
dropdb nova_core
createdb nova_core

# Restore from backup
pg_restore -d nova_core /backups/nova_core_20260714.dump

# Apply pending migrations
alembic upgrade head

# Restart application
kubectl scale deployment/nova-api --replicas=3 -n nova-core
```

### Redis Recovery

```bash
# Stop Redis
docker compose stop redis

# Replace dump file
cp /backups/redis_20260714.rdb /data/dump.rdb

# Start Redis
docker compose start redis

# Verify
redis-cli DBSIZE
```

### Full System Recovery

```bash
# 1. Restore PostgreSQL
pg_restore -d nova_core /backups/nova_core_latest.dump

# 2. Restore Redis
cp /backups/redis_latest.rdb /data/dump.rdb

# 3. Restore ChromaDB
docker compose exec chroma tar xzf /backups/chroma_latest.tar.gz -C /

# 4. Restore configuration
tar xzf /backups/config_latest.tar.gz

# 5. Restart all services
docker compose down
docker compose up -d

# 6. Verify
curl http://localhost:8000/health
```

### Disaster Recovery

| Scenario | RTO | RPO | Procedure |
|----------|-----|-----|-----------|
| Database corruption | 1 hour | 24 hours | Restore from daily backup |
| Application crash | 5 minutes | 0 | Auto-restart via orchestrator |
| Full system failure | 2 hours | 24 hours | Full restore from backups |
| Data breach | 4 hours | 0 | Isolate, investigate, restore |

---

## 9. Scaling Operations

### Horizontal Scaling

```bash
# Scale API
kubectl scale deployment/nova-api --replicas=<count> -n nova-core

# Scale workers
kubectl scale deployment/nova-workers --replicas=<count> -n nova-core

# Check HPA
kubectl get hpa -n nova-core
```

### Vertical Scaling

```yaml
# Update deployment resources
resources:
  requests:
    cpu: "2"
    memory: "2Gi"
  limits:
    cpu: "4"
    memory: "4Gi"
```

### Database Scaling

```bash
# Add read replica
pg_basebackup -h primary -D /replica/data -U replica -P -v -R

# Configure connection pooling (PgBouncer)
# Edit pgbouncer.ini
```

### Auto-Scaling Policies

| Metric | Scale Up Threshold | Scale Down Threshold |
|--------|--------------------|----------------------|
| CPU | >70% for 5 min | <30% for 10 min |
| Memory | >80% for 5 min | <40% for 10 min |
| Queue Depth | >100 messages | <10 messages |
| Request Rate | >500 req/s | <100 req/s |

---

## 10. Version Upgrades

### Pre-Upgrade Checklist

- [ ] Read release notes for target version
- [ ] Check for breaking changes
- [ ] Back up database
- [ ] Back up Redis
- [ ] Back up configuration
- [ ] Test upgrade in staging environment
- [ ] Schedule maintenance window
- [ ] Notify stakeholders

### Upgrade Procedure

```bash
# 1. Backup
/opt/nova-core/scripts/backup-full.sh

# 2. Pull new version
git pull origin main

# 3. Update dependencies
pip install -e ".[dev]"
cd frontend && npm install && cd ..

# 4. Run migrations
alembic upgrade head

# 5. Build new Docker image
docker compose build nova-api

# 6. Rolling restart
kubectl rollout restart deployment/nova-api -n nova-core

# 7. Verify
curl http://localhost:8000/health
kubectl logs -f deployment/nova-api -n nova-core
```

### Rollback Procedure

```bash
# 1. Restore previous version
git checkout v1.0.0

# 2. Restore database (if needed)
pg_restore -d nova_core /backups/nova_core_pre_upgrade.dump

# 3. Rebuild and restart
docker compose build nova-api
kubectl rollout restart deployment/nova-api -n nova-core

# 4. Verify
curl http://localhost:8000/health
```

### Version Compatibility

| Version | Database | Redis | API Compatibility |
|---------|----------|-------|-------------------|
| v1.0.0 | v1.0 | v7+ | v1.0 |
| v1.0.x | v1.0 | v7+ | v1.0 (backward) |
| v1.x.0 | v1.0+ | v7+ | v1.x (backward) |
| v2.0.0 | v2.0 | v7+ | v2.0 (breaking) |
