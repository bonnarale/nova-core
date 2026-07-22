from uuid import UUID

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/memory/{session_id}")
async def get_memory(
    session_id: UUID,
    request: Request,
) -> dict:
    memory = request.app.state.memory

    history = await memory.get_history(session_id)

    return {
        "session_id": str(session_id),
        "messages": history,
    }
