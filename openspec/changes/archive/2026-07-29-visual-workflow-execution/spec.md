# Workflow Execution & Monitoring Specification

## Purpose

Enable users to execute workflows, monitor real-time progress via polling, and control running executions (pause/resume/cancel) from the workflow detail page.

## Requirements

### Requirement: Execution Lifecycle Management

The system MUST allow users to start, pause, resume, and cancel workflow executions from the workflow detail page.

#### Scenario: Start a new execution

- GIVEN user is on the workflow detail page
- WHEN user clicks "Start" button
- THEN system calls `POST /api/v1/workflows/executions` with `{workflow_id}`
- AND system calls `POST /api/v1/workflows/executions/{id}/start`
- AND UI updates to show execution status as RUNNING

#### Scenario: Pause a running execution

- GIVEN an execution is in RUNNING status
- WHEN user clicks "Pause" button
- THEN system calls `POST /api/v1/workflows/executions/{id}/action` with `{action: "pause"}`
- AND UI updates status to PAUSED

#### Scenario: Resume a paused execution

- GIVEN an execution is in PAUSED status
- WHEN user clicks "Resume" button
- THEN system calls `POST /api/v1/workflows/executions/{id}/action` with `{action: "resume"}`
- AND UI updates status to RUNNING

#### Scenario: Cancel an execution

- GIVEN an execution is in RUNNING or PAUSED status
- WHEN user clicks "Cancel" button
- THEN system calls `POST /api/v1/workflows/executions/{id}/action` with `{action: "cancel"}`
- AND UI updates status to CANCELLED

### Requirement: Real-Time Event Monitoring

The system MUST poll execution events every 2 seconds while execution is RUNNING and display them in a scrollable event stream.

#### Scenario: Display events during execution

- GIVEN an execution is RUNNING
- WHEN 2-second poll interval elapses
- THEN system calls `GET /api/v1/workflows/executions/{id}/events`
- AND new events are appended to the event stream UI
- AND stream auto-scrolls to latest event

#### Scenario: Stop polling on completion

- GIVEN an execution reaches COMPLETED, FAILED, or CANCELLED status
- WHEN status change is detected
- THEN polling stops immediately
- AND final events are displayed

### Requirement: Execution History

The system MUST display a table of past executions with status, duration, and step progress.

#### Scenario: List executions for workflow

- GIVEN user is on the workflow detail page
- WHEN page loads
- THEN system calls `GET /api/v1/workflows/executions?workflow_id={id}`
- AND execution history table is populated with results

### Requirement: Visual Status Indicators

The system MUST display color-coded badges for execution and step statuses.

#### Scenario: Status badge colors

- GIVEN an execution or step has a status
- WHEN status is displayed
- THEN: RUNNING = blue, COMPLETED = green, FAILED = red, PENDING = gray, PAUSED = yellow, CANCELLED = gray

### Requirement: API Client Methods

The system MUST provide typed API methods for all execution endpoints.

#### Scenario: API method signatures

- GIVEN frontend needs to call execution endpoints
- WHEN `startExecution(workflowId)` is called
- THEN returns `Promise<WorkflowExecution>`
- AND `getExecutionEvents(id)` returns `Promise<WorkflowEvent[]>`
- AND `executeAction(id, action)` returns `Promise<WorkflowExecution>`
- AND `listExecutions(filters)` returns `Promise<WorkflowExecution[]>`

## Edge Cases

### Requirement: Duplicate Execution Prevention

The system MUST prevent starting a new execution if one is already RUNNING for the same workflow.

#### Scenario: Execution already running

- GIVEN a workflow has an execution in RUNNING status
- WHEN user clicks "Start"
- THEN "Start" button is disabled
- AND tooltip shows "Execution already in progress"

### Requirement: Empty Workflow Handling

The system MUST handle workflows with no steps gracefully.

#### Scenario: Start empty workflow

- GIVEN a workflow has zero steps
- WHEN user starts execution
- THEN execution completes immediately with COMPLETED status
- AND event stream shows "Workflow completed (no steps)"

## Component Interfaces

### ExecutionControls

- Props: `{ execution: WorkflowExecution | null, onStart: () => void, onPause: () => void, onResume: () => void, onCancel: () => void }`
- State: derives button disabled state from `execution.status`

### EventStream

- Props: `{ events: WorkflowEvent[], isPolling: boolean }`
- State: `scrollRef` for auto-scroll management

### ExecutionHistory

- Props: `{ executions: WorkflowExecution[] }`
- State: none (controlled by parent)

### StepStatusBadge

- Props: `{ status: string }`
- State: none (pure presentational)

## State Management

- Use SWR for execution list and detail fetching with automatic revalidation
- Use `mutate()` for optimistic updates after pause/resume/cancel actions
- Polling managed via `useEffect` with 2s interval, cleaned up on status change
- No Zustand needed — component-local state sufficient for this scope
