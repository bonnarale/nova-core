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
    user_id: str | None = None


@router.post("/execute")
async def execute(request: Request, body: ExecuteRequest):
    """Execute a task through the kernel with full memory orchestration.

    Flow:
      0. [Cognitive Engine] Intercept and decide whether to route to kernel.
      1. Resolve or create a kernel session (in-memory).
      2. Ensure the DB session exists and persist the user message.
      3. Retrieve conversation history (includes the just-saved message).
      4. Inject history into the session context so the agent can build
         ``[system-prompt] + [history]``.
      5. Run the agent via the kernel (only if cognitive engine routes there).
      6. Persist the assistant response.
    """
    from app.cognitive.engine import CognitiveEngine
    from app.cognitive.decision import DecisionAction

    cognitive_engine: CognitiveEngine | None = request.app.state.__dict__.get("cognitive_engine") if hasattr(request.app.state, "__dict__") else None

    # ── 0. Cognitive Engine — intercept and decide ──────────────────────
    if cognitive_engine is not None:
        state = await cognitive_engine.process(
            raw_input=body.task,
            user_id=body.user_id,
            session_id=body.session_id,
        )
        action = state.decision.action if state.decision else DecisionAction.ROUTE_TO_KERNEL

        # Non-kernel actions are handled by the engine itself
        if action not in (DecisionAction.ROUTE_TO_KERNEL, DecisionAction.FALLBACK):
            return {
                "session_id": body.session_id,
                "cognitive_decision": state.decision.to_dict() if state.decision else None,
                "cognitive_execution": state.execution_result,
            }

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

    # ── 4a. Memoria semántica (almacenar + recuperar) ───────────────────
    semantic_memory = request.app.state.semantic_memory
    relevant_memories = await semantic_memory.search(body.task)
    ctx.metadata["semantic_memories"] = relevant_memories

    # Almacenar mensaje actual como memoria semántica
    await semantic_memory.store(session_id, body.task)

    # ── 4b. Extraer, fusionar, persistir e inyectar perfil de usuario ──
    if body.user_id:
        try:
            uid = UUID(body.user_id)
            profile_memory = request.app.state.profile_memory

            # Extraer información de los mensajes del usuario
            from app.services.extractor import MemoryExtractor
            extractor = MemoryExtractor()
            extracted = extractor.extract(history)

            # Cargar o crear perfil
            profile = await profile_memory.get_profile(uid)
            if profile is None:
                profile = await profile_memory.create_profile(uid)

            logger.info("=== PROFILE BEFORE ===")
            logger.info(json.dumps(profile, indent=2, ensure_ascii=False))
            logger.info("=== EXTRACTED DATA ===")
            logger.info(json.dumps(extracted, indent=2, ensure_ascii=False))

            if extracted:
                name = extracted.get("name")
                goals = extracted.get("goals")
                preferences = extracted.get("preferences")
                facts = extracted.get("facts")

                # Merge goals — dedup and accumulate
                existing_goals = profile.get("goals") or []
                new_goals = [g for g in (goals or []) if g not in existing_goals]
                merged_goals = existing_goals + new_goals if new_goals else None

                # Merge preferences — dict merge, never overwrite with empty
                merged_prefs = None
                if preferences:
                    existing_prefs = profile.get("preferences") or {}
                    merged_prefs = {**existing_prefs, **preferences}

                # Always persist name if extracted (latest self-ID wins)
                await profile_memory.update_profile(
                    uid,
                    name=name,
                    goals=merged_goals,
                    preferences=merged_prefs,
                )

                # add_facts maneja deduplicación internamente
                if facts:
                    await profile_memory.add_facts(uid, facts)

            # Reload perfil actualizado (get_profile is always called so that
            # ctx.metadata always gets the freshest state)
            profile = await profile_memory.get_profile(uid)
            logger.info("=== PROFILE AFTER ===")
            logger.info(json.dumps(profile, indent=2, ensure_ascii=False))

            ctx.metadata["user_profile"] = profile or {}
        except ValueError:
            ctx.metadata["user_profile"] = {}
            logger.warning("Invalid user_id format: %s", body.user_id)
    else:
        ctx.metadata["user_profile"] = {}

    # ── 4c. Goal manager: extraer, crear e inyectar ─────────────────────
    if body.user_id:
        try:
            uid = UUID(body.user_id)
            goal_manager = request.app.state.goal_manager

            # Extraer metas del último mensaje del usuario
            from app.services.extractor import MemoryExtractor
            extractor = MemoryExtractor()
            extracted = extractor.extract(history)
            user_goals = extracted.get("goals", [])

            for goal_text in user_goals:
                try:
                    await goal_manager.create_goal(uid, title=goal_text, priority=3)
                except Exception:
                    logger.debug("Goal already exists or create skipped: %s", goal_text)

            # Inyectar estado actual de metas en el contexto
            goals = await goal_manager.list_goals(uid)
            next_actions = await goal_manager.get_next_actions(uid)
            analysis = await goal_manager.analyze_progress(uid)

            ctx.metadata["goals"] = {
                "goals": goals,
                "next_actions": next_actions,
                "analysis": analysis,
            }

            logger.info("=== GOALS INJECTED ===")
            logger.info("goals=%d  next_actions=%d", len(goals), len(next_actions))
        except ValueError:
            ctx.metadata["goals"] = {}
            logger.warning("Invalid user_id format for goals: %s", body.user_id)
    else:
        ctx.metadata["goals"] = {}

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
