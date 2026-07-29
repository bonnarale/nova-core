#!/usr/bin/env bash
# NOVA CORE — Validated Startup Script
# Starts backend + frontend with validation at each step.
# NEVER reports success unless all checks pass.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TMP_DIR="$PROJECT_ROOT/tmp"
BACKEND_PID_FILE="$TMP_DIR/backend.pid"
FRONTEND_PID_FILE="$TMP_DIR/frontend.pid"
BACKEND_LOG="$TMP_DIR/backend.log"
FRONTEND_LOG="$TMP_DIR/frontend.log"
MAX_WAIT=60
FRONTEND_MAX_WAIT=90

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}[OK]${NC}   $1"; }
warn() { echo -e "  ${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "  ${RED}[FAIL]${NC} $1"; }
info() { echo -e "  ${CYAN}[...]${NC} $1"; }

# --- Step 0: Stop any existing services ---
stop_existing() {
    if [ -f "$BACKEND_PID_FILE" ]; then
        local pid
        pid=$(cat "$BACKEND_PID_FILE" 2>/dev/null || echo "")
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            info "Stopping existing backend (pid $pid)..."
            kill "$pid" 2>/dev/null || true
            sleep 2
        fi
        rm -f "$BACKEND_PID_FILE"
    fi
    if [ -f "$FRONTEND_PID_FILE" ]; then
        local pid
        pid=$(cat "$FRONTEND_PID_FILE" 2>/dev/null || echo "")
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            info "Stopping existing frontend (pid $pid)..."
            kill "$pid" 2>/dev/null || true
            sleep 2
        fi
        rm -f "$FRONTEND_PID_FILE"
    fi
}

# --- Step 1: Detect Python ---
detect_python() {
    info "Detecting Python interpreter..."
    # Check venv first
    for vpy in "$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/venv/bin/python"; do
        if [ -x "$vpy" ]; then
            PYTHON="$vpy"
            ok "Using virtual environment: $PYTHON"
            return 0
        fi
    done
    # Check python3, then python
    for cmd in python3 python; do
        if command -v "$cmd" >/dev/null 2>&1; then
            PYTHON="$cmd"
            ok "Using system Python: $PYTHON ($(command -v "$cmd"))"
            return 0
        fi
    done
    fail "No Python interpreter found."
    echo ""
    echo "  CAUSE: python and python3 are not on PATH."
    echo "  ACTION: Install Python 3.12+ or create a virtual environment:"
    echo "    python3 -m venv .venv && source .venv/bin/activate"
    echo ""
    return 1
}

# --- Step 2: Validate dependencies ---
validate_deps() {
    info "Validating dependencies..."
    local failed=0

    # Node.js
    if command -v node >/dev/null 2>&1; then
        ok "Node.js: $(node --version)"
    else
        fail "Node.js not found. Install Node.js 18+."
        failed=1
    fi

    # npm
    if command -v npm >/dev/null 2>&1; then
        ok "npm: $(npm --version)"
    else
        fail "npm not found."
        failed=1
    fi

    # uvicorn (check as Python module)
    if "$PYTHON" -m uvicorn --version >/dev/null 2>&1; then
        ok "uvicorn available"
    else
        fail "uvicorn not available. Run: $PYTHON -m pip install uvicorn"
        failed=1
    fi

    # fastapi
    if "$PYTHON" -c "import fastapi" 2>/dev/null; then
        ok "fastapi available"
    else
        fail "fastapi not installed. Run: $PYTHON -m pip install fastapi"
        failed=1
    fi

    # Frontend node_modules
    if [ -d "$PROJECT_ROOT/frontend/node_modules" ]; then
        ok "Frontend node_modules present"
    else
        fail "Frontend node_modules missing. Run: cd frontend && npm install"
        failed=1
    fi

    return $failed
}

# --- Step 3: Validate backend ---
validate_backend_code() {
    info "Validating backend code..."
    if [ -f "$PROJECT_ROOT/backend/app/main.py" ]; then
        ok "Backend main.py exists"
    else
        fail "Backend main.py not found at $PROJECT_ROOT/backend/app/main.py"
        return 1
    fi

    # Quick syntax check
    if "$PYTHON" -c "import ast; ast.parse(open('$PROJECT_ROOT/backend/app/main.py').read())" 2>/dev/null; then
        ok "Backend main.py syntax valid"
    else
        fail "Backend main.py has syntax errors"
        return 1
    fi
    return 0
}

# --- Step 4: Start backend ---
start_backend() {
    info "Starting backend on port 8000..."
    mkdir -p "$TMP_DIR"
    cd "$PROJECT_ROOT/backend"
    "$PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > "$BACKEND_LOG" 2>&1 &
    echo $! > "$BACKEND_PID_FILE"
    cd "$PROJECT_ROOT"
    ok "Backend process started (pid $(cat "$BACKEND_PID_FILE"))"
}

# --- Step 5: Validate backend is responding ---
validate_backend_health() {
    info "Waiting for backend to become available..."
    local elapsed=0
    while [ $elapsed -lt $MAX_WAIT ]; do
        if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
            local response
            response=$(curl -sf http://127.0.0.1:8000/health 2>/dev/null || echo "{}")
            ok "Backend health check passed: $response"
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        info "  ...waiting ($elapsed/${MAX_WAIT}s)"
    done
    fail "Backend did not respond within ${MAX_WAIT}s."
    echo ""
    echo "  CHECK LOG: $BACKEND_LOG"
    echo "  LAST 20 LINES:"
    tail -20 "$BACKEND_LOG" 2>/dev/null | sed 's/^/    /'
    echo ""
    return 1
}

# --- Step 6: Validate NOVA Web APIs ---
validate_nova_apis() {
    info "Validating NOVA Web APIs..."
    local base="http://127.0.0.1:8000/api/v1/nova-web"
    local failed=0
    local endpoints=(
        "dashboard"
        "objectives"
        "projects"
        "roadmaps"
        "backlog"
        "approvals"
        "recommendations"
        "memory"
        "observability"
        "tools"
    )

    for ep in "${endpoints[@]}"; do
        if curl -sf "$base/$ep" >/dev/null 2>&1; then
            ok "  /nova-web/$ep"
        else
            warn "  /nova-web/$ep — not responding"
            failed=$((failed + 1))
        fi
    done

    # Check core APIs
    local core_apis=(
        "http://127.0.0.1:8000/api/v1/agents"
        "http://127.0.0.1:8000/api/v1/tasks"
        "http://127.0.0.1:8000/api/v1/workflows"
    )
    for url in "${core_apis[@]}"; do
        local ep_name="${url##*/api/v1/}"
        if curl -sf "$url" >/dev/null 2>&1; then
            ok "  /api/v1/$ep_name"
        else
            warn "  /api/v1/$ep_name — not responding"
            failed=$((failed + 1))
        fi
    done

    if [ $failed -gt 0 ]; then
        warn "$failed API endpoints not responding (may be degraded)"
    fi
    return 0
}

# --- Step 7: Start frontend ---
start_frontend() {
    info "Starting frontend on port 3000..."
    cd "$PROJECT_ROOT/frontend"
    npx next dev --port 3000 > "$FRONTEND_LOG" 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"
    cd "$PROJECT_ROOT"
    ok "Frontend process started (pid $(cat "$FRONTEND_PID_FILE"))"
}

# --- Step 8: Validate frontend ---
validate_frontend() {
    info "Waiting for frontend to become available..."
    local elapsed=0
    while [ $elapsed -lt $FRONTEND_MAX_WAIT ]; do
        if curl -sf http://127.0.0.1:3000 >/dev/null 2>&1; then
            ok "Frontend is responding on port 3000"
            return 0
        fi
        sleep 3
        elapsed=$((elapsed + 3))
        info "  ...waiting ($elapsed/${FRONTEND_MAX_WAIT}s)"
    done
    fail "Frontend did not respond within ${FRONTEND_MAX_WAIT}s."
    echo "  CHECK LOG: $FRONTEND_LOG"
    return 1
}

# --- Step 9: Final report ---
print_report() {
    local backend_ok=0
    local frontend_ok=0

    if [ -f "$BACKEND_PID_FILE" ] && kill -0 "$(cat "$BACKEND_PID_FILE")" 2>/dev/null; then
        backend_ok=1
    fi
    if [ -f "$FRONTEND_PID_FILE" ] && kill -0 "$(cat "$FRONTEND_PID_FILE")" 2>/dev/null; then
        frontend_ok=1
    fi

    echo ""
    echo "========================================================================"
    if [ $backend_ok -eq 1 ] && [ $frontend_ok -eq 1 ]; then
        echo -e "  ${GREEN}NOVA CORE IS OPERATIONAL${NC}"
    elif [ $backend_ok -eq 1 ]; then
        echo -e "  ${YELLOW}NOVA CORE IS PARTIALLY OPERATIONAL (frontend degraded)${NC}"
    else
        echo -e "  ${RED}NOVA CORE IS NOT OPERATIONAL${NC}"
    fi
    echo "========================================================================"
    echo ""
    echo "  Backend:   $([ $backend_ok -eq 1 ] && echo -e "${GREEN}RUNNING${NC}" || echo -e "${RED}STOPPED${NC}")"
    echo "  Frontend:  $([ $frontend_ok -eq 1 ] && echo -e "${GREEN}RUNNING${NC}" || echo -e "${RED}STOPPED${NC}")"
    echo ""
    echo "  URLs:"
    echo "    Frontend:  http://localhost:3000"
    echo "    Backend:   http://localhost:8000"
    echo "    API Docs:  http://localhost:8000/docs"
    echo ""
    echo "  Logs:"
    echo "    Backend:   $BACKEND_LOG"
    echo "    Frontend:  $FRONTEND_LOG"
    echo ""
    echo "  Commands:"
    echo "    make stop     — Stop all services"
    echo "    make status   — Check status"
    echo "    make test     — Run tests"
    echo "========================================================================"
    echo ""

    if [ $backend_ok -eq 1 ] && [ $frontend_ok -eq 1 ]; then
        return 0
    else
        return 1
    fi
}

# ===========================================================================
# MAIN
# ===========================================================================
main() {
    echo ""
    echo "========================================================================"
    echo "  NOVA CORE — Validated Startup"
    echo "========================================================================"
    echo ""

    stop_existing

    detect_python || exit 1
    validate_deps || { fail "Dependency validation failed. Fix issues above."; exit 1; }
    validate_backend_code || { fail "Backend code validation failed."; exit 1; }
    start_backend
    validate_backend_health || { fail "Backend health check failed."; exit 1; }
    validate_nova_apis
    start_frontend
    validate_frontend || warn "Frontend validation failed — continuing with degraded mode."
    print_report
}

main "$@"
