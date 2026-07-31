# Tasks: Real Agents Task Executor

## Phase 1: TaskExecutor Core

### Task 1.1: Create TaskExecutor class
- **File**: `backend/app/orchestrator/task_executor.py` (new)
- **Description**: Create event-driven executor that subscribes to task.created events
- **Acceptance criteria**:
  - Class subscribes to task.created via InMemoryEventBus
  - Handles task.created → check deps → queue or hold
  - Handles task.queued → dispatch to agent
  - Handles agent result → transition to COMPLETED/FAILED
- **Estimated lines**: ~150
- **Status**: ✅ Complete

### Task 1.2: Modify DependencyResolver to emit task.queued
- **File**: `backend/app/orchestrator/dependency_resolver.py` (modify)
- **Description**: Emit task.queued event when dependencies are satisfied
- **Acceptance criteria**:
  - After checking deps, if met, emit task.queued
  - Preserve existing behavior for unmet deps
- **Estimated lines**: ~20
- **Status**: ✅ Complete

### Task 1.3: Register TaskExecutor in main.py
- **File**: `backend/app/main.py` (modify)
- **Description**: Initialize TaskExecutor and start it during lifespan
- **Acceptance criteria**:
  - TaskExecutor created with event_bus, task_manager, agent_manager
  - Started during app startup
  - Stopped during app shutdown
- **Estimated lines**: ~30
- **Status**: ✅ Complete

### Task 1.4: Write unit tests for TaskExecutor
- **File**: `tests/backend/test_task_executor.py` (new)
- **Description**: Test state transitions, event handling, error cases
- **Acceptance criteria**:
  - Test task.created handling
  - Test task.queued handling
  - Test agent dispatch
  - Test error handling
- **Estimated lines**: ~200
- **Status**: ✅ Complete

## Phase 2: Fix Chat Endpoint

### Task 2.1: Modify chat endpoint to return task ID
- **File**: `backend/app/api/v1/routes/nova_web.py` (modify)
- **Description**: Return task_id when CognitiveEngine creates a task
- **Acceptance criteria**:
  - Extract task_id from CognitiveEngine execution result
  - Include task_id in response
  - Maintain backward compatibility
- **Estimated lines**: ~30
- **Status**: ✅ Complete

### Task 2.2: Modify CognitiveEngine to return task ID
- **File**: `backend/app/cognitive/engine.py` (modify)
- **Description**: Return task_id in CREATE_TASK result
- **Acceptance criteria**:
  - _execute_create_task returns task_id
  - Task ID available in execution_result
- **Estimated lines**: ~15
- **Status**: ✅ Complete

### Task 2.3: Write integration tests for chat endpoint
- **File**: `tests/backend/test_chat_async.py` (new)
- **Description**: Test async task creation via chat
- **Acceptance criteria**:
  - Send chat message → verify task_id returned
  - Verify task created in database
- **Estimated lines**: ~100
- **Status**: ✅ Complete

## Phase 3: Real Agent Implementations

### Task 3.1: Implement real PlannerAgent
- **File**: `backend/app/agents/builtins/planner_agent.py` (modify)
- **Description**: Replace stub with LLM-powered planning
- **Acceptance criteria**:
  - Uses ModelGateway.chat() for LLM calls
  - Returns structured plan with steps
  - Handles LLM errors gracefully
- **Estimated lines**: ~80
- **Status**: ✅ Complete

### Task 3.2: Implement real ExecutorAgent
- **File**: `backend/app/agents/builtins/executor_agent.py` (modify)
- **Description**: Replace stub with LLM-powered execution
- **Acceptance criteria**:
  - Uses ModelGateway.chat() for LLM calls
  - Returns execution results
  - Handles LLM errors gracefully
- **Estimated lines**: ~80
- **Status**: ✅ Complete

### Task 3.3: Implement real CoderAgent
- **File**: `backend/app/agents/builtins/coder_agent.py` (modify)
- **Description**: Replace stub with LLM-powered code generation
- **Acceptance criteria**:
  - Uses ModelGateway.chat() for LLM calls
  - Returns generated code
  - Handles LLM errors gracefully
- **Estimated lines**: ~80
- **Status**: ✅ Complete

### Task 3.4: Implement real ResearchAgent
- **File**: `backend/app/agents/builtins/research_agent.py` (modify)
- **Description**: Replace stub with LLM-powered research
- **Acceptance criteria**:
  - Uses ModelGateway.chat() for LLM calls
  - Returns research findings
  - Handles LLM errors gracefully
- **Estimated lines**: ~80
- **Status**: ✅ Complete

### Task 3.5: Write unit tests for LLM agents
- **File**: `tests/backend/test_llm_agents.py` (new)
- **Description**: Test all LLM-powered agents with mocked gateway
- **Acceptance criteria**:
  - Test PlannerAgent with mock LLM
  - Test ExecutorAgent with mock LLM
  - Test CoderAgent with mock LLM
  - Test ResearchAgent with mock LLM
- **Estimated lines**: ~200
- **Status**: ✅ Complete

## Phase 4: Integration Verification

### Task 4.1: Run full test suite
- **Description**: Verify no regressions
- **Acceptance criteria**:
  - All existing tests pass
  - All new tests pass
  - ruff: 0 errors in new/modified files
- **Status**: ✅ Complete

### Task 4.2: End-to-end test
- **File**: `tests/backend/test_e2e_execution.py` (new)
- **Description**: Test full flow: chat → task created → agent executes → result stored
- **Acceptance criteria**:
  - Send chat message requesting a project
  - Verify task created
  - Verify task transitions to RUNNING
  - Verify agent executes
  - Verify task transitions to COMPLETED
- **Estimated lines**: ~150
- **Status**: ✅ Complete

## Summary

| Phase | Tasks | Estimated Lines |
|-------|-------|-----------------|
| Phase 1: TaskExecutor Core | 4 | ~400 |
| Phase 2: Fix Chat Endpoint | 3 | ~145 |
| Phase 3: Real Agent Implementations | 5 | ~440 |
| Phase 4: Integration Verification | 2 | ~150 |
| **Total** | **14** | **~1,135** |

## PR Split (Stacked-to-Main)

- **PR 1** (Phase 1): TaskExecutor core + tests (~400 lines)
- **PR 2** (Phase 2): Chat endpoint fix + tests (~145 lines)
- **PR 3** (Phase 3+4): Real agents + integration tests (~590 lines)
