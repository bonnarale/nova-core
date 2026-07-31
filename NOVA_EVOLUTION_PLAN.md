# NOVA EVOLUTION v1.0 — Strategic Project Plan

> Mission: Make NOVA CORE 100% operational through repair, integration, optimization, and stabilization.
> Created: 2026-07-16
> Status: ACTIVE

---

## EXECUTIVE SUMMARY

NOVA CORE is an AI operating system with 37 backend modules, 35 API routers, and 30+ frontend pages. The system has extensive infrastructure but critical gaps in integration and usability.

**Key Finding**: The system has all the building blocks but they're not properly connected. The chat doesn't use AI, goals page is broken, and conversations aren't persisted.

**Mission**: Fix what exists. Don't build new modules. Make daily utilization work perfectly.

---

## CURRENT STATE ASSESSMENT

### What Works ✅
- Backend infrastructure (PostgreSQL, Redis, ChromaDB, Ollama)
- 35 API routers all mounted and returning data
- CRUD operations for goals, tasks, workflows, agents, tools
- Model Gateway connected to Ollama
- RAG pipeline functional
- Vector memory operational
- Event system working
- Security engine functional
- 30+ frontend pages connected to real endpoints

### What's Broken ❌
1. **Chat doesn't use AI** — `/nova-web/chat` uses keyword matching, not the real LLM
2. **Goals page returns 404** — Missing user_id handling
3. **No conversation persistence** — Messages lost on page refresh
4. **Projects can't be created** — Frontend calls non-existent endpoint
5. **Tasks can't be created** — Button disabled
6. **Two API clients** — `lib/api.ts` and `lib/nova-api.ts` coexist
7. **Response shape mismatches** — Backend wraps in `{success, data}`, frontend expects raw
8. **Dead code everywhere** — Unused modules, broken hooks, legacy services

### What's Half-Done ⚠️
- Assistant module exists but not wired
- NovaOS module exists but not initialized
- WebSocket hooks defined but unused
- Visual workflow builder is placeholder

---

## PRIORITY 1 — CRITICAL FIXES

### C-001: Wire Chat to Real LLM
**Current**: `/nova-web/chat` does keyword matching
**Target**: `/nova-web/chat` uses `ModelGateway.chat()` or `Kernel.execute()`
**Impact**: Users get intelligent responses instead of robotic keyword matches
**Difficulty**: Medium
**Files to modify**: `backend/app/api/v1/routes/nova_web.py`

### C-002: Implement Conversation Persistence
**Current**: Conversations lost on page refresh
**Target**: Conversations stored in PostgreSQL via `ConversationMemory`
**Impact**: Users never lose chat history
**Difficulty**: Medium
**Files to modify**: `backend/app/api/v1/routes/nova_web.py`, `backend/app/memory/conversation.py`

### C-003: Fix Goals Page
**Current**: `GET /api/v1/goals` requires `/{user_id}` but frontend doesn't pass it
**Target**: Goals page works without 404 errors
**Impact**: Users can track strategic objectives
**Difficulty**: Low
**Files to modify**: `backend/app/api/v1/routes/goals.py` or `frontend/app/goals/page.tsx`

### C-004: Fix Projects Page
**Current**: `novaWeb.createProject()` calls `POST /nova-web/projects` which doesn't exist
**Target**: Users can create projects from frontend
**Impact**: Project management works end-to-end
**Difficulty**: Low
**Files to modify**: `backend/app/api/v1/routes/nova_web.py`

### C-005: Enable Task Creation
**Current**: Task creation button disabled
**Target**: Users can create tasks from frontend
**Impact**: Task management works end-to-end
**Difficulty**: Low
**Files to modify**: `frontend/app/tasks/page.tsx`

---

## PRIORITY 2 — INTEGRATION

### M-001: Unify Memory Layer
**Current**: Memory scattered across conversation_memory, long_term_memory, vector_memory, knowledge_graph
**Target**: Single memory facade that coordinates all memory systems
**Impact**: Consistent memory across all modules
**Difficulty**: High
**Files to create**: `backend/app/memory/unified.py`

### M-002: Wire Assistant Module
**Current**: `assistant/` module exists but not initialized in lifespan
**Target**: Assistant module wired and functional
**Impact**: Full AI assistant capabilities
**Difficulty**: High
**Files to modify**: `backend/app/main.py`

### M-003: Fix Response Shape Mismatches
**Current**: Backend wraps in `{success, data}`, frontend expects raw
**Target**: Consistent response format across all endpoints
**Impact**: No more data parsing issues
**Difficulty**: Medium
**Files to modify**: Multiple frontend and backend files

### M-004: Consolidate API Clients
**Current**: Two API clients (`lib/api.ts` and `lib/nova-api.ts`)
**Target**: Single API client
**Impact**: Consistent API layer, easier maintenance
**Difficulty**: Medium
**Files to modify**: `frontend/lib/api.ts`, `frontend/lib/nova-api.ts`

---

## PRIORITY 3 — CLEANUP

### P4-001: Delete Dead Code
**Files to delete**:
- `backend/app/command_center/orchestrator.py` (duplicate Governor)
- `backend/app/autonomy/governor.py` (unused AutonomyGovernor)
- `backend/app/nova_os/governor.py` (unused NovaGovernor)
- `frontend/services/index.ts` (broken legacy code)
- `frontend/hooks/index.ts` (unused WebSocket hooks)

### P4-002: Remove Unused Modules
**Options**:
1. Wire `nova_os/` module in lifespan
2. OR delete `nova_os/` entirely
3. Wire `assistant/` module in lifespan
4. OR delete `assistant/` entirely

**Recommendation**: Wire both modules — they provide valuable capabilities

---

## IMPLEMENTATION ROADMAP

### Phase 1: Critical Fixes (Week 1-2)
1. ✅ Wire `/nova-web/chat` to real LLM
2. ✅ Implement conversation persistence
3. ✅ Fix Goals page
4. ✅ Fix Projects page
5. ✅ Enable task creation

### Phase 2: Integration (Week 3-4)
6. ✅ Unify memory layer
7. ✅ Wire Assistant module
8. ✅ Fix response shape mismatches
9. ✅ Consolidate API clients

### Phase 3: Cleanup (Week 5-6)
10. ✅ Delete dead code
11. ✅ Remove unused modules or wire them
12. ✅ End-to-end testing

### Phase 4: Optimization (Week 7-8)
13. ✅ Performance optimization
14. ✅ Documentation updates
15. ✅ Final validation

---

## SUCCESS CRITERIA

NOVA CORE is considered complete when:

- [ ] Chat responds with AI-generated responses (not keyword-matched)
- [ ] Conversations persist across sessions
- [ ] Goals page works without 404 errors
- [ ] Projects can be created from frontend
- [ ] Tasks can be created from frontend
- [ ] Goal → Project → Task hierarchy works
- [ ] All Priority 1 pages load without errors
- [ ] Navigation between pages preserves state
- [ ] No dead code or broken endpoints
- [ ] Daily utilization workflows work end-to-end

---

## DAILY UTILIZATION CHECKLIST

Verify these workflows work:

1. User sends message in chat → NOVA responds intelligently
2. Chat conversation persists across page refreshes
3. User creates a goal → goal appears in goals list
4. User creates a project → project appears in projects list
5. User creates a task → task appears in tasks list
6. Goal → Project → Task hierarchy works
7. User can view pending approvals
8. User can approve/reject items
9. Dashboard shows real-time system status
10. Memory page shows stored conversations
11. Navigation between pages doesn't lose state

---

## ABSOLUTE RULES

1. **NO NEW MODULES** — Only repair, integrate, optimize existing code
2. **NO NEW AGENTS** — Only fix existing agent coordination
3. **NO NEW ARCHITECTURES** — Only simplify existing architecture
4. **QUALITY OVER QUANTITY** — Make existing features work perfectly
5. **SIMPLICITY OVER COMPLEXITY** — Remove unnecessary abstractions
6. **DAILY UTILIZATION FIRST** — Fix what users actually need

---

## TESTING STRATEGY

### Backend Tests
```bash
cd backend && python -m pytest ../tests/backend/ --tb=short -q
```

### Frontend Tests
```bash
cd frontend && node node_modules/jest/bin/jest.js
```

### Manual Testing
1. Start NOVA: `make start`
2. Open frontend: http://localhost:3000
3. Test chat: Send a message, verify AI response
4. Test goals: Create a goal, verify it appears
5. Test projects: Create a project, verify it appears
6. Test tasks: Create a task, verify it appears
7. Test navigation: Switch between pages, verify state preserved

---

## REFERENCES

- **Architecture Document**: `ARCHITECTURE.md` — Complete system map
- **Evolution Backlog**: `NOVA_EVOLUTION_BACKLOG.md` — Detailed issue tracking
- **Backend Tests**: `tests/backend/` — 80+ test files
- **Frontend Tests**: `frontend/tests/` — 5 test files
- **Makefile**: `Makefile` — Build, test, and run commands

---

## NEXT STEPS

1. **Read this plan** — Understand the current state and priorities
2. **Start with Phase 1** — Fix critical issues first
3. **Test after each change** — Run `make test-backend` and `make test-frontend`
4. **Validate daily workflows** — Use the Daily Utilization Checklist
5. **Update this document** — Mark completed items and add new issues found

---

**Remember**: The goal is NOT to build new features. The goal is to make existing features work perfectly.

**Quality has absolute priority over quantity.**
**Simplicity has absolute priority over complexity.**
**Daily utilization has absolute priority over new features.**
