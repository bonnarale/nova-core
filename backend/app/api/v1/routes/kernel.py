import json
import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from app.kernel import create_session, get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kernel", tags=["Kernel"])


class ExecuteRequest(BaseModel):
    task: str
    agent_id: str
    session_id: str | None = None


@router.post("/execute")
async def execute(request: Request, body: ExecuteRequest):
    """Execute a task through the kernel with full memory orchestration.

    Flow:
      1. Resolve or create a kernel session (in-memory).
      2. Ensure the DB session exists and persist the user message.
      3. Retrieve conversation history (includes the just-saved message).
      4. Inject history into the session context so the agent can build
         ``[system-prompt] + [history]``.
      5. Run the agent via the kernel.
      6. Persist the assistant response.
    """
    kernel = request.app.state.kernel
    memory = request.app.state.memory

    # ── 1. Resolver session_id ──────────────────────────────────────────
    if body.session_id:
        try:
            session_id = UUID(body.session_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid session_id format. Must be a valid UUID.",
            )
    else:
        session_id = uuid4()

    # ── 2. Asegurar sesión en el kernel (registro en memoria) ──────────
    session = get_session(session_id)
    if session is None:
        session = create_session(
            session_id=session_id,
            metadata={"task": body.task},
        )

    # ── 3. Persistir mensaje del usuario ────────────────────────────────
    await memory.ensure_session(session_id, body.agent_id)
    await memory.add_message(session_id, "user", body.task)

    # ── 4. Recuperar historial (incluye el mensaje recién guardado) ────
    history = await memory.get_history(session_id)
    logger.info("=== MEMORY_AUDIT [route handler] history from PostgreSQL ===")
    logger.info("session_id=%s  entries=%d", session_id, len(history))
    logger.info("history=%s", json.dumps(history, indent=2, ensure_ascii=False))
    ctx = session.get_context()
    ctx.metadata["history"] = history

    # ── 5. Ejecutar agente ──────────────────────────────────────────────
    try:
        result = await kernel.run_agent(
            agent_id=body.agent_id,
            task=body.task,
            session_id=session_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    # ── 6. Persistir respuesta del asistente ────────────────────────────
    response_data = result.get("response", {})
    message = response_data.get("message", {})
    assistant_content = message.get("content", "")
    if assistant_content:
        await memory.add_message(session_id, "assistant", assistant_content)

    return {
        "session_id": str(session_id),
        "result": result,
    }
