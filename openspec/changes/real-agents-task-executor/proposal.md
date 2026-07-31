# Proposal: Real Agents Task Executor

## Intent

NOVA CORE has complete task lifecycle infrastructure (TaskManager, Worker, Planner, DependencyResolver, EventBus) but the execution pipeline is **disconnected**. Tasks are created via the cognitive engine but never transition to RUNNING — no executor picks them up. Additionally, all builtin agents are stubs returning hardcoded responses. This change connects the pipeline so tasks actually execute and agents do real work.

## Scope

### In Scope
- Event-driven `TaskExecutor` that subscribes to `task.created` and orchestrates CREATED → QUEUED → RUNNING → COMPLETED transitions
- Dependency-aware scheduling (reuse DependencyResolver logic)
- Replace builtin agent stubs with functional implementations (executor, coder, researcher agents)
- Error handling: retry logic, dead-letter queue for failed tasks
- Chat endpoint returns task ID immediately (async execution)

### Out of Scope
- Parallel task execution (future optimization)
- Agent-to-agent communication or delegation
- Custom agent creation UI
- Task priority queuing or preemption
- External agent integrations (OpenAI, etc.)

## Capabilities

### New Capabilities
- `task-execution-pipeline`: Event-driven executor that transitions tasks through lifecycle states and dispatches to agents
- `builtin-agent-implementation`: Functional agent implementations replacing stub responses

### Modified Capabilities
None — this change wires existing infrastructure, doesn't alter spec-level behavior of existing capabilities.

## Approach

**Phase 1 — Task Executor Core**
Create `backend/app/orchestrator/task_executor.py` subscribing to `task.created`. Transitions: CREATED → QUEUED (deps satisfied) → RUNNING (dispatch via agent_manager) → COMPLETED/FAILED. Leverages existing EventBus and Worker patterns.

**Phase 2 — Builtin Agent Implementations**
Replace stub responses in `executor_agent.py`, `coder_agent.py`, `researcher_agent.py` with real task-execution logic using the kernel's LLM capabilities.

**Phase 3 — Error Handling & Resilience**
Add retry with exponential backoff, dead-letter queue for permanently failed tasks, structured logging for execution tracing.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/app/orchestrator/task_executor.py` | New | Event-driven executor class |
| `backend/app/orchestrator/dependency_resolver.py` | Modified | Add auto-transition on deps satisfied |
| `backend/app/cognitive/engine.py:488-550` | Modified | Emit task ID in response |
| `backend/app/agents/builtins/*.py` | Modified | Replace stubs with real implementations |
| `backend/app/api/v1/routes/nova_web.py:115-274` | Modified | Return task ID, not blocking result |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Event loops or deadlocks from synchronous transitions | Medium | Use async/await patterns, test with dependency chains |
| Agent failures crash executor | Medium | Wrap dispatch in try/except, transition to FAILED state |
| Existing task lifecycle breaks | Low | Follow existing Worker/TaskManager patterns exactly |

## Rollback Plan

1. Revert `task_executor.py` creation (new file, no existing deps)
2. Revert `dependency_resolver.py` changes (git restore)
3. Revert builtin agent changes (git restore stubs)
4. Revert `engine.py` and `nova_web.py` changes
5. All changes are additive or reversible modifications — no data migrations required

## Dependencies

- Existing EventBus infrastructure (already present)
- Existing TaskManager.transition_task() method (already present)
- Existing agent_manager.dispatch() method (already present)

## Success Criteria

- [ ] Task created via chat endpoint transitions to RUNNING within 5 seconds
- [ ] Builtin agents return real LLM-generated responses (not hardcoded strings)
- [ ] Failed tasks transition to FAILED state with error logged
- [ ] Chat endpoint returns task ID immediately (non-blocking)
- [ ] Dependency chains execute in correct order
- [ ] No regressions in existing chat functionality
