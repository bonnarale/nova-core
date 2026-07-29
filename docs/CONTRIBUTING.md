# Contributing

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a feature branch: `git checkout -b feature/my-feature`
4. Make your changes
5. Run tests: `cd backend && python -m pytest ../tests/backend/ -v`
6. Run linter: `cd deployment && ./scripts/lint.sh`
7. Commit: `git commit -m "feat: add my feature"`
8. Push: `git push origin feature/my-feature`
9. Open a Pull Request

## Code Standards

- Python 3.13+ with `from __future__ import annotations`
- Full type annotations on all functions and methods
- ABCs for all provider interfaces
- `dataclass` for domain models, Pydantic for API schemas
- `logging.getLogger(__name__)` for logging
- No breaking changes to existing APIs
- All new code must have tests

## Architecture Patterns

- **Provider Pattern** — ABC in `base.py`, implementation in separate file
- **Factory Pattern** — Static creation methods in `factory.py`
- **Registry Pattern** — Central component registry
- **Event-Driven** — Subsystem communication via events

## Pull Request Requirements

- All tests pass
- Code follows existing conventions
- Documentation updated if needed
- No regressions in existing functionality
