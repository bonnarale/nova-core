# Multi-stage build for NOVA CORE — Production
FROM python:3.13-slim AS base
LABEL maintainer="NOVA CORE Team"
LABEL description="NOVA CORE AI Operating System"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ─── Build stage ──────────────────────────────────────────────────────────
FROM base AS builder

RUN pip install --upgrade pip setuptools wheel

COPY backend/pyproject.toml backend/README.md /app/
COPY backend/app /app/app

RUN pip install --no-cache-dir ".[dev]" 2>/dev/null || pip install --no-cache-dir fastapi uvicorn pydantic sqlalchemy aiosqlite httpx redis

# ─── Production stage ────────────────────────────────────────────────────
FROM base AS production

RUN groupadd -r nova && useradd -r -g nova -d /app -s /sbin/nologin nova

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

RUN chown -R nova:nova /app

USER nova

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/health'); r.raise_for_status()" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
