# NOVA EVOLUTION BACKLOG

> Mission: Make NOVA CORE 100% operational through repair, integration, optimization, and stabilization.
> Last Updated: 2026-07-16

---

## PRIORITY 1 — CRITICAL (Chat, Memory, Projects, Goals, Tasks, Workflows, Command Center, Approvals)

### CHAT MODULE

| ID | Issue | Impact | Affected Modules | Proposed Solution | Difficulty | Priority |
|----|-------|--------|------------------|-------------------|------------|----------|
| C-001 | `/nova-web/chat` uses keyword matching, NOT the real LLM | Users get robotic, non-intelligent responses | Chat, Command Center, All AI features | Wire `/nova-web/chat` to use `ModelGateway.chat()` or `Kernel.execute()` instead of keyword detection | Medium | CRITICAL |
| C-002 | No conversation persistence — messages lost on page refresh | Users lose chat history | Chat, Memory | Implement conversation storage in PostgreSQL via existing `memory/conversation.py` | Medium | CRITICAL |
| C-003 | Two separate chat pages (`nova/page.tsx` and `chat/page.tsx`) with different implementations | Confusing UX, duplicated code | Chat, Frontend | Consolidate into single chat implementation; use `nova/page.tsx` as primary | Low | HIGH |
| C-004 | Chat page uses raw `fetch()` instead of NovaAPI client | Inconsistent API usage, no error handling | Chat, Frontend | Refactor to use `NovaAPI` client from `lib/api.ts` | Low | MEDIUM |

### MEMORY MODULE

| ID | Issue | Impact | Affected Modules | Proposed Solution | Difficulty | Priority |
|----|-------|--------|------------------|-------------------|------------|----------|
| M-001 | No unified persistent memory layer — data scattered across modules | Memory not retained across sessions | Memory, Chat, All modules | Create unified memory facade that coordinates `conversation_memory`, `long_term_memory`, `vector_memory`, `knowledge_graph` | High | CRITICAL |
| M-002 | Memory page shows status only, no actual memory management | Users cannot view/manage stored memories | Memory, Frontend | Add memory viewing, search, and deletion capabilities to memory page | Medium | HIGH |
| M-003 | Conversation memory not wired to chat | Chat conversations not stored | Memory, Chat | Wire chat endpoint to store conversations via `ConversationMemory` | Medium | CRITICAL |

### PROJECTS MODULE

| ID | Issue | Impact | Affected Modules | Proposed Solution | Difficulty | Priority |
|----|-------|--------|------------------|-------------------|------------|----------|
| P-001 | `novaWeb.createProject()` calls `POST /nova-web/projects` which doesn't exist | Cannot create projects from frontend | Projects, Frontend | Add `POST /nova-web/projects` endpoint or update frontend to use existing project creation endpoint | Low | HIGH |
| P-002 | Projects page doesn't show project details/tasks | Limited project management | Projects, Frontend | Enhance project detail view with tasks, milestones, and progress tracking | Medium | MEDIUM |

### GOALS MODULE

| ID | Issue | Impact | Affected Modules | Proposed Solution | Difficulty | Priority |
|----|-------|--------|------------------|-------------------|------------|----------|
| G-001 | `GET /api/v1/goals` requires `/{user_id}` but frontend doesn't pass it correctly | Goals page returns 404 | Goals, Frontend | Add default user_id handling in backend or update frontend to always pass user_id | Low | CRITICAL |
| G-002 | Goals not connected to projects/tasks | No goal → project → task hierarchy | Goals, Projects, Tasks | Implement goal-project-task linkage in backend | Medium | HIGH |

### TASKS MODULE

| ID | Issue | Impact | Affected Modules | Proposed Solution | Difficulty | Priority |
|----|-------|--------|------------------|-------------------|------------|----------|
| T-001 | Task creation button disabled ("Not yet implemented") | Users cannot create tasks | Tasks, Frontend | Implement task creation form and wire to `POST /api/v1/tasks` | Low | HIGH |
| T-002 | Tasks not linked to goals/projects | No traceability from goal to task | Tasks, Goals, Projects | Add goal_id/project_id foreign keys and UI filters | Medium | MEDIUM |

### WORKFLOWS MODULE

| ID | Issue | Impact | Affected Modules | Proposed Solution | Difficulty | Priority |
|----|-------|--------|------------------|-------------------|------------|----------|
| W-001 | Visual workflow builder is placeholder | Cannot design workflows visually | Workflows, Frontend | Either implement basic visual builder or remove the tab to avoid confusion | High | MEDIUM |
| W-002 | Workflow creation button exists but no form | Cannot create workflows from UI | Workflows, Frontend | Add workflow creation form | Medium | HIGH |

### COMMAND CENTER MODULE

| ID | Issue | Impact | Affected Modules | Proposed Solution | Difficulty | Priority |
|----|-------|--------|------------------|-------------------|------------|----------|
| CC-001 | Governor uses keyword matching, not AI | Strategic analysis is rule-based, not intelligent | Command Center, Chat, All AI | Wire Governor to use LLM for analysis via `ModelGateway` | High | CRITICAL |
| CC-002 | No dedicated Command Center page | Users cannot access full command center features | Command Center, Frontend | Create dedicated `/command-center` page or enhance nova dashboard | Medium | HIGH |

### APPROVALS MODULE

| ID | Issue | Impact | Affected Modules | Proposed Solution | Difficulty | Priority |
|----|-------|--------|------------------|-------------------|------------|----------|
| A-001 | `novaWeb.approvalHistory()` calls non-existent endpoint | Cannot view approval history | Approvals, Frontend | Add `GET /nova-web/approvals/history` endpoint | Low | MEDIUM |

---

## PRIORITY 2 — HIGH (Planner, Research, Reviewer, Executor, OpenCode, RAG, Knowledge Graph)

| ID | Issue | Impact | Affected Modules | Proposed Solution | Difficulty | Priority |
|----|-------|--------|------------------|-------------------|------------|----------|
| P2-001 | Assistant module exists but is not wired | Missing AI assistant capabilities | Assistant, All | Wire `assistant/` module in lifespan or remove dead code | High | HIGH |
| P2-002 | NovaOS module exists but is not initialized | Missing OS abstraction layer | NovaOS, All | Either wire `nova_os/` in lifespan or remove dead code | High | HIGH |
| P2-003 | RAG pipeline functional but not integrated with chat | Chat cannot leverage knowledge base | RAG, Chat | Add RAG context retrieval to chat endpoint | Medium | HIGH |
| P2-004 | Knowledge Graph not connected to memory | Entities/relationships not used in memory | Knowledge Graph, Memory | Wire KG extraction to memory storage | Medium | MEDIUM |

---

## PRIORITY 3 — MEDIUM (Dashboard, Observability, Diagnostics, Performance, Resilience)

| ID | Issue | Impact | Affected Modules | Proposed Solution | Difficulty | Priority |
|----|-------|--------|------------------|-------------------|------------|----------|
| P3-001 | Dashboard shows aggregated data but no real-time updates | Stale data displayed | Dashboard, Frontend | Add auto-refresh or WebSocket for live updates | Medium | MEDIUM |
| P3-002 | Observability page exists but limited actionable insights | Monitoring without action | Observability | Add alert thresholds and recommended actions | Low | LOW |

---

## PRIORITY 4 — LOW (Dead Code Cleanup, Architecture)

| ID | Issue | Impact | Affected Modules | Proposed Solution | Difficulty | Priority |
|----|-------|--------|------------------|-------------------|------------|----------|
| P4-001 | Dead Governor classes (orchestrator.py, autonomy/governor.py, nova_os/governor.py) | Code confusion, maintenance burden | Command Center, Autonomy, NovaOS | Delete dead code files | Low | LOW |
| P4-002 | `services/index.ts` — entirely broken legacy code | Dead code, potential confusion | Frontend | Delete `services/index.ts` | Low | LOW |
| P4-003 | WebSocket hooks defined but never used | Dead infrastructure | Frontend | Either implement WS endpoints or remove hooks | Low | LOW |
| P4-004 | Two API clients (`lib/api.ts` and `lib/nova-api.ts`) | Inconsistent API layer | Frontend | Consolidate into single API client | Medium | MEDIUM |
| P4-005 | Response shape mismatch — backend wraps in `{success, data}`, frontend expects raw | Data parsing issues | Frontend, Backend | Standardize response format across all endpoints | Medium | MEDIUM |
| P4-006 | Admin page response shape mismatch | Admin page broken | Admin, Frontend | Fix frontend to handle actual backend response format | Low | MEDIUM |
| P4-007 | Planning page response shape mismatch | Planning page broken | Planning, Frontend | Fix frontend to unwrap `{success, data}` | Low | MEDIUM |

---

## DAILY UTILIZATION CHECKLIST

Verify these workflows work end-to-end:

- [ ] User sends message in chat → NOVA responds intelligently (not keyword-matched)
- [ ] Chat conversation persists across page refreshes
- [ ] User creates a goal → goal appears in goals list
- [ ] User creates a project → project appears in projects list
- [ ] User creates a task → task appears in tasks list
- [ ] Goal → Project → Task hierarchy works
- [ ] User can view pending approvals
- [ ] User can approve/reject items
- [ ] Dashboard shows real-time system status
- [ ] Memory page shows stored conversations
- [ ] Navigation between pages doesn't lose state

---

## IMPLEMENTATION ROADMAP

### Phase 1: Critical Fixes (Week 1-2)
1. Wire `/nova-web/chat` to real LLM
2. Fix Goals page (user_id handling)
3. Fix Projects page (createProject endpoint)
4. Implement conversation persistence

### Phase 2: Integration (Week 3-4)
5. Unify memory layer
6. Wire Assistant module or remove dead code
7. Fix all response shape mismatches
8. Consolidate API clients

### Phase 3: Optimization (Week 5-6)
9. Clean up dead code (Governor classes, services/index.ts)
10. Implement task/goal/project linking
11. Add RAG context to chat
12. Enhance Command Center with AI

### Phase 4: Stabilization (Week 7-8)
13. End-to-end testing of all daily workflows
14. Performance optimization
15. Documentation updates
16. Final validation

---

## SUCCESS METRICS

NOVA CORE is considered complete when:

- [ ] Chat responds with AI-generated responses (not keyword-matched)
- [ ] Conversations persist across sessions
- [ ] Goals page works without 404 errors
- [ ] Projects can be created from frontend
- [ ] Tasks can be created from frontend
- [ ] Goal → Project → Task hierarchy is functional
- [ ] All Priority 1 pages load without errors
- [ ] Navigation between pages preserves state
- [ ] No dead code or broken endpoints
- [ ] Daily utilization workflows work end-to-end

---

## ABSOLUTE RULES

1. **NO NEW MODULES** — Only repair, integrate, optimize existing code
2. **NO NEW AGENTS** — Only fix existing agent coordination
3. **NO NEW ARCHITECTURES** — Only simplify existing architecture
4. **QUALITY OVER QUANTITY** — Make existing features work perfectly
5. **SIMPLICITY OVER COMPLEXITY** — Remove unnecessary abstractions
6. **DAILY UTILIZATION FIRST** — Fix what users actually need
