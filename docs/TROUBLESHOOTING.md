# Troubleshooting

## Common Issues

### Database Connection

**Symptom**: `ConnectionRefusedError` or timeout
**Fix**:
1. Verify PostgreSQL is running: `pg_isready`
2. Check `DATABASE_URL` in `.env`
3. Verify credentials and database exists

### Redis Connection

**Symptom**: `ConnectionError` for Redis
**Fix**:
1. Verify Redis is running: `redis-cli ping`
2. Check `REDIS_URL` in `.env`

### ChromaDB

**Symptom**: Vector operations fail
**Fix**:
1. Check ChromaDB is running
2. Verify `CHROMA_URL` in `.env`

### Test Failures

**Symptom**: Tests hang or timeout
**Fix**:
1. Run with `-x` flag: `pytest -x`
2. Check for async fixture issues
3. Verify `pytest-asyncio` is installed

### Import Errors

**Symptom**: `ModuleNotFoundError`
**Fix**:
1. Verify all dependencies installed: `pip install -e .`
2. Check Python version: `python --version`

## Debug Mode

```bash
LOG_LEVEL=DEBUG python -m uvicorn app.main:app --reload
```

## Health Checks

```bash
# Quick health check
curl http://localhost:8000/health

# Detailed observability
curl http://localhost:8000/observability/diagnostics
```
