# Design: Real Agents Task Executor

## Technical Approach

Connect the disconnected task execution pipeline by creating a `TaskExecutor` that subscribes to `task.created` events and orchestrates lifecycle transitions (CREATED → QUEUED → RUNNING → COMPLETED/FAILED). Replace stub builtin agents with real LLM-powered implementations using the existing `ModelGateway`. Fix the chat endpoint to return task IDs asynchronously instead of blocking for execution results.

## Architecture Decisions

### Decision: Event-Driven TaskExecutor

**Choice**: Create `TaskExecutor` class subscribing to `task.created` via `InMemoryEventBus`
**Alternatives considered**: Polling-based executor, synchronous execution in chat endpoint
**Rationale**: Follows existing `DependencyResolver` pattern; non-blocking; leverages existing infrastructure

### Decision: Reuse Existing Worker for Transitions

**Choice**: Delegate state transitions to `TaskManager.transition_task()` which calls `Worker.transition()`
**Alternatives considered**: Create new transition logic in TaskExecutor
**Rationale**: Maintains single source of truth for task state; respects existing constraints (no Worker modification)

### Decision: LLM Agents via ModelGateway

**Choice**: Builtin agents use `ModelGateway.chat()` for LLM calls (same as `LLMAgent`)
**Alternatives considered**: Direct Ollama HTTP calls, new LLM abstraction
**Rationale**: Reuses existing gateway with retry/circuit-breaking; follows `LLMAgent` pattern

### Decision: Async Chat Endpoint

**Choice**: Chat endpoint creates task, returns task ID immediately, execution happens in background
**Alternatives considered**: Keep blocking execution, WebSocket for results
**Rationale**: Meets spec requirement; simple client integration; task status available via existing task API

## Data Flow

```
User Request → ChatEndpoint → CognitiveEngine.process()
                                    ↓
                              DecisionAction.CREATE_TASK
                                    ↓
                              TaskManager.create_task()
                                    ↓
                              EventBus.publish("task.created")
                                    ↓
                    ┌───────────────┴───────────────┐
                    ↓                               ↓
          DependencyResolver              TaskExecutor
          (checks deps)                   (subscribes)
                    ↓                               ↓
          If deps met → task.queued       On task.queued → dispatch
                    ↓                               ↓
                    └───────────────┬───────────────┘
                                    ↓
                              AgentManager.dispatch()
                                    ↓
                              BuiltinAgent.execute()
                                    ↓
                              ModelGateway.chat()
                                    ↓
                              TaskManager.transition_task()
                                    ↓
                              EventBus.publish("task.completed")
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/orchestrator/task_executor.py` | Create | Event-driven executor class with lifecycle management |
| `backend/app/orchestrator/dependency_resolver.py` | Modify | Emit `task.queued` when deps satisfied |
| `backend/app/agents/builtins/executor_agent.py` | Modify | Replace stub with LLM-powered execution |
| `backend/app/agents/builtins/coder_agent.py` | Modify | Replace stub with LLM-powered code generation |
| `backend/app/agents/builtins/research_agent.py` | Modify | Replace stub with LLM-powered research |
| `backend/app/agents/builtins/planner_agent.py` | Modify | Replace stub with LLM-powered planning |
| `backend/app/api/v1/routes/nova_web.py` | Modify | Return task ID, extract CognitiveEngine result |
| `backend/app/cognitive/engine.py` | Modify | Return task ID in CREATE_TASK result |

## Interfaces / Contracts

### TaskExecutor Class

```python
class TaskExecutor:
    """Event-driven task executor."""
    
    def __init__(
        self,
        event_bus: InMemoryEventBus,
        task_manager: TaskManager,
        agent_manager: AgentManager,
    ) -> None: ...
    
    async def start(self) -> None:
        """Subscribe to task.created events."""
    
    async def stop(self) -> None:
        """Unsubscribe from events."""
    
    async def _handle_task_created(self, event: Event) -> None:
        """Handle task.created → check deps → queue or hold."""
    
    async def _handle_task_queued(self, event: Event) -> None:
        """Handle task.queued → dispatch to agent."""
    
    async def _dispatch_to_agent(self, task_id: str, task_data: dict) -> None:
        """Dispatch task to assigned agent via AgentManager."""
    
    async def _handle_agent_result(
        self, task_id: str, result: dict, context: dict
    ) -> None:
        """Process agent result → transition to COMPLETED/FAILED."""
```

### Builtin Agent Execute Signatures

```python
# ExecutorAgent
async def execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
    """Execute task using LLM. Returns: {agent, status, result, summary}"""

# CoderAgent  
async def execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
    """Generate code using LLM. Returns: {agent, status, code, language, summary}"""

# ResearchAgent
async def execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
    """Research using LLM. Returns: {agent, status, findings, sources, summary}"""

# PlannerAgent
async def execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
    """Create plan using LLM. Returns: {agent, status, plan, steps, summary}"""
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | TaskExecutor state transitions | Mock EventBus, TaskManager, verify transitions |
| Unit | Builtin agents LLM calls | Mock ModelGateway, verify prompt construction |
| Unit | DependencyResolver re-queue | Mock TaskRepository, verify task.queued emission |
| Integration | Full task lifecycle | Create task → verify COMPLETED status |
| Integration | Chat endpoint async | Send request → verify task ID returned |
| E2E | End-to-end execution | Chat → task created → agent executes → result stored |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary.

## Migration / Rollout

No migration required. All changes are additive (new TaskExecutor) or modify existing behavior (agents return real results). The chat endpoint change is backward-compatible — clients can ignore the task_id field if not needed.

## Open Questions

- [ ] Should TaskExecutor have configurable concurrency limits?
- [ ] Should we add task status polling endpoint for async results?
- [ ] Should builtin agents have configurable timeouts per spec?
