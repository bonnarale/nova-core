# Design: Visual Workflow Execution & Real-Time Monitoring

## 1. Architecture Decision

**Decision: Inline components in page file, separate type definitions.**

The proposal estimates ~300-350 total changed lines. Splitting `ExecutionControls`, `EventStream`, `ExecutionHistory`, and `StepStatusBadge` into separate files would create four tiny components (<50 lines each) that are only used in one place. That's not abstraction — it's indirection.

**Approach:**
- Define all new types in `frontend/types/index.ts` (reuse across future pages)
- Expand `NovaAPI.workflows` namespace in `frontend/lib/api.ts` with typed methods
- Implement everything else inline in `frontend/app/workflows/[id]/page.tsx`
- Reuse existing `StatusBadge` from `@/components/ui` (already maps status → color)
- Reuse existing `usePolling` hook from `@/hooks` for the 2s interval

**Why not SWR?** The codebase uses a custom `useApi` hook everywhere. SWR is installed but zero files import it. Switching to SWR mid-feature adds a second data-fetching pattern for no benefit. Stick with `useApi` for consistency.

**Why not Zustand?** No store exists yet. This feature only needs page-local state — current execution, events list, action loading states. A global store would be premature.

## 2. Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    WorkflowDetailPage                        │
│                                                              │
│  useApi<Workflow>(/workflows/{id})  ──→  workflow           │
│  useApi<WorkflowExecution[]>(/executions?workflow_id={id})  │
│                                        ──→  executions[]    │
│                                                              │
│  ┌─ activeExecution (derived from executions[])             │
│  │   status === RUNNING || PAUSED → start polling           │
│  │                                                           │
│  │  usePolling(fetchEvents, 2000) ──→ events[]             │
│  └──────────────────────────────────────────────────────    │
│                                                              │
│  User clicks "Start"                                         │
│    → api.workflows.create({workflow_id: id})                │
│    → api.workflows.start(execution.id)                      │
│    → refetch executions → activeExecution becomes RUNNING   │
│    → polling starts automatically                           │
│                                                              │
│  User clicks "Pause"                                         │
│    → api.workflows.action(execution.id, "pause")            │
│    → refetch executions → status → PAUSED                   │
│    → polling stops (not RUNNING)                             │
│                                                              │
│  User clicks "Resume"                                        │
│    → api.workflows.action(execution.id, "resume")           │
│    → refetch executions → status → RUNNING                  │
│    → polling restarts                                        │
│                                                              │
│  User clicks "Cancel"                                        │
│    → api.workflows.action(execution.id, "cancel")           │
│    → refetch executions → status → CANCELLED                │
│    → polling stops                                           │
└─────────────────────────────────────────────────────────────┘
```

**Key insight:** Polling state is derived from `activeExecution.status`, not managed separately. When status transitions to a terminal state (COMPLETED, FAILED, CANCELLED), polling stops because the condition becomes false.

## 3. Component Design

### 3.1 Type Definitions (`frontend/types/index.ts`)

Add after the existing `Workflow` interface:

```typescript
// --- Workflow Execution Types ---

export type WorkflowExecutionStatus =
  | "PENDING"
  | "RUNNING"
  | "PAUSED"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED"
  | "ROLLING_BACK"
  | "ROLLED_BACK";

export type StepExecutionStatus =
  | "PENDING"
  | "RUNNING"
  | "COMPLETED"
  | "FAILED"
  | "SKIPPED"
  | "RETRYING"
  | "ROLLING_BACK"
  | "ROLLED_BACK";

export type WorkflowEventType =
  | "CREATED"
  | "STARTED"
  | "STEP_STARTED"
  | "STEP_COMPLETED"
  | "STEP_FAILED"
  | "PAUSED"
  | "RESUMED"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED"
  | "ROLLING_BACK"
  | "ROLLED_BACK"
  | "RETRYING"
  | "PROGRESS"
  | "WAITING"
  | "DECISION_REQUIRED";

export interface WorkflowStepExecution {
  step_id: string;
  step_name: string;
  step_type: string;
  status: StepExecutionStatus;
  error: string | null;
  retry_count: number;
  duration_ms: number;
}

export interface WorkflowExecution {
  id: string;
  workflow_id: string;
  workflow_name: string;
  status: WorkflowExecutionStatus;
  error: string | null;
  current_step_id: string | null;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  steps: WorkflowStepExecution[];
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number;
  user_id: string | null;
  tags: string[];
  metadata: Record<string, unknown>;
}

export interface WorkflowEvent {
  id: string;
  execution_id: string;
  event_type: WorkflowEventType;
  step_id: string | null;
  payload: Record<string, unknown>;
  timestamp: string | null;
}
```

**Why union types instead of enums?** TypeScript enums have implicit `number` values and don't narrow cleanly in JSX. Union string types match the backend's string values directly and work with `===` comparisons in conditionals.

### 3.2 API Client Extension (`frontend/lib/api.ts`)

Expand the existing `workflows` namespace (lines 93-100). Replace the current untyped `execute` with typed methods:

```typescript
workflows = {
  list: () => this.get<Workflow[]>("/workflows"),
  create: (data: Record<string, unknown>) => this.post<Workflow>("/workflows", data),
  get: (id: string) => this.get<Workflow>(`/workflows/${id}`),
  delete: (id: string) => this.delete<{ status: string }>(`/workflows/${id}`),
  health: () => this.get("/workflows/health"),
  metrics: () => this.get("/workflows/metrics"),

  // Execution lifecycle
  createExecution: (data: { workflow_id: string; input?: Record<string, unknown> }) =>
    this.post<WorkflowExecution>("/workflows/executions", data),
  startExecution: (executionId: string) =>
    this.post<WorkflowExecution>(`/workflows/executions/${executionId}/start`),
  getExecution: (executionId: string) =>
    this.get<WorkflowExecution>(`/workflows/executions/${executionId}`),
  listExecutions: (params?: { workflow_id?: string; status?: string; limit?: number }) => {
    const query: Record<string, string> = {};
    if (params?.workflow_id) query.workflow_id = params.workflow_id;
    if (params?.status) query.status = params.status;
    if (params?.limit) query.limit = String(params.limit);
    return this.get<WorkflowExecution[]>("/workflows/executions", query);
  },
  action: (executionId: string, action: "pause" | "resume" | "cancel" | "rollback") =>
    this.post<WorkflowExecution>(`/workflows/executions/${executionId}/action`, { action }),
  getEvents: (executionId: string) =>
    this.get<WorkflowEvent[]>(`/workflows/executions/${executionId}/events`),
};
```

**Note:** The old `execute` method is removed and replaced with `createExecution` + `startExecution`. The two-step flow (create PENDING → start RUNNING) matches the spec's scenario: "Start" creates an execution then starts it.

### 3.3 Page Component State (`frontend/app/workflows/[id]/page.tsx`)

The page maintains these state variables:

```typescript
// Data fetching
const { data: workflow, loading, error } = useApi<Workflow>(`/api/v1/workflows/${id}`, [id]);
const { data: executions, refetch: refetchExecutions } = useApi<WorkflowExecution[]>(
  `/api/v1/workflows/executions?workflow_id=${id}`, [id]
);

// Active execution (most recent non-terminal, or most recent overall)
const activeExecution = useMemo(() => {
  if (!executions?.length) return null;
  const running = executions.find(e => ["RUNNING", "PAUSED"].includes(e.status));
  return running || executions[0];
}, [executions]);

// Event polling
const [events, setEvents] = useState<WorkflowEvent[]>([]);
const isPolling = activeExecution?.status === "RUNNING";

useEffect(() => {
  if (!isPolling || !activeExecution) return;
  const id = setInterval(async () => {
    try {
      const newEvents = await api.workflows.getEvents(activeExecution.id);
      setEvents(newEvents);
    } catch { /* silent — will retry next interval */ }
  }, 2000);
  return () => clearInterval(id);
}, [isPolling, activeExecution?.id]);

// Reset events when execution changes
useEffect(() => {
  setEvents([]);
  if (activeExecution) {
    api.workflows.getEvents(activeExecution.id).then(setEvents).catch(() => {});
  }
}, [activeExecution?.id]);

// Action loading states
const [actionLoading, setActionLoading] = useState<string | null>(null);
```

### 3.4 Inline Sub-Components

All defined inside the page file, above the default export:

```typescript
// --- StepStatusBadge (inline) ---
function StepStatusBadge({ status }: { status: string }) {
  // Reuses the StatusBadge from @/components/ui
  // Maps StepExecutionStatus → StatusBadge variant
  const variantMap: Record<string, "default" | "success" | "warning" | "error" | "info"> = {
    PENDING: "default",
    RUNNING: "info",
    COMPLETED: "success",
    FAILED: "error",
    SKIPPED: "default",
    RETRYING: "warning",
    ROLLING_BACK: "warning",
    ROLLED_BACK: "default",
  };
  return <Badge variant={variantMap[status] || "default"}>{status}</Badge>;
}

// --- ExecutionControls (inline) ---
function ExecutionControls({
  execution, onStart, onPause, onResume, onCancel, loading,
}: {
  execution: WorkflowExecution | null;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onCancel: () => void;
  loading: string | null;
}) {
  const status = execution?.status;
  const isTerminal = ["COMPLETED", "FAILED", "CANCELLED", "ROLLED_BACK"].includes(status || "");
  const isRunning = status === "RUNNING";
  const isPaused = status === "PAUSED";
  const hasActive = status !== undefined && !isTerminal;

  return (
    <div className="flex gap-2">
      {!hasActive && (
        <Button onClick={onStart} loading={loading === "start"}>
          Start Execution
        </Button>
      )}
      {isRunning && (
        <Button variant="secondary" onClick={onPause} loading={loading === "pause"}>
          Pause
        </Button>
      )}
      {isPaused && (
        <Button onClick={onResume} loading={loading === "resume"}>
          Resume
        </Button>
      )}
      {(isRunning || isPaused) && (
        <Button variant="danger" onClick={onCancel} loading={loading === "cancel"}>
          Cancel
        </Button>
      )}
    </div>
  );
}

// --- EventStream (inline) ---
function EventStream({ events, isPolling }: { events: WorkflowEvent[]; isPolling: boolean }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events.length]);

  if (events.length === 0) {
    return (
      <div className="text-sm text-gray-500 py-4 text-center">
        {isPolling ? "Waiting for events..." : "No events recorded."}
      </div>
    );
  }

  return (
    <div ref={scrollRef} className="max-h-64 overflow-y-auto space-y-1">
      {events.map((event) => (
        <div key={event.id} className="flex items-start gap-2 text-xs font-mono py-1 px-2 rounded bg-gray-900/30">
          <span className="text-gray-500 shrink-0">
            {event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : "--:--:--"}
          </span>
          <StepStatusBadge status={event.event_type} />
          <span className="text-gray-300 break-all">
            {event.step_id && <span className="text-gray-400">[{event.step_id}] </span>}
            {Object.keys(event.payload).length > 0
              ? JSON.stringify(event.payload)
              : event.event_type}
          </span>
        </div>
      ))}
    </div>
  );
}

// --- ExecutionHistory (inline) ---
function ExecutionHistory({ executions }: { executions: WorkflowExecution[] }) {
  if (executions.length === 0) {
    return <div className="text-sm text-gray-500 py-4 text-center">No executions yet.</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700">
            <th className="text-left py-2 text-gray-400 font-medium">Status</th>
            <th className="text-left py-2 text-gray-400 font-medium">Started</th>
            <th className="text-left py-2 text-gray-400 font-medium">Duration</th>
            <th className="text-left py-2 text-gray-400 font-medium">Steps</th>
          </tr>
        </thead>
        <tbody>
          {executions.map((exec) => (
            <tr key={exec.id} className="border-b border-gray-800/50">
              <td className="py-2"><StatusBadge status={exec.status} /></td>
              <td className="py-2 text-gray-300">
                {exec.started_at ? new Date(exec.started_at).toLocaleString() : "-"}
              </td>
              <td className="py-2 text-gray-300">
                {exec.duration_ms > 0 ? `${(exec.duration_ms / 1000).toFixed(1)}s` : "-"}
              </td>
              <td className="py-2 text-gray-300">
                {exec.steps.filter(s => s.status === "COMPLETED").length}/{exec.steps.length}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

## 4. Polling Strategy

### Implementation

```typescript
// In the page component:

const isPolling = activeExecution?.status === "RUNNING";

// Fetch events — called on interval AND on execution change
const fetchEvents = useCallback(async () => {
  if (!activeExecution) return;
  try {
    const newEvents = await api.workflows.getEvents(activeExecution.id);
    setEvents(newEvents);
  } catch { /* silent retry */ }
}, [activeExecution?.id]);

// Poll only while RUNNING
useEffect(() => {
  if (!isPolling || !activeExecution) return;
  const id = setInterval(fetchEvents, 2000);
  return () => clearInterval(id);
}, [isPolling, fetchEvents, activeExecution?.id]);

// Reset and fetch on execution change (including on initial load)
useEffect(() => {
  setEvents([]);
  if (activeExecution) {
    fetchEvents();
  }
}, [activeExecution?.id, fetchEvents]);
```

### Behavior Matrix

| `activeExecution.status` | `isPolling` | Interval active? | Events fetched? |
|---|---|---|---|
| `undefined` (no executions) | `false` | No | No |
| `PENDING` | `false` | No | Yes (once, on mount) |
| `RUNNING` | `true` | Yes (2s) | Yes (continuous) |
| `PAUSED` | `false` | No | Yes (once, on transition) |
| `COMPLETED` | `false` | No | Yes (once, on transition) |
| `FAILED` | `false` | No | Yes (once, on transition) |
| `CANCELLED` | `false` | No | Yes (once, on transition) |

### Cleanup

- `clearInterval` runs on every re-render where `isPolling` or `activeExecution.id` changes
- If the component unmounts while polling, the effect cleanup clears the interval
- The `fetchEvents` callback is memoized with `useCallback` — no stale closure issues

### Why not `usePolling` hook?

The existing `usePolling` hook takes a plain `fn` and `intervalMs`. It works, but it doesn't handle conditional polling (only poll when `isPolling` is true). We'd need to wrap it:

```typescript
usePolling(fetchEvents, isPolling ? 2000 : 0);
// But usePolling always runs the interval — passing 0 would still tick
```

Looking at the hook implementation (line 72-79 of hooks/index.ts), it always sets up the interval. Passing `0` as interval would cause rapid firing. Better to use the `useEffect` approach directly — it's cleaner and the intent is explicit.

**Decision: Use `useEffect` with `setInterval` directly, not the `usePolling` hook.**

## 5. API Client Extension — Exact Implementation

The `workflows` property on `NovaAPI` becomes:

```typescript
workflows = {
  // --- Definition CRUD ---
  list: () => this.get<Workflow[]>("/workflows"),
  create: (data: Record<string, unknown>) => this.post<Workflow>("/workflows", data),
  get: (id: string) => this.get<Workflow>(`/workflows/${id}`),
  delete: (id: string) => this.delete<{ status: string }>(`/workflows/${id}`),
  health: () => this.get("/workflows/health"),
  metrics: () => this.get("/workflows/metrics"),

  // --- Execution Lifecycle ---
  createExecution: (data: { workflow_id: string; input?: Record<string, unknown> }) =>
    this.post<WorkflowExecution>("/workflows/executions", data),

  startExecution: (executionId: string) =>
    this.post<WorkflowExecution>(`/workflows/executions/${executionId}/start`),

  getExecution: (executionId: string) =>
    this.get<WorkflowExecution>(`/workflows/executions/${executionId}`),

  listExecutions: (params?: { workflow_id?: string; status?: string; limit?: number }) => {
    const query: Record<string, string> = {};
    if (params?.workflow_id) query.workflow_id = params.workflow_id;
    if (params?.status) query.status = params.status;
    if (params?.limit) query.limit = String(params.limit);
    return this.get<WorkflowExecution[]>("/workflows/executions", query);
  },

  action: (executionId: string, action: "pause" | "resume" | "cancel" | "rollback") =>
    this.post<WorkflowExecution>(`/workflows/executions/${executionId}/action`, { action }),

  getEvents: (executionId: string) =>
    this.get<WorkflowEvent[]>(`/workflows/executions/${executionId}/events`),
};
```

**Imports needed in `api.ts`:**
```typescript
import type { Workflow, WorkflowExecution, WorkflowEvent } from "@/types";
```

**Note:** The generic type parameters on `this.get<T>()` / `this.post<T>()` are already supported by the existing `request<T>` method (line 21 of api.ts). No changes needed to the base HTTP methods.

## 6. Error Handling Strategy

### Layer 1: API Client (automatic)

The existing `request<T>` method (api.ts line 21-36) already handles HTTP errors:
```typescript
if (!res.ok) {
  const err = await res.json().catch(() => ({ detail: res.statusText }));
  throw new Error(err.detail || `HTTP ${res.status}`);
}
```

All `api.workflows.*` methods inherit this. No changes needed.

### Layer 2: Action Handlers (page component)

```typescript
const handleStart = async () => {
  setActionLoading("start");
  try {
    const execution = await api.workflows.createExecution({ workflow_id: id });
    await api.workflows.startExecution(execution.id);
    refetchExecutions();
    setActionError(null);
  } catch (err) {
    setActionError(err instanceof Error ? err.message : "Failed to start execution");
  } finally {
    setActionLoading(null);
  }
};

const handleAction = async (action: "pause" | "resume" | "cancel") => {
  if (!activeExecution) return;
  setActionLoading(action);
  try {
    await api.workflows.action(activeExecution.id, action);
    refetchExecutions();
    setActionError(null);
  } catch (err) {
    setActionError(err instanceof Error ? err.message : `Failed to ${action}`);
  } finally {
    setActionLoading(null);
  }
};
```

### Layer 3: UI Error Display

```typescript
{actionError && (
  <div className="bg-red-900/30 border border-red-700/50 rounded-lg px-4 py-2 text-sm text-red-300 mb-4">
    {actionError}
  </div>
)}
```

### Layer 4: Polling Errors (silent)

Event polling errors are swallowed — the next 2s interval will retry. If the backend is down, the UI shows stale events until it recovers. No user-facing error for background polling.

```typescript
try {
  const newEvents = await api.workflows.getEvents(activeExecution.id);
  setEvents(newEvents);
} catch { /* silent — will retry next interval */ }
```

### Edge Case: Duplicate Execution Prevention

The "Start" button is disabled when an active execution exists:

```typescript
const hasActiveExecution = executions?.some(
  e => ["RUNNING", "PAUSED", "PENDING"].includes(e.status)
);

// In ExecutionControls:
{!hasActive && (
  <Button onClick={onStart} loading={loading === "start"}>
    Start Execution
  </Button>
)}
```

## 7. Performance Considerations

### Re-render Optimization

1. **`useMemo` for `activeExecution`** — Only recalculates when `executions` array reference changes (after `refetchExecutions`), not on every render.

2. **`useCallback` for `fetchEvents`** — Memoized on `activeExecution.id`. Prevents the polling `useEffect` from re-creating the interval on every render.

3. **`useEffect` dependency on `activeExecution?.id`** — Not on `activeExecution` object (which gets a new reference on each render from `useMemo`). The `.id` is a stable string.

4. **Event list rendering** — Each event has a stable `id` key. React only re-renders the new events appended to the list, not the entire list. The `max-h-64 overflow-y-auto` container limits DOM size.

### Memory Management

- **Event accumulation** — The `events` state replaces the entire array on each poll (not append). This means the list never grows beyond what the backend returns. If the backend returns all events for an execution, the list is bounded by execution duration.

- **Polling cleanup** — The `clearInterval` in the effect cleanup ensures no orphaned timers. When the component unmounts or `activeExecution` changes, the old interval is cleared before the new one is set.

- **No event deduplication needed** — Each poll replaces `events` with the full list from the backend. The backend's `get_events()` returns all events for an execution. If the backend added pagination (offset), we'd need dedup, but for MVP the full replace is correct.

### When NOT to optimize

- **No `React.memo` on inline components** — They're defined in the same file and render in the same tree. Memoizing them would add complexity without measurable benefit at this scale.
- **No virtualization for event list** — The list is bounded by execution events (typically <100). Virtualization adds a library dependency for negligible gain.
- **No debounce on event polling** — 2s is already slow enough. Debouncing would delay event visibility.

## 8. File Change Summary

| File | Change | Lines |
|---|---|---|
| `frontend/types/index.ts` | Add `WorkflowExecution`, `WorkflowEvent`, `WorkflowStepExecution`, status union types | ~65 |
| `frontend/lib/api.ts` | Expand `workflows` namespace with typed methods, add type imports | ~30 |
| `frontend/app/workflows/[id]/page.tsx` | Rewrite page with execution controls, event stream, history | ~200 |
| **Total** | | **~295** |

## 9. Testing Strategy

### Unit Tests (if added later)
- `StepStatusBadge` — verify correct variant mapping for each status
- `ExecutionControls` — verify button visibility for each execution status
- `EventStream` — verify auto-scroll behavior

### Integration Test
1. Navigate to `/workflows/{id}`
2. Click "Start Execution" → verify status changes to RUNNING
3. Wait 3s → verify events appear in stream
4. Click "Pause" → verify status changes to PAUSED, polling stops
5. Click "Resume" → verify status changes to RUNNING, polling resumes
6. Click "Cancel" → verify status changes to CANCELLED

### Manual Verification
- Confirm events appear within 2-3 seconds of start
- Confirm polling stops when execution completes
- Confirm "Start" button is disabled while execution is active
- Confirm error messages display on failed actions
