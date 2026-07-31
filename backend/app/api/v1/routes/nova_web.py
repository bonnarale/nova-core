"""NOVA Web Platform — unified API for the web dashboard."""
from __future__ import annotations

import datetime
import logging
from typing import Any
from uuid import UUID, uuid4

from app.kernel import create_session, get_session

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)


def _utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid4())

router = APIRouter(prefix="/nova-web", tags=["nova-web"])

_components: dict[str, Any] | None = None
_bootstrap_done: bool = False
_model_gateway: Any = None


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None  # Optional session ID for conversation persistence


def set_dependencies(model_gateway: Any = None) -> None:
    global _model_gateway
    _model_gateway = model_gateway


def _get_components(request: Request | None = None) -> dict[str, Any]:
    global _components
    if _components is None:
        from app.command_center.factory import CommandCenterFactory

        _components = CommandCenterFactory.create_all()
    # Override approvals with the shared instance from app.state if available
    if request is not None:
        shared_approvals = getattr(request.app.state, "approvals_manager", None)
        if shared_approvals is not None:
            _components["approvals"] = shared_approvals
    return _components


# ---------------------------------------------------------------------------
# 1. Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard")
async def dashboard() -> dict[str, Any]:
    comps = _get_components()

    try:
        system_status = await comps["orchestrator"].get_status()
    except Exception:
        system_status = {"error": "unable to retrieve status"}

    active_objectives = comps["objectives"].list_active()
    active_projects = comps["projects"].list_all()
    pending_approvals = comps["approvals"].get_pending()
    recent_recommendations = comps["recommendations"].list_all()
    backlog_items = comps["backlog"].list_items()
    metrics_snapshot = comps["metrics"].snapshot()
    lifecycle = comps["lifecycle"].to_dict()
    roadmaps = comps["roadmap"].list_all()

    return {
        "system_status": system_status,
        "objectives": {
            "count": len(active_objectives),
            "items": [o.__dict__ for o in active_objectives],
        },
        "projects": {
            "count": len(active_projects),
            "items": [p.__dict__ for p in active_projects],
        },
        "approvals": {
            "count": len(pending_approvals),
            "items": [a.__dict__ for a in pending_approvals],
        },
        "recommendations": {
            "count": len(recent_recommendations),
            "items": [r.__dict__ for r in recent_recommendations],
        },
        "backlog": {
            "count": len(backlog_items),
            "items": [b.__dict__ for b in backlog_items],
        },
        "roadmaps": {
            "count": len(roadmaps),
            "items": [rm.__dict__ for rm in roadmaps],
        },
        "metrics": metrics_snapshot,
        "lifecycle": lifecycle,
    }


# ---------------------------------------------------------------------------
# 2. Chat — NOVA Command System
# ---------------------------------------------------------------------------

_SYSTEM_COMMANDS = {
    "/help": "Available commands:\n  /help — Show this help\n  /status — System status\n  /health — Health check\n  /clear — Clear session",
    "/status": "System operational. Chat is delegated to the NOVA kernel with full memory orchestration.",
    "/health": "OK",
}


@router.post("/chat")
async def chat(req: ChatRequest, request: Request) -> dict[str, Any]:
    """Chat endpoint — delegates substantive messages to the NOVA kernel.

    Trivial system commands (/help, /status, /health) are handled inline
    for instant response.  Everything else goes through the kernel's
    ``run_agent`` pipeline which provides full memory orchestration:
    conversation history, semantic memory, user profile, and goals injection.
    """
    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Generate or use provided session_id
    session_id = req.session_id or str(uuid4())

    # --- Lightweight system-command dispatch (no LLM overhead) ---
    if message.lower() in _SYSTEM_COMMANDS:
        response_text = _SYSTEM_COMMANDS[message.lower()]

        # Store exchange in conversation memory
        conversation_memory = getattr(request.app.state, "memory", None)
        if conversation_memory is not None:
            try:
                session_uuid = UUID(session_id) if len(session_id) == 36 else uuid4()
                await conversation_memory.ensure_session(session_uuid, "nova_web")
                await conversation_memory.add_message(session_uuid, "user", message)
                await conversation_memory.add_message(session_uuid, "assistant", response_text)
            except Exception as exc:
                logger.warning("Failed to store system command in memory: %s", exc)

        return {
            "response": response_text,
            "session_id": session_id,
            "task_id": None,
            "actions_taken": [],
            "objectives": [],
            "projects": [],
            "tasks": [],
            "approval_required": False,
        }

    # --- Kernel delegation for all substantive messages ---
    kernel = request.app.state.kernel
    memory = request.app.state.memory

    # 1. Resolve or create kernel session
    session_id_uuid = UUID(session_id) if len(session_id) == 36 else uuid4()
    session = get_session(session_id_uuid)
    if session is None:
        session = create_session(
            session_id=session_id_uuid,
            metadata={"source": "nova_web_chat"},
        )

    # 2. Persist user message
    await memory.ensure_session(session_id_uuid, "nova_web")
    await memory.add_message(session_id_uuid, "user", message)

    # 3. Retrieve conversation history (includes the just-saved message)
    history = await memory.get_history(session_id_uuid)
    ctx = session.get_context()
    ctx.metadata["history"] = history

    # 4. Inject semantic memory
    semantic_memory = request.app.state.semantic_memory
    relevant_memories = await semantic_memory.search(message)
    ctx.metadata["semantic_memories"] = relevant_memories
    await semantic_memory.store(session_id_uuid, message)

    # 5. Run agent via kernel (with cognitive engine intent detection)
    task_id: str | None = None
    kernel_result: dict[str, Any] = {}
    try:
        # Try cognitive engine for intent detection first
        cognitive_engine = getattr(request.app.state, "cognitive_engine", None)
        agent_id = "assistant"  # default
        
        logger.info("Chat: cognitive_engine available=%s", cognitive_engine is not None)
        
        if cognitive_engine is not None:
            from app.cognitive.decision import DecisionAction
            state = await cognitive_engine.process(
                raw_input=message,
                user_id=None,
                session_id=str(session_id_uuid),
            )
            action = state.decision.action if state.decision else DecisionAction.ROUTE_TO_KERNEL
            
            logger.info("Chat: cognitive action=%s", action)
            
            # Extract task_id from execution_result for CREATE_TASK actions
            if action == DecisionAction.CREATE_TASK and state.execution_result:
                task_id = state.execution_result.get("task_id")
                logger.info("Chat: task created with id=%s", task_id)
            
            # Check if approval was auto-rejected (budget exceeded, etc.)
            if state.execution_result and state.execution_result.get("approval_rejected"):
                return {
                    "response": state.execution_result.get("message", "Action rejected by policy."),
                    "session_id": session_id,
                    "task_id": None,
                    "actions_taken": [],
                    "objectives": [],
                    "projects": [],
                    "tasks": [],
                    "approval_required": False,
                    "approval_rejected": True,
                    "approval_id": state.execution_result.get("approval_id"),
                    "approval_category": state.execution_result.get("approval_category"),
                    "reason": state.execution_result.get("reason"),
                }

            # Check if approval is required (gate intercepted the action) — BEFORE routing
            if state.execution_result and state.execution_result.get("approval_required"):
                approval_id = state.execution_result.get("approval_id")
                approval_category = state.execution_result.get("approval_category")
                message_text = state.execution_result.get("message", "Approval required")
                return {
                    "response": message_text,
                    "session_id": session_id,
                    "task_id": None,
                    "actions_taken": [],
                    "objectives": [],
                    "projects": [],
                    "tasks": [],
                    "approval_required": True,
                    "approval_id": approval_id,
                    "approval_category": approval_category,
                }

            # If cognitive engine delegated to an agent, use the execution result directly
            delegation_actions = {
                DecisionAction.DELEGATE_TO_PLANNER,
                DecisionAction.DELEGATE_TO_RESEARCHER,
                DecisionAction.DELEGATE_TO_CODER,
                DecisionAction.DELEGATE_TO_EXECUTOR,
                DecisionAction.DELEGATE_TO_MEMORY,
                DecisionAction.DELEGATE_TO_REVIEWER,
                DecisionAction.DELEGATE_TO_OPENCODE,
            }

            # Handle tool execution results (consulting, etc.)
            if action == DecisionAction.EXECUTE_TOOL and state.execution_result:
                logger.info("Chat: tool execution result from %s",
                            state.execution_result.get("tool_name"))
                tool_result = state.execution_result
                if tool_result.get("success"):
                    data = tool_result.get("data", {})
                    if isinstance(data, dict) and "content" in data:
                        response_text = data["content"]
                    else:
                        response_text = tool_result.get("message", str(data))
                else:
                    response_text = f"Error: {tool_result.get('error', 'Tool execution failed')}"
                kernel_result = tool_result
            elif action in delegation_actions and state.execution_result:
                logger.info("Chat: using delegation result from %s", action.value)
                kernel_result = state.execution_result
                # Extract agent_id from the result for response formatting
                if "agent_id" in state.execution_result:
                    agent_id = state.execution_result["agent_id"]
            else:
                # If cognitive engine routes to a specific agent, use that
                if action == DecisionAction.RUN_META_CYCLE:
                    agent_id = "meta"
                elif hasattr(state.decision, 'agent_id') and state.decision.agent_id:
                    agent_id = state.decision.agent_id

                logger.info("Chat: routing to agent=%s", agent_id)
                
                kernel_result = await kernel.run_agent(
                    agent_id=agent_id,
                    task=message,
                    session_id=session_id_uuid,
                )
    except Exception as exc:
        logger.error("Kernel execution failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your message. Please try again.",
        )

    # 6. Extract response text from kernel result
    # Handle delegation results, LLMAgent format, and MetaAgent format
    response_text = ""

    # Handle tool execution results (consulting, search_market, etc.)
    if isinstance(kernel_result, dict) and "tool_name" in kernel_result and "success" in kernel_result:
        if kernel_result.get("success"):
            data = kernel_result.get("data", {})
            if isinstance(data, dict) and "content" in data:
                response_text = data["content"]
            elif isinstance(data, dict):
                response_text = str(data)
            else:
                response_text = str(data) if data else kernel_result.get("message", "Tool executed successfully")
        else:
            response_text = f"Error: {kernel_result.get('error', 'Tool execution failed')}"
    
    # Handle delegation results (from cognitive engine)
    if not response_text and "result" in kernel_result and "agent_id" in kernel_result:
        # This is a delegation result from _execute_delegate
        agent_result = kernel_result["result"]
        if isinstance(agent_result, dict):
            # Try to extract response from agent result
            response_data = agent_result.get("response", {})
            if isinstance(response_data, dict):
                message_obj = response_data.get("message", {})
                if isinstance(message_obj, dict):
                    response_text = message_obj.get("content", "")
            
            # If no response text, check for other formats
            if not response_text:
                # Handle planner agent format (plan, steps, summary)
                if "plan" in agent_result and "steps" in agent_result:
                    plan = agent_result["plan"]
                    steps = agent_result["steps"]
                    summary = agent_result.get("summary", "")
                    
                    # Format the plan nicely
                    parts = []
                    if plan:
                        parts.append(f"**Plan:** {plan}")
                    if steps:
                        parts.append("\n**Steps:**")
                        for i, step in enumerate(steps, 1):
                            parts.append(f"{i}. {step}")
                    if summary:
                        parts.append(f"\n**Summary:** {summary}")
                    
                    response_text = "\n".join(parts)
                elif "summary" in agent_result:
                    response_text = agent_result["summary"]
                elif "error" in agent_result:
                    response_text = f"Error: {agent_result['error']}"
                elif "content" in agent_result:
                    response_text = agent_result["content"]
    
    # Try LLMAgent format first (if not already extracted)
    if not response_text:
        response_data = kernel_result.get("response", {})
        if isinstance(response_data, dict):
            message_obj = response_data.get("message", {})
            if isinstance(message_obj, dict):
                response_text = message_obj.get("content", "")
    
    # If no response text, try MetaAgent format
    if not response_text:
        # MetaAgent returns "summary" or "status" with details
        if "summary" in kernel_result:
            response_text = kernel_result["summary"]
        elif "status" in kernel_result and kernel_result["status"] == "completed":
            # Build response from audit results
            targets = kernel_result.get("targets", [])
            goals = kernel_result.get("goals_created", [])
            improvements = kernel_result.get("improvements", [])
            
            parts = []
            if targets:
                parts.append(f"Identified {len(targets)} improvement targets:")
                for t in targets[:3]:
                    parts.append(f"  - {t.get('description', t.get('type', 'unknown'))}")
            if goals:
                parts.append(f"\nCreated {len(goals)} improvement goals.")
            if improvements:
                parts.append(f"\nDelegated {len(improvements)} improvements to OpenCodeAgent.")
            
            response_text = "\n".join(parts) if parts else f"Evolution cycle {kernel_result.get('status', 'unknown')}"
        elif "error" in kernel_result:
            response_text = f"Error: {kernel_result['error']}"
    
    # Fallback to raw result if nothing else works
    if not response_text:
        response_text = str(kernel_result)

    # 7. Persist assistant response
    if response_text:
        await memory.add_message(session_id_uuid, "assistant", response_text)

    return {
        "response": response_text,
        "session_id": session_id,
        "task_id": task_id,
        "actions_taken": [],
        "objectives": [],
        "projects": [],
        "tasks": [],
        "approval_required": False,
    }


@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str, request: Request) -> dict[str, Any]:
    """Retrieve conversation history for a session."""
    conversation_memory = getattr(request.app.state, 'memory', None)
    
    if conversation_memory is None:
        return {
            "session_id": session_id,
            "messages": [],
            "error": "Conversation memory not available",
        }
    
    try:
        from uuid import UUID
        session_uuid = UUID(session_id)
        messages = await conversation_memory.get_history(session_uuid, limit=50)
        return {
            "session_id": session_id,
            "messages": messages,
        }
    except Exception as exc:
        logger.warning("Failed to retrieve conversation history: %s", exc)
        return {
            "session_id": session_id,
            "messages": [],
            "error": str(exc),
        }





# ---------------------------------------------------------------------------
# 3. Objectives
# ---------------------------------------------------------------------------

def _normalize_objective(o: Any) -> dict[str, Any]:
    """Normalize objective data: scale progress from 0.0-1.0 to 0-100."""
    d = o.__dict__ if hasattr(o, "__dict__") else dict(o)
    progress = d.get("progress", 0.0)
    if isinstance(progress, float) and progress <= 1.0:
        d["progress"] = round(progress * 100, 1)
    return d


@router.get("/objectives")
async def list_objectives() -> list[dict[str, Any]]:
    comps = _get_components()
    return [_normalize_objective(o) for o in comps["objectives"].list_all()]


# ---------------------------------------------------------------------------
# 4. Projects
# ---------------------------------------------------------------------------

def _normalize_project(p: Any) -> dict[str, Any]:
    """Normalize project data: scale progress from 0.0-1.0 to 0-100."""
    d = p.__dict__ if hasattr(p, "__dict__") else dict(p)
    progress = d.get("progress", 0.0)
    if isinstance(progress, float) and progress <= 1.0:
        d["progress"] = round(progress * 100, 1)
    return d


class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""
    objective_id: str | None = None


@router.get("/projects")
async def list_projects() -> list[dict[str, Any]]:
    comps = _get_components()
    return [_normalize_project(p) for p in comps["projects"].list_all()]


@router.post("/projects")
async def create_project(req: CreateProjectRequest) -> dict[str, Any]:
    comps = _get_components()
    project = comps["projects"].create(
        name=req.name,
        description=req.description,
        objective_id=req.objective_id,
    )
    return _normalize_project(project)


# ---------------------------------------------------------------------------
# 5. Roadmaps
# ---------------------------------------------------------------------------

@router.get("/roadmaps")
async def list_roadmaps() -> list[dict[str, Any]]:
    comps = _get_components()
    return [r.__dict__ for r in comps["roadmap"].list_all()]


# ---------------------------------------------------------------------------
# 6. Tasks (aggregated from objectives)
# ---------------------------------------------------------------------------

@router.get("/tasks")
async def list_tasks() -> list[dict[str, Any]]:
    comps = _get_components()
    tasks: list[dict[str, Any]] = []
    for obj in comps["objectives"].list_all():
        for task in obj.tasks:
            task_with_context = {**task, "objective_id": obj.id}
            tasks.append(task_with_context)
    return tasks


# ---------------------------------------------------------------------------
# 7. Backlog
# ---------------------------------------------------------------------------

@router.get("/backlog")
async def list_backlog() -> list[dict[str, Any]]:
    comps = _get_components()
    return [_normalize_backlog(b) for b in comps["backlog"].list_items()]


# ---------------------------------------------------------------------------
# 8. Approvals
# ---------------------------------------------------------------------------

@router.get("/approvals")
async def list_approvals(request: Request) -> list[dict[str, Any]]:
    comps = _get_components(request)
    return [a.__dict__ for a in comps["approvals"].get_pending()]


@router.get("/approvals/history")
async def approval_history(request: Request) -> list[dict[str, Any]]:
    comps = _get_components(request)
    return [a.__dict__ for a in comps["approvals"].get_resolved()]


# ---------------------------------------------------------------------------
# 9. Approve — and re-execute the original action
# ---------------------------------------------------------------------------

@router.post("/approvals/{approval_id}/approve")
async def approve_item(approval_id: str, request: Request) -> dict[str, Any]:
    comps = _get_components(request)
    approval = comps["approvals"].approve(approval_id, reviewer="web_user")
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")

    # Record budget usage if a project has a budget set
    projects_mgr = getattr(request.app.state, "projects_manager", None)
    if projects_mgr is not None and hasattr(projects_mgr, 'projects'):
        for project in projects_mgr.projects.values():
            if hasattr(project, 'approval_budget') and project.approval_budget:
                comps["approvals"].record_budget_usage(project.approval_budget, approval.risk_level)
                break  # Record for first project with budget

    # Re-execute the original action that was gated
    execution_result = None
    metadata = approval.metadata or {}
    original_payload = metadata.get("payload", {})
    action_type = approval.action_type

    cognitive_engine = getattr(request.app.state, "cognitive_engine", None)
    if cognitive_engine is not None and original_payload:
        # Reconstruct the original message from the payload
        original_message = (
            original_payload.get("objective")
            or original_payload.get("task")
            or original_payload.get("query")
            or approval.description
        )
        session_id = original_payload.get("session_id")
        user_id = original_payload.get("user_id")

        logger.info(
            "Approval %s: re-executing action %s with skip_approval_check=True",
            approval_id, action_type,
        )
        try:
            state = await cognitive_engine.process(
                raw_input=original_message,
                user_id=user_id,
                session_id=session_id,
                skip_approval_check=True,
            )
            execution_result = state.execution_result
        except Exception as exc:
            logger.error("Approval re-execution failed: %s", exc, exc_info=True)
            execution_result = {"error": str(exc)}

    # Record approval_grant decision in project if bridge is available
    project_goal_bridge = getattr(request.app.state, "project_goal_bridge", None)
    if project_goal_bridge is not None:
        project_id = original_payload.get("project_id") if original_payload else None
        if project_id:
            try:
                await project_goal_bridge.record_decision(
                    project_id=project_id,
                    action_type="approval_grant",
                    agent_id="web_user",
                    description=f"Approval granted for: {approval.description}",
                    result_summary=f"Action {approval.action_type} approved by web_user",
                )
            except Exception:
                logger.debug("Failed to record approval_grant decision")

    return {
        "approval": approval.__dict__,
        "execution_result": execution_result,
    }


# ---------------------------------------------------------------------------
# 10. Reject
# ---------------------------------------------------------------------------

@router.post("/approvals/{approval_id}/reject")
async def reject_item(approval_id: str, request: Request) -> dict[str, Any]:
    comps = _get_components(request)
    result = comps["approvals"].reject(approval_id, reviewer="web_user")
    if result is None:
        raise HTTPException(status_code=404, detail="Approval not found")

    # Record approval_reject decision in project if bridge is available
    project_goal_bridge = getattr(request.app.state, "project_goal_bridge", None)
    if project_goal_bridge is not None:
        # Find the original approval to get metadata
        original = comps["approvals"].get(approval_id)
        if original is not None:
            metadata = getattr(original, "metadata", {}) or {}
            payload = metadata.get("payload", {}) or {}
            project_id = payload.get("project_id")
            if project_id:
                try:
                    await project_goal_bridge.record_decision(
                        project_id=project_id,
                        action_type="approval_reject",
                        agent_id="web_user",
                        description=f"Approval rejected for: {original.description}",
                        result_summary=f"Action {original.action_type} rejected by web_user",
                    )
                except Exception:
                    logger.debug("Failed to record approval_reject decision")

    return result.__dict__


# ---------------------------------------------------------------------------
# 11. Recommendations
# ---------------------------------------------------------------------------

@router.get("/recommendations")
async def list_recommendations() -> list[dict[str, Any]]:
    comps = _get_components()
    return [r.__dict__ for r in comps["recommendations"].list_all()]


# ---------------------------------------------------------------------------
# 12. Accept recommendation
# ---------------------------------------------------------------------------

@router.post("/recommendations/{rec_id}/accept")
async def accept_recommendation(rec_id: str) -> dict[str, Any]:
    comps = _get_components()
    result = comps["recommendations"].accept(rec_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return result.__dict__


# ---------------------------------------------------------------------------
# 13. Memory / status
# ---------------------------------------------------------------------------

@router.get("/memory")
async def get_memory() -> dict[str, Any]:
    comps = _get_components()
    data: dict[str, Any] = {
        "learning": {},
        "vector_memory": {},
        "knowledge_graph": {},
    }

    try:
        data["learning"] = comps["self_improvement"].to_dict()
    except Exception:
        data["learning"] = {"status": "unavailable"}

    try:
        from app.api.v1.routes import vector_memory as _vm_module  # noqa: F401
        data["vector_memory"] = {"status": "module_present"}
    except Exception:
        data["vector_memory"] = {"status": "unavailable"}

    try:
        from app.api.v1.routes import knowledge_graph as _kg_module  # noqa: F401
        data["knowledge_graph"] = {"status": "module_present"}
    except Exception:
        data["knowledge_graph"] = {"status": "unavailable"}

    data["command_center_memory"] = comps["objectives"].to_dict()
    return data


# ---------------------------------------------------------------------------
# 14. Observability
# ---------------------------------------------------------------------------

@router.get("/observability")
async def get_observability(request: Request) -> dict[str, Any]:
    comps = _get_components(request)
    
    # Real API metrics from the global collector
    api_metrics = getattr(request.app.state, "api_metrics", None)
    api_tracer = getattr(request.app.state, "api_tracer", None)
    
    api_stats = api_metrics.get_statistics() if api_metrics else {}
    api_traces = api_tracer.get_recent_traces(limit=50) if api_tracer else []
    
    # Compute latency percentiles from the rolling window
    latency_percentiles = {}
    if api_metrics and hasattr(api_metrics, '_latencies'):
        latencies = api_metrics._latencies
        if latencies:
            sorted_lat = sorted(latencies)
            n = len(sorted_lat)
            latency_percentiles = {
                "p50": round(sorted_lat[n // 2], 2),
                "p95": round(sorted_lat[int(n * 0.95)], 2),
                "p99": round(sorted_lat[int(n * 0.99)], 2),
            }
    
    return {
        "metrics": comps["metrics"].snapshot(),
        "api_metrics": {
            "total_requests": api_stats.get("total_requests", 0),
            "total_errors": api_stats.get("total_errors", 0),
            "error_rate": api_stats.get("error_rate", 0.0),
            "average_latency_ms": api_stats.get("average_latency_ms", 0.0),
            "latency_percentiles": latency_percentiles,
            "endpoint_usage": api_stats.get("endpoint_usage", {}),
        },
        "traces": {
            "command_center": comps["tracing"].to_dict(),
            "api_recent": api_traces,
        },
        "health": comps["lifecycle"].to_dict(),
    }


# ---------------------------------------------------------------------------
# 15. Tools
# ---------------------------------------------------------------------------

@router.get("/tools")
async def get_tools(request: Request) -> dict[str, Any]:
    comps = _get_components(request)
    
    # Real tool execution data from ToolRuntime
    tool_runtime = getattr(request.app.state, "tool_runtime", None)
    tool_manager = getattr(request.app.state, "tool_manager", None)
    
    tool_catalog = []
    tool_metrics_snapshot = {}
    tool_traces_recent = []
    
    if tool_runtime:
        tool_metrics_snapshot = tool_runtime.metrics.snapshot() if hasattr(tool_runtime, 'metrics') else {}
        if hasattr(tool_runtime, 'tracer'):
            tool_traces_recent = tool_runtime.tracer.to_dict()[:20]  # last 20
    
    if tool_manager:
        tool_catalog = [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "version": t.version,
            }
            for t in tool_manager.list_tools()
        ]
    
    return {
        "catalog": tool_catalog,
        "metrics": tool_metrics_snapshot,
        "recent_executions": tool_traces_recent,
        "orchestrator": comps["orchestrator"].to_dict(),
        "autonomy": comps["autonomy"].to_dict(),
    }


# ---------------------------------------------------------------------------
# 16. Create Roadmap (POST)
# ---------------------------------------------------------------------------

class CreateRoadmapRequest(BaseModel):
    name: str
    description: str = ""
    start_year: int = 0
    end_year: int = 0
    duration_years: int = 0


@router.post("/roadmaps")
async def create_roadmap(req: CreateRoadmapRequest) -> dict[str, Any]:
    comps = _get_components()
    current_year = datetime.datetime.now().year
    start = req.start_year or current_year
    end = req.end_year or (start + max(req.duration_years, 1))
    roadmap = comps["roadmap"].create(
        name=req.name,
        description=req.description,
        duration_years=req.duration_years or max(1, end - start),
        start_year=start,
        end_year=end,
    )
    return roadmap.__dict__


# ---------------------------------------------------------------------------
# 17. Create Backlog Item (POST)
# ---------------------------------------------------------------------------

_PRIORITY_STR_TO_INT: dict[str, int] = {
    "critical": 1, "high": 2, "medium": 3, "low": 4,
}
_PRIORITY_INT_TO_STR: dict[int, str] = {v: k for k, v in _PRIORITY_STR_TO_INT.items()}


def _normalize_backlog(b: Any) -> dict[str, Any]:
    """Normalize backlog item: convert priority int to string for frontend."""
    d = b.__dict__ if hasattr(b, "__dict__") else dict(b)
    p = d.get("priority", 3)
    if isinstance(p, int):
        d["priority"] = _PRIORITY_INT_TO_STR.get(p, "medium")
    return d


class CreateBacklogRequest(BaseModel):
    title: str
    description: str = ""
    category: str = "general"
    priority: str | int = "medium"
    source: str = "user"


@router.post("/backlog")
async def create_backlog(req: CreateBacklogRequest) -> dict[str, Any]:
    comps = _get_components()
    if isinstance(req.priority, str):
        priority_int = _PRIORITY_STR_TO_INT.get(req.priority.lower(), 3)
    else:
        priority_int = req.priority
    item = comps["backlog"].add(
        title=req.title,
        description=req.description,
        category=req.category,
        priority=priority_int,
        source=req.source,
    )
    return _normalize_backlog(item)


# ---------------------------------------------------------------------------
# 18. NOVA Self-Management Bootstrap
# ---------------------------------------------------------------------------

_NOVA_SELF_PROJECT_BOOTSTRAPPED = False


@router.post("/bootstrap")
async def bootstrap_nova() -> dict[str, Any]:
    """Bootstrap NOVA as its own first project. Run once on first call."""
    global _NOVA_SELF_PROJECT_BOOTSTRAPPED
    if _NOVA_SELF_PROJECT_BOOTSTRAPPED:
        return {"status": "already_bootstrapped", "message": "NOVA self-project already exists"}

    comps = _get_components()
    governor = comps.get("governor")
    orch = comps["orchestrator"]

    # Create NOVA's own objective
    nova_objective = await orch.orchestrate(
        "NOVA must become the user's primary intelligence operating system"
    )

    # Add NOVA-specific backlog items
    nova_backlog_items = [
        ("Implement LLM-powered analysis", "Replace keyword matching with Model Gateway", "technology", 1),
        ("Add database persistence for Command Center", "Persist objectives, projects, tasks across restarts", "technology", 1),
        ("Implement task execution via AgentRuntime", "Dispatch tasks to agents for actual execution", "technology", 2),
        ("Add real-time dashboard updates", "WebSocket or polling for live status", "technology", 2),
        ("Implement approval enforcement", "Block execution until approvals are granted", "technology", 2),
        ("Add auth system", "JWT-based authentication for web platform", "technology", 3),
        ("Deduplicate command_center/constitution/autonomy", "Merge overlapping managers into one", "refactoring", 3),
        ("Clean up dead frontend components", "Remove unused charts, common, workflow components", "refactoring", 3),
    ]
    for title, desc, cat, priority in nova_backlog_items:
        comps["backlog"].add(title=title, description=desc, category=cat, priority=priority, source="nova_bootstrap")

    # Create NOVA's roadmap
    nova_roadmap = comps["roadmap"].create(
        name="NOVA Self-Improvement Roadmap",
        description="Strategic roadmap for NOVA to become the primary intelligence OS",
        duration_years=1,
    )

    _NOVA_SELF_PROJECT_BOOTSTRAPPED = True

    return {
        "status": "bootstrapped",
        "message": "NOVA self-project created successfully",
        "objective": nova_objective.get("objective", {}),
        "project": nova_objective.get("project", {}),
        "backlog_items": len(nova_backlog_items),
        "roadmap": nova_roadmap.__dict__,
    }


# ---------------------------------------------------------------------------
# 19. Daily Mode — Continuous Evaluation
# ---------------------------------------------------------------------------

@router.get("/daily")
async def daily_mode() -> dict[str, Any]:
    """Daily mode: continuous evaluation of projects, priorities, and optimizations."""
    comps = _get_components()
    orch = comps.get("orchestrator")
    governor = comps.get("governor")

    # Gather current state
    active_objectives = comps["objectives"].list_active()
    active_projects = comps["projects"].list_all()
    pending_approvals = comps["approvals"].get_pending()
    backlog_items = list(comps["backlog"].items.values())
    recommendations = comps["recommendations"].list_all()

    # Generate daily assessment
    assessment = {
        "timestamp": _utcnow(),
        "active_objectives": len(active_objectives),
        "active_projects": len(active_projects),
        "pending_approvals": len(pending_approvals),
        "backlog_items": len(backlog_items),
        "recommendations": len(recommendations),
    }

    # Identify priorities
    priorities = []
    if pending_approvals:
        priorities.append({
            "action": "review_approvals",
            "reason": f"{len(pending_approvals)} approval(s) pending",
            "priority": "high",
        })
    if not active_objectives and backlog_items:
        priorities.append({
            "action": "promote_backlog",
            "reason": "No active objectives; promote from backlog",
            "priority": "high",
        })
    if active_objectives:
        for obj in active_objectives:
            if obj.progress < 0.3:
                priorities.append({
                    "action": "advance_objective",
                    "reason": f"Objective '{obj.title}' at {obj.progress:.0%} — needs attention",
                    "priority": "medium",
                })

    # Identify optimizations
    optimizations = []
    if len(active_objectives) > 3:
        optimizations.append({
            "type": "workload",
            "description": f"{len(active_objectives)} active objectives — consider prioritizing",
        })
    if len(backlog_items) > 10:
        optimizations.append({
            "type": "backlog",
            "description": f"{len(backlog_items)} backlog items — consider grooming",
        })

    # Generate recommendation
    recommendation = None
    if orch:
        recommendation = await orch.recommend_next()

    return {
        "assessment": assessment,
        "priorities": priorities,
        "optimizations": optimizations,
        "recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
# 20. Self-Optimization — Detect Problems and Propose Solutions
# ---------------------------------------------------------------------------

@router.get("/self-optimize")
async def self_optimize() -> dict[str, Any]:
    """Self-optimization: detect architectural problems and propose solutions."""
    comps = _get_components()

    analysis = {
        "timestamp": _utcnow(),
        "problems": [],
        "proposals": [],
        "status": "healthy",
    }

    # Check for architectural issues
    active_objectives = comps["objectives"].list_active()
    backlog_items = list(comps["backlog"].items.values())

    # Problem: Too many active objectives
    if len(active_objectives) > 3:
        analysis["problems"].append({
            "type": "workload",
            "severity": "medium",
            "description": f"{len(active_objectives)} active objectives exceeds recommended maximum of 3",
        })
        analysis["proposals"].append({
            "action": "prioritize",
            "description": "Review active objectives and defer lower-priority items to backlog",
            "requires_open_code": False,
        })

    # Problem: Backlog growing without action
    if len(backlog_items) > 15:
        analysis["problems"].append({
            "type": "backlog_growth",
            "severity": "low",
            "description": f"{len(backlog_items)} items in backlog — consider grooming session",
        })
        analysis["proposals"].append({
            "action": "groom_backlog",
            "description": "Review and reprioritize backlog items",
            "requires_open_code": False,
        })

    # Problem: No active objectives
    if not active_objectives:
        analysis["problems"].append({
            "type": "stagnation",
            "severity": "high",
            "description": "No active objectives — NOVA is idle",
        })
        analysis["proposals"].append({
            "action": "create_objective",
            "description": "Define a new objective to drive progress",
            "requires_open_code": False,
        })

    # Problem: Pending approvals blocking progress
    pending = comps["approvals"].get_pending()
    if pending:
        analysis["problems"].append({
            "type": "approval_block",
            "severity": "medium",
            "description": f"{len(pending)} pending approval(s) may block progress",
        })
        analysis["proposals"].append({
            "action": "review_approvals",
            "description": "Review and approve pending decisions",
            "requires_open_code": False,
        })

    # Known architectural issues (from audit)
    known_issues = [
        {
            "type": "duplication",
            "severity": "medium",
            "description": "ObjectivesManager exists in 3 modules (autonomy, command_center, constitution)",
            "proposal": "Consolidate into single ObjectivesManager in command_center",
            "requires_open_code": True,
        },
        {
            "type": "persistence",
            "severity": "high",
            "description": "Command Center data is in-memory only — lost on restart",
            "proposal": "Add PostgreSQL persistence for objectives, projects, tasks, roadmaps",
            "requires_open_code": True,
        },
        {
            "type": "llm_integration",
            "severity": "medium",
            "description": "Governor uses keyword matching instead of LLM analysis",
            "proposal": "Connect Governor to ModelGateway for AI-powered analysis",
            "requires_open_code": True,
        },
    ]
    analysis["known_issues"] = known_issues

    # Determine overall status
    if any(p["severity"] == "high" for p in analysis["problems"]):
        analysis["status"] = "needs_attention"
    elif analysis["problems"]:
        analysis["status"] = "minor_issues"
    else:
        analysis["status"] = "healthy"

    return analysis


# ---------------------------------------------------------------------------
# 21. Think — Deep Analysis with 10-Step Process
# ---------------------------------------------------------------------------

@router.post("/think")
async def think(req: ChatRequest) -> dict[str, Any]:
    """Deep thinking: full 10-step analysis process."""
    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    comps = _get_components()
    governor = comps.get("governor")

    # Step 1-8: Full analysis via Governor
    analysis = {}
    if governor and hasattr(governor, "analyze_objective"):
        analysis = await governor.analyze_objective(message)

    # Step 9: Determine if execution is necessary
    requires_open_code = analysis.get("requires_open_code", False)
    requires_approval = analysis.get("requires_human_approval", False)

    # Step 10: Build reasoning
    reasoning_steps = [
        {"step": 1, "name": "Analyze", "result": f"Category: {analysis.get('category', 'general')}, Complexity: {analysis.get('complexity', 'medium')}"},
        {"step": 2, "name": "Investigate", "result": f"Dependencies: {len(analysis.get('dependencies', []))} identified"},
        {"step": 3, "name": "Reason", "result": f"Strategy: {analysis.get('recommended_approach', 'standard')}"},
        {"step": 4, "name": "Plan", "result": f"Milestones: {len(analysis.get('milestones', []))}, Tasks: {len(analysis.get('tasks', []))}"},
        {"step": 5, "name": "Prioritize", "result": f"Priority: {'high' if analysis.get('complexity') in ('high', 'very_high') else 'medium'}"},
        {"step": 6, "name": "Identify Risks", "result": f"Risks: {len(analysis.get('key_risks', []))} identified"},
        {"step": 7, "name": "Identify Opportunities", "result": f"Opportunities: {len(analysis.get('opportunities', []))} identified"},
        {"step": 8, "name": "Determine Execution", "result": f"Execution required: {requires_open_code}"},
        {"step": 9, "name": "Determine Open Code", "result": f"Open Code required: {requires_open_code}"},
        {"step": 10, "name": "Approval", "result": f"Approval required: {requires_approval}"},
    ]

    # Determine recommendation
    if not requires_open_code and not requires_approval:
        recommendation = "NO ACTION REQUIRED — Analysis complete. This is a conceptual/strategic matter."
    elif requires_open_code and not requires_approval:
        recommendation = "IMPLEMENTATION REQUIRED — Open Code should be used."
    elif requires_approval:
        recommendation = "APPROVAL REQUIRED — Human review needed before execution."
    else:
        recommendation = "INVESTIGATION REQUIRED — Further analysis needed."

    return {
        "message": message,
        "analysis": analysis,
        "reasoning_steps": reasoning_steps,
        "requires_open_code": requires_open_code,
        "requires_approval": requires_approval,
        "recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
# 22. Status — Unified Status Endpoint
# ---------------------------------------------------------------------------

@router.get("/status")
async def nova_status() -> dict[str, Any]:
    """Unified status: everything NOVA knows about itself."""
    comps = _get_components()
    orch = comps.get("orchestrator")

    status = {}
    if orch:
        status = await orch.get_status()

    active_objectives = comps["objectives"].list_active()
    active_projects = comps["projects"].list_all()
    pending_approvals = comps["approvals"].get_pending()
    backlog_items = list(comps["backlog"].items.values())
    roadmaps = comps["roadmap"].list_all()

    return {
        "nova": {
            "version": "1.0.0",
            "role": "Intelligence Operating System",
            "status": "operational",
        },
        "operational": status,
        "objectives": {
            "active": len(active_objectives),
            "items": [o.__dict__ for o in active_objectives],
        },
        "projects": {
            "active": len(active_projects),
            "items": [p.__dict__ for p in active_projects],
        },
        "approvals": {
            "pending": len(pending_approvals),
            "items": [a.__dict__ for a in pending_approvals],
        },
        "backlog": {
            "total": len(backlog_items),
            "items": [b.__dict__ for b in backlog_items[:10]],
        },
        "roadmaps": {
            "total": len(roadmaps),
            "items": [r.__dict__ for r in roadmaps],
        },
    }
