# Proposal: Visual Workflow Execution & Real-Time Monitoring

## Intent

Connect the workflow detail page (`/workflows/[id]`) to the existing backend execution endpoints so users can start workflows, monitor progress in real-time, and control running executions (pause/resume/cancel).

## Scope

### In Scope
1. **Execution Controls** — Start, pause, resume, cancel buttons on workflow detail page
2. **Real-Time Event Stream** — Poll `GET /executions/{id}/events` and display events as they arrive
3. **Execution History** — List past executions with status, duration, step progress
4. **Visual Status Indicators** — Color-coded step status (running=blue, completed=green, failed=red, pending=gray)
5. **API Client Completion** — Add missing methods: `startExecution`, `getExecutionEvents`, `executeAction`, `deleteWorkflow`, `listExecutions`

### Out of Scope
- Visual drag-and-drop workflow builder (future task)
- Database persistence (in-memory is fine for now)
- SSE/WebSocket real-time (polling is sufficient for MVP)
- Workflow editing/update UI

## Business Value

Currently the backend has 18 functional endpoints but the frontend can't use them. This bridges the gap — turning the workflow feature from "can list definitions" into "can actually run and monitor workflows".

## Technical Approach

### Frontend Changes

**Files to modify:**
- `frontend/lib/api.ts` — Add missing API methods
- `frontend/app/workflows/[id]/page.tsx` — Add execution controls, event stream, history
- `frontend/types/index.ts` — Add proper WorkflowExecution and WorkflowEvent types

**New components (minimal):**
- `ExecutionControls` — Button group for start/pause/resume/cancel
- `EventStream` — Scrollable list of execution events with timestamps
- `ExecutionHistory` — Table of past executions
- `StepStatusBadge` — Color-coded status indicator

**Approach:**
- Use SWR's `mutate` for optimistic updates after actions
- Poll events every 2s while execution is RUNNING, pause when COMPLETED/FAILED
- Reuse existing `useApi` hook pattern
- Keep changes minimal — inline components in the page file where possible

### Backend Changes
None required — all endpoints are functional.

### Risk Assessment
- **Low risk** — Frontend-only changes, no backend modification
- **No graph library needed** — Focusing on execution monitoring, not visual building
- **In-memory persistence** — Data lost on restart is acceptable for now

## Estimated Changed Lines
~300-350 lines (within 400-line budget)
- `lib/api.ts`: ~40 lines (new methods)
- `types/index.ts`: ~60 lines (new types)
- `app/workflows/[id]/page.tsx`: ~200 lines (execution UI, event stream, history)
