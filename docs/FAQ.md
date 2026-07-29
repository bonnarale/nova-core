# FAQ

### What Python version is required?

Python 3.12 or higher (3.13 recommended). The codebase uses `from __future__ import annotations` throughout.

### How do I run the tests?

```bash
cd backend
python -m pytest ../tests/backend/ -v
```

### How do I add a new subsystem?

1. Create `backend/app/my_subsystem/` with `__init__.py`, `base.py` (ABCs), `models.py` (dataclasses), `enums.py`
2. Implement the provider in a separate file
3. Create a factory in `factory.py`
4. Add API routes in `backend/app/api/v1/routes/my_subsystem.py`
5. Register the router in `backend/app/api/v1/router.py`
6. Add tests in `tests/backend/test_my_subsystem.py`

### How do I add a new API endpoint?

1. Create or edit a route file in `backend/app/api/v1/routes/`
2. Define the endpoint with `@router.get/post/put/delete`
3. If creating a new route module, register it in `router.py`

### What database does NOVA CORE use?

PostgreSQL via asyncpg and SQLAlchemy 2.0 async. ChromaDB is used for vector storage.

### How does authentication work?

Bearer tokens (JWT) for API access. API keys for service-to-service. RBAC for authorization.

### Can I use NOVA CORE without all subsystems?

Yes. Each subsystem is independently testable via mocks and in-memory implementations.

### How do I contribute?

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

### What's the test coverage target?

>95% unit coverage. Critical paths at 100%.

### How do I deploy to production?

See [DEPLOYMENT.md](DEPLOYMENT.md) for Docker and Kubernetes instructions.

### Where are the API docs?

When running: `http://localhost:8000/docs` (Swagger UI)
