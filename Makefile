.PHONY: start stop restart status diagnose health validate test test-backend test-frontend build lint clean help dev-backend dev-frontend

SHELL := /bin/bash
.DEFAULT_GOAL := help

PYTHON := $(shell \
	if [ -x .venv/bin/python ]; then echo ".venv/bin/python"; \
	elif [ -x venv/bin/python ]; then echo "venv/bin/python"; \
	elif command -v python3 >/dev/null 2>&1; then echo "python3"; \
	elif command -v python >/dev/null 2>&1; then echo "python"; \
	else echo "python"; \
	fi)

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# OFFICIAL STARTUP — Single entry point
# ============================================================================

start: ## Start NOVA (single official entry point)
	@echo ""
	@echo "========================================================================"
	@echo "  NOVA CORE — Starting"
	@echo "========================================================================"
	@echo ""
	@mkdir -p tmp
	@echo "  [1/4] Validating environment..."
	@$(PYTHON) scripts/nova_diagnose.py --start --quick 2>&1 || { echo ""; echo "  Fix issues above and try again."; exit 1; }
	@echo ""
	@echo "  [2/4] Stopping existing services..."
	@-tmux kill-session -t nova-backend 2>/dev/null || true
	@-tmux kill-session -t nova-frontend 2>/dev/null || true
	@-pkill -f 'uvicorn app.main' 2>/dev/null || true
	@sleep 2
	@echo ""
	@echo "  [3/4] Starting services..."
	@tmux new-session -d -s nova-backend 'cd $(CURDIR)/backend && $(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1 | tee $(CURDIR)/tmp/backend.log'
	@echo "    Backend started in tmux session 'nova-backend'"
	@tmux new-session -d -s nova-frontend 'cd $(CURDIR)/frontend && npx next dev --port 3000 2>&1 | tee $(CURDIR)/tmp/frontend.log'
	@echo "    Frontend started in tmux session 'nova-frontend'"
	@echo ""
	@echo "  [4/4] Waiting for services to become healthy..."
	@sleep 20
	@echo ""
	@echo "  Validating..."
	@$(PYTHON) scripts/nova_diagnose.py --quick 2>&1 | sed 's/^/    /'
	@echo ""
	@echo "========================================================================"
	@BACKEND_OK=0; FRONTEND_OK=0; \
	if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then BACKEND_OK=1; fi; \
	if curl -sf http://127.0.0.1:3000/ >/dev/null 2>&1; then FRONTEND_OK=1; fi; \
	if [ $$BACKEND_OK -eq 1 ] && [ $$FRONTEND_OK -eq 1 ]; then \
		echo "  NOVA IS OPERATIONAL"; \
		echo "  Backend:  http://localhost:8000"; \
		echo "  Frontend: http://localhost:3000"; \
		echo "  API Docs: http://localhost:8000/docs"; \
	elif [ $$BACKEND_OK -eq 1 ]; then \
		echo "  NOVA IS PARTIALLY OPERATIONAL (frontend degraded)"; \
		echo "  Backend:  http://localhost:8000"; \
	else \
		echo "  NOVA IS NOT OPERATIONAL — Check: cat tmp/backend.log"; \
	fi; \
	echo "========================================================================"
	@echo ""

stop: ## Stop all NOVA services
	@echo "Stopping NOVA CORE..."
	@-tmux kill-session -t nova-backend 2>/dev/null || true
	@-tmux kill-session -t nova-frontend 2>/dev/null || true
	@-pkill -f 'uvicorn app.main' 2>/dev/null || true
	@echo "NOVA CORE stopped."

restart: stop start ## Restart NOVA

# ============================================================================
# STATUS & DIAGNOSTICS
# ============================================================================

status: ## Check NOVA status
	@echo ""
	@echo "NOVA CORE Status:"
	@echo "========================================================================"
	@BACKEND_OK=0; FRONTEND_OK=0; \
	if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then \
		BACKEND_OK=1; echo "  Backend:  RUNNING"; \
	else \
		echo "  Backend:  STOPPED"; \
	fi; \
	if curl -sf http://127.0.0.1:3000/ >/dev/null 2>&1; then \
		FRONTEND_OK=1; echo "  Frontend: RUNNING"; \
	else \
		echo "  Frontend: STOPPED"; \
	fi; \
	echo ""; \
	if [ $$BACKEND_OK -eq 1 ]; then \
		echo "  Backend Health:"; \
		curl -s http://127.0.0.1:8000/health 2>/dev/null | sed 's/^/    /'; \
	fi; \
	echo ""; \
	if [ $$BACKEND_OK -eq 1 ] && [ $$FRONTEND_OK -eq 1 ]; then \
		echo "  Verdict: NOVA IS OPERATIONAL"; \
		echo "  URLs: http://localhost:3000 | http://localhost:8000/docs"; \
	elif [ $$BACKEND_OK -eq 1 ]; then \
		echo "  Verdict: NOVA IS PARTIALLY OPERATIONAL (frontend degraded)"; \
	else \
		echo "  Verdict: NOVA IS NOT OPERATIONAL"; \
	fi; \
	echo "========================================================================"
	@echo ""

diagnose: ## Run full operational diagnostics
	@$(PYTHON) scripts/nova_diagnose.py

health: ## Quick health check
	@$(PYTHON) scripts/nova_diagnose.py --quick

validate: ## Alias for diagnose
	@$(PYTHON) scripts/nova_diagnose.py

# ============================================================================
# TESTS
# ============================================================================

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests
	@echo "Running backend tests..."
	@cd backend && $(PYTHON) -m pytest ../tests/backend/ --tb=short -q --ignore=../tests/backend/test_performance.py --ignore=../tests/backend/test_system_integration.py

test-frontend: ## Run frontend tests
	@echo "Running frontend tests..."
	@cd frontend && node node_modules/jest/bin/jest.js --passWithNoTests

# ============================================================================
# BUILD & LINT
# ============================================================================

build: ## Build frontend for production
	@echo "Building frontend..."
	@cd frontend && npx next build

lint: ## Lint frontend
	@cd frontend && npx next lint

clean: ## Clean build artifacts
	@-tmux kill-session -t nova-backend 2>/dev/null || true
	@-tmux kill-session -t nova-frontend 2>/dev/null || true
	@-pkill -f 'uvicorn app.main' 2>/dev/null || true
	@rm -rf frontend/.next tmp
	@echo "Cleaned."

# ============================================================================
# DEVELOPMENT (foreground, for debugging)
# ============================================================================

dev-backend: ## Start only backend (foreground, for debugging)
	@mkdir -p tmp
	@echo "Starting backend on http://localhost:8000 ..."
	@cd backend && $(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

dev-frontend: ## Start only frontend (foreground, for debugging)
	@echo "Starting frontend on http://localhost:3000 ..."
	@cd frontend && npx next dev --port 3000
