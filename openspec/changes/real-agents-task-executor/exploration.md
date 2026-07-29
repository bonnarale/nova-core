## Exploration: real-agents-task-executor

### Current State
The NOVA CORE system has a complete task lifecycle infrastructure (TaskManager, Worker, Planner, DependencyResolver, EventBus) but the execution pipeline is disconnected. Tasks are created but never executed because:

1. The chat endpoint (`nova_web.py:115-274`) calls `kernel.run_agent()` which routes to the cognitive engine
2. The cognitive engine detects intent and creates tasks (`engine.py:488-550`) via `task_manager.create_task()`
3. `Planner.create_task()` creates tasks with status CREATED and emits `task.created` event (`planner.py:28-38`)
4. `DependencyResolver` subscribes to `task.created` but only checks dependencies (`dependency_resolver.py:36-49`)
5. **NO ONE transitions tasks from CREATED → QUEUED → RUNNING** — this is the critical broken connection
6. `TaskManager.transition_task()` exists (`task_manager.py:100-112`) and dispatches to agents when status=RUNNING, but it's never called automatically
7. Builtin agents are stubs returning hardcoded responses (e.g., `executor_agent.py:35-52`, `coder_agent.py:35-45`)

### Affected Areas
- `backend/app/api/v1/routes/nova_web.py:115-274` — chat endpoint extracts response from kernel result
- `backend/app/cognitive/engine.py:488-550` — `_execute_create_task` creates task but doesn't transition it
- `backend/app/orchestrator/planner.py:28-38` — creates task with status CREATED
- `backend/app/orchestrator/dependency_resolver.py:36-49` — subscribes to task.created but only checks deps
- `backend/app/orchestrator/task_manager.py:100-112` — `transition_task` dispatches agents but never called
- `backend/app/agents/builtins/*.py` — all agents are stubs returning hardcoded responses
- `backend/app/agents/agent_manager.py:114-167` — `dispatch` method works but is never triggered for task execution

### Broken Connections
1. **No CREATED → QUEUED transition**: After task creation, nobody calls `task_manager.transition_task(task_id, "QUEUED")`
2. **No QUEUED → RUNNING transition**: No worker/scheduler picks up QUEUED tasks
3. **No event-driven execution**: `task.created` event only triggers dependency checking, not execution
4. **Agent dispatch never triggered for tasks**: `agent_manager.dispatch` is only called when `transition_task` is called with status=RUNNING

### Specific Code Changes Needed

#### Option A: Event-Driven Task Executor (Recommended)
Create a new `TaskExecutor` class that:
1. Subscribes to `task.created` event
2. Checks dependencies (reuse DependencyResolver logic)
3. Transitions task to QUEUED → RUNNING
4. Dispatches to assigned agent via `agent_manager.dispatch`
5. Advances steps and transitions to COMPLETED

**Files to create/modify:**
- `backend/app/orchestrator/task_executor.py` (new) — event-driven executor
- `backend/app/orchestrator/dependency_resolver.py` — add auto-transition logic
- `backend/app/cognitive/engine.py:488-550` — after task creation, optionally auto-queue
- `backend/app/agents/builtins/*.py` — replace stubs with real implementations

#### Option B: Inline Task Execution
Modify `_execute_create_task` in cognitive engine to:
1. Create task
2. Immediately transition to QUEUED → RUNNING
3. Dispatch to agent
4. Return result

**Pros:** Simpler, fewer moving parts
**Cons:** Blocks the chat response, no async execution

#### Option C: Hybrid Approach
- Add auto-transition in DependencyResolver for tasks with no dependencies
- Keep long-running tasks async
- Add a task scheduler that periodically picks up QUEUED tasks

### Risk Assessment
- **High Risk**: Replacing builtin agents with real implementations requires significant work
- **Medium Risk**: Event-driven execution must handle failures gracefully (retry, dead letter)
- **Low Risk**: Adding task transitions is straightforward with existing Worker infrastructure

### Recommendation
**Option A (Event-Driven Task Executor)** is recommended because:
1. It leverages the existing EventBus and DependencyResolver
2. It enables async execution (chat returns immediately)
3. It's extensible for future agent types
4. It aligns with the existing architecture patterns

### Ready for Proposal
Yes — the exploration is complete. The orchestrator should proceed to `sdd-propose` to create a detailed change proposal for implementing real agent task execution.