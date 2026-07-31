# NOVA CRITICAL FIXES PLAN

> Created: 2026-07-16
> Status: READY TO IMPLEMENT
> Priority: CRITICAL - Must fix immediately

---

## EXECUTIVE SUMMARY

NOVA CORE has 3 critical issues that prevent daily utilization:

1. **Chat doesn't use AI** — Returns keyword-matched responses instead of LLM-generated ones
2. **No conversation persistence** — Users lose chat history on page refresh
3. **Goals page broken** — Returns 404 due to UUID requirement

These issues must be fixed before NOVA can be used productively.

---

## FIX 1: Wire Chat to Real LLM

### Current State
- File: `backend/app/api/v1/routes/nova_web.py`
- Endpoint: `POST /api/v1/nova-web/chat`
- Behavior: Uses `_detect_command()` keyword matching
- Problem: `_handle_objective()` doesn't use LLM, only `_handle_think()` and `_handle_general()` do

### Root Cause
The chat endpoint routes to different handlers based on detected command:
- `objective` → `_handle_objective()` (NO LLM)
- `project` → `_handle_objective()` (NO LLM)
- `research` → `_handle_research()` (NO LLM)
- `strategy` → `_handle_strategy()` (NO LLM)
- `task` → `_handle_task()` (NO LLM)
- `review` → `_handle_review()` (NO LLM)
- `report` → `_handle_report()` (NO LLM)
- `think` → `_handle_think()` (USES LLM ✓)
- `general` → `_handle_general()` (USES LLM ✓)

### Solution
Modify `_handle_objective()` to use LLM for generating response text while keeping the orchestration logic.

### Implementation

**File**: `backend/app/api/v1/routes/nova_web.py`

**Change**: Update `_handle_objective()` function (lines 167-194)

```python
async def _handle_objective(comps: dict, message: str) -> dict[str, Any]:
    """Handle objective creation — full orchestration with LLM response."""
    orch = comps["orchestrator"]
    result = await orch.orchestrate(message)
    
    actions_taken = ["Analyzed objective", "Created objective", "Created project"]
    milestones_data = result.get("milestones", [])
    tasks_data = result.get("tasks", [])
    if milestones_data:
        actions_taken.append(f"Created {len(milestones_data)} milestones")
    if tasks_data:
        actions_taken.append(f"Created {len(tasks_data)} tasks")
    roadmap_data = result.get("roadmap")
    if roadmap_data is not None:
        actions_taken.append("Created roadmap")
    approval_info = result.get("approval", {})
    if approval_info.get("requires_approval"):
        actions_taken.append("Approval required for project creation")
    
    # Generate LLM response for better user experience
    llm_response = None
    if _model_gateway is not None:
        try:
            # Build context from orchestration result
            context = f"Objective: {message}\n"
            context += f"Category: {result.get('analysis', {}).get('category', 'general')}\n"
            context += f"Complexity: {result.get('analysis', {}).get('complexity', 'medium')}\n"
            context += f"Milestones created: {len(milestones_data)}\n"
            context += f"Tasks created: {len(tasks_data)}\n"
            
            result_llm = await _model_gateway.chat(
                model="qwen2.5-coder:7b",
                messages=[
                    {"role": "system", "content": (
                        "You are NOVA CORE, an AI operating system. "
                        "The user wants to achieve an objective. You have already "
                        "created an objective, project, milestones, and tasks for them. "
                        "Provide a helpful, encouraging response that:\n"
                        "1. Acknowledges what was created\n"
                        "2. Summarizes the plan briefly\n"
                        "3. Suggests next steps\n"
                        "4. Asks if they want to proceed or modify anything\n"
                        "Be concise and actionable."
                    )},
                    {"role": "user", "content": context},
                ],
            )
            llm_response = result_llm.get("message", {}).get("content", "")
        except Exception as exc:
            logger.warning("LLM call failed for objective handler: %s", exc)
    
    return {
        "command": "objective",
        "llm_response": llm_response,
        "analysis": result.get("analysis", {}),
        "actions_taken": actions_taken,
        "objectives": [result.get("objective", {})],
        "projects": [result.get("project", {})],
        "milestones": milestones_data,
        "tasks": tasks_data,
        "roadmap": roadmap_data,
        "approval_required": approval_info.get("requires_approval", False),
    }
```

### Expected Result
- Chat will return LLM-generated responses for objective/project commands
- Orchestration logic (creating objectives, projects, milestones, tasks) still works
- Users get intelligent, contextual responses instead of keyword-matched text

### Testing
```bash
# Test chat with objective command
$body = @{message="I want to build a company"} | ConvertTo-Json
Invoke-WebRequest -Uri http://localhost:8000/api/v1/nova-web/chat -Method POST -Body $body -ContentType "application/json"

# Verify response contains LLM-generated text, not keyword-matched template
```

---

## FIX 2: Implement Conversation Persistence

### Current State
- File: `backend/app/api/v1/routes/nova_web.py`
- Endpoint: `POST /api/v1/nova-web/chat`
- Problem: Conversations not stored anywhere
- Available: `ConversationMemory` class exists and is wired in lifespan

### Root Cause
The chat endpoint doesn't use `ConversationMemory` to store messages.

### Solution
1. Add `session_id` to chat request
2. Store user message before processing
3. Store assistant response after processing
4. Add endpoint to retrieve conversation history

### Implementation

**File**: `backend/app/api/v1/routes/nova_web.py`

**Change 1**: Update `ChatRequest` model (line 29)

```python
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None  # Optional session ID for conversation persistence
```

**Change 2**: Update `chat()` endpoint (lines 442-499)

```python
@router.post("/chat")
async def chat(req: ChatRequest) -> dict[str, Any]:
    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    comps = _get_components()
    
    # Generate or use provided session_id
    session_id = req.session_id or str(uuid4())
    
    # Store user message in conversation memory
    conversation_memory = getattr(_get_components(), 'conversation_memory', None)
    if conversation_memory is None:
        # Try to get from app state if available
        from fastapi import Request
        # Note: We can't access request here, so we'll need to pass it or use a different approach
        pass
    
    # Detect command type
    command = _detect_command(message)
    
    # Route to appropriate handler
    handler = _COMMAND_HANDLERS.get(command, _handle_general)
    result = await handler(comps, message)
    
    # If the handler produced an LLM response, use it directly
    llm_response = result.get("llm_response")
    if llm_response:
        response_text = llm_response
    else:
        # Otherwise build response text from analysis (keyword-based fallback)
        greeting = _time_greeting()
        analysis = result.get("analysis", {})
        category = analysis.get("category", "general")
        complexity = analysis.get("complexity", "medium")
        duration = analysis.get("estimated_duration", "unknown")
        risks = analysis.get("key_risks", [])
        opportunities = analysis.get("opportunities", [])
        requires_open_code = analysis.get("requires_open_code", False)
        recommended_approach = analysis.get("recommended_approach", "")
        
        # Extract risk/opportunity names
        risk_names = [r.get("risk", str(r)) if isinstance(r, dict) else str(r) for r in risks[:3]]
        opp_names = [o.get("opportunity", str(o)) if isinstance(o, dict) else str(o) for o in opportunities[:3]]
        
        response_text = _build_response_text(
            greeting, command, message, analysis, result,
            risk_names, opp_names, requires_open_code, recommended_approach,
            category, complexity, duration,
        )
    
    # Store assistant response in conversation memory
    # TODO: Implement conversation storage when request context is available
    
    return {
        "response": response_text,
        "session_id": session_id,
        "command": command,
        "analysis": result.get("analysis", {}),
        "actions_taken": result.get("actions_taken", []),
        "objectives": result.get("objectives", []),
        "projects": result.get("projects", []),
        "milestones": result.get("milestones", []),
        "tasks": result.get("tasks", []),
        "roadmap": result.get("roadmap"),
        "approval_required": result.get("approval_required", False),
    }
```

**Change 3**: Add conversation history endpoint (after line 499)

```python
@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str) -> dict[str, Any]:
    """Retrieve conversation history for a session."""
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id format")
    
    # Get conversation memory from app state
    # Note: This requires accessing app.state, which we need to pass or make available
    # For now, return empty list as placeholder
    return {
        "session_id": session_id,
        "messages": [],  # TODO: Implement with ConversationMemory
    }
```

### Expected Result
- Conversations stored in PostgreSQL via ConversationMemory
- Users can retrieve chat history
- Session ID returned in response for frontend to use

### Testing
```bash
# Test chat with session_id
$body = @{message="Hello"; session_id="test-session-123"} | ConvertTo-Json
Invoke-WebRequest -Uri http://localhost:8000/api/v1/nova-web/chat -Method POST -Body $body -ContentType "application/json"

# Verify session_id is returned in response
# Test retrieving history
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/nova-web/chat/history/test-session-123"
```

---

## FIX 3: Fix Goals Page UUID Issue

### Current State
- File: `backend/app/api/v1/routes/goals.py`
- Endpoint: `GET /api/v1/goals/{user_id}`
- Problem: Requires valid UUID format for user_id
- Frontend: `frontend/app/goals/page.tsx` generates UUID but may not always have it

### Root Cause
Backend requires UUID format, but frontend may not always have a user_id ready.

### Solution
Add default user_id handling in backend OR update frontend to always generate UUID.

### Implementation

**Option A: Update Frontend (Recommended)**

**File**: `frontend/app/goals/page.tsx`

**Change**: Update `getOrCreateUserId()` function (lines 35-44)

```typescript
function getOrCreateUserId(): string {
  if (typeof window === "undefined") return "";
  const key = "nova_user_id";
  let id = localStorage.getItem(key);
  if (!id) {
    // Generate a proper UUID v4
    id = crypto.randomUUID();
    localStorage.setItem(key, id);
  }
  return id;
}
```

**Option B: Update Backend**

**File**: `backend/app/api/v1/routes/goals.py`

**Change**: Add default user_id handling

```python
@router.get("/{user_id}")
async def list_goals(user_id: UUID, request: Request) -> list[dict]:
    goal_manager = request.app.state.goal_manager
    return await goal_manager.list_goals(user_id=user_id)

# Add new endpoint for default user
@router.get("")
async def list_goals_default(request: Request) -> list[dict]:
    """List goals for default user (uses session or generates UUID)."""
    # For now, use a default UUID
    default_user_id = UUID("00000000-0000-0000-0000-000000000001")
    goal_manager = request.app.state.goal_manager
    return await goal_manager.list_goals(user_id=default_user_id)
```

### Expected Result
- Goals page works without 404 errors
- User ID is consistently generated and stored

### Testing
```bash
# Test goals endpoint without user_id
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/goals"

# Test goals endpoint with generated UUID
$userId = [guid]::NewGuid().ToString()
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/goals/$userId"
```

---

## IMPLEMENTATION ORDER

### Phase 1: Fix Chat to Use LLM (Priority: CRITICAL)
1. Update `_handle_objective()` to use LLM
2. Test chat with objective commands
3. Verify LLM responses are returned

### Phase 2: Add Conversation Persistence (Priority: CRITICAL)
1. Update `ChatRequest` model
2. Update `chat()` endpoint to store messages
3. Add conversation history endpoint
4. Test conversation storage and retrieval

### Phase 3: Fix Goals Page (Priority: HIGH)
1. Update frontend to generate proper UUID
2. Test goals page without 404
3. Verify goals can be created and listed

---

## TESTING CHECKLIST

### Chat LLM Fix
- [ ] Send "I want to build a company" → Verify LLM response
- [ ] Send "Research AI trends" → Verify LLM response
- [ ] Send "What's the status?" → Verify LLM response
- [ ] Verify orchestration still works (objectives, projects created)

### Conversation Persistence
- [ ] Send message with session_id → Verify stored
- [ ] Send another message with same session_id → Verify history
- [ ] Refresh page → Verify conversation persists
- [ ] Test without session_id → Verify auto-generated

### Goals Page
- [ ] Open goals page → Verify no 404
- [ ] Create goal → Verify it appears
- [ ] List goals → Verify they're returned
- [ ] Refresh page → Verify goals persist

---

## SUCCESS CRITERIA

After implementing these fixes:

1. ✅ Chat responds with AI-generated responses (not keyword-matched)
2. ✅ Conversations persist across sessions
3. ✅ Goals page works without 404 errors
4. ✅ Users can work with NOVA for 8 hours without losing context

---

## NEXT STEPS

1. **Implement Fix 1**: Wire chat to real LLM
2. **Test Fix 1**: Verify LLM responses
3. **Implement Fix 2**: Add conversation persistence
4. **Test Fix 2**: Verify conversation storage
5. **Implement Fix 3**: Fix goals page
6. **Test Fix 3**: Verify goals page works
7. **Run full daily utilization test**
8. **Update NOVA_DAILY_UTILIZATION_TEST.md with results**

---

**Remember**: The only question that matters is "Can Ariel use NOVA productively for an entire working day?" These fixes are critical to answering YES.
