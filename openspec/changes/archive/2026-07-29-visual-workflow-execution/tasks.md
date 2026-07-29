# Tasks: Visual Workflow Execution & Real-Time Monitoring

## Task 1: Add execution types to `frontend/types/index.ts` ✅

**File:** `frontend/types/index.ts`
**Depends on:** nothing
**Estimated lines:** ~65

Add after the existing `Workflow` interface (line 117):

- `WorkflowExecutionStatus` union type (8 variants: PENDING, RUNNING, PAUSED, COMPLETED, FAILED, CANCELLED, ROLLING_BACK, ROLLED_BACK)
- `StepExecutionStatus` union type (8 variants: PENDING, RUNNING, COMPLETED, FAILED, SKIPPED, RETRYING, ROLLING_BACK, ROLLED_BACK)
- `WorkflowEventType` union type (15 variants)
- `WorkflowStepExecution` interface (step_id, step_name, step_type, status, error, retry_count, duration_ms)
- `WorkflowExecution` interface (id, workflow_id, workflow_name, status, error, current_step_id, input, output, steps, created_at, started_at, completed_at, duration_ms, user_id, tags, metadata)
- `WorkflowEvent` interface (id, execution_id, event_type, step_id, payload, timestamp)

**Verify:**
- `npx tsc --noEmit` passes (no type errors in the new exports)
- Existing `Workflow` interface unchanged

---

## Task 2: Expand API client in `frontend/lib/api.ts` ✅

**File:** `frontend/lib/api.ts`
**Depends on:** Task 1 (needs type imports)
**Estimated lines:** ~30 (replace lines 93-100, add import)

1. Add import at top: `import type { Workflow, WorkflowExecution, WorkflowEvent } from "@/types";`
2. Replace the existing `workflows` namespace (lines 93-100) with expanded typed methods:
   - Keep existing: `list`, `create`, `get`, `health`, `metrics`
   - Remove: `execute` (replaced by two-step flow)
   - Add: `delete` (missing from current namespace)
   - Add: `createExecution(data)` → `POST /workflows/executions`
   - Add: `startExecution(executionId)` → `POST /workflows/executions/{id}/start`
   - Add: `getExecution(executionId)` → `GET /workflows/executions/{id}`
   - Add: `listExecutions(params?)` → `GET /workflows/executions` with query params
   - Add: `action(executionId, action)` → `POST /workflows/executions/{id}/action`
   - Add: `getEvents(executionId)` → `GET /workflows/executions/{id}/events`

**Verify:**
- `npx tsc --noEmit` passes
- No other files import the removed `execute` method (grep confirms)

---

## Task 3: Implement execution page in `frontend/app/workflows/[id]/page.tsx` ✅

**File:** `frontend/app/workflows/[id]/page.tsx`
**Depends on:** Task 1 + Task 2
**Estimated lines:** ~200 (rewrite from 81 lines)

Rewrite the page component to add:

1. **Data fetching** — keep existing `useApi<Workflow>` for workflow, add `useApi<WorkflowExecution[]>` for executions list
2. **Active execution derivation** — `useMemo` to find RUNNING/PAUSED execution or most recent
3. **Polling logic** — `useEffect` with `setInterval` (2s) that calls `api.workflows.getEvents` while `activeExecution.status === "RUNNING"`, cleanup on status change
4. **Event state** — `useState<WorkflowEvent[]>`, reset on execution change
5. **Action handlers** — `handleStart` (create + start + refetch), `handleAction` (pause/resume/cancel + refetch), with loading and error states
6. **Inline sub-components** (defined above the default export):
   - `StepStatusBadge` — maps `StepExecutionStatus` → `Badge` variant
   - `ExecutionControls` — Start/Pause/Resume/Cancel buttons, disabled based on status
   - `EventStream` — scrollable event list with auto-scroll via `useRef`
   - `ExecutionHistory` — table of past executions with status, duration, step progress
7. **Edge cases** — disable Start when execution active, empty workflow handling, error display

**Verify:**
- `npx tsc --noEmit` passes
- `npm run build` succeeds (Next.js build)
- Manual: navigate to `/workflows/{id}`, buttons render, Start triggers execution, events appear within 2-3s, Pause/Resume/Cancel work, polling stops on completion

---

## Workload Forecast

| Metric | Value |
|---|---|
| Estimated total changed lines | ~295 |
| Files changed | 3 |
| Chained PRs needed? | No (under 400 lines) |
| Decision needed before apply? | No |
| Backend changes required? | No (already functional) |
