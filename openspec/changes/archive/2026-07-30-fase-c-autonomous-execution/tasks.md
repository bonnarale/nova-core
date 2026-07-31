# Tasks: Fase C — Autonomous Execution Engine

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~413 (backend ~353, frontend ~60) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: DB + Repository (~115) → PR 2: Core backend (~238) → PR 3: Frontend (~60) |
| Delivery strategy | ask-on-risk |
| Chain strategy | feature-branch-chain |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Database + Repository | PR 1 | `pytest tests/test_activity_repository.py -v` | SQLite test DB | `activity_log` model + repository only |
| 2 | Core backend (handler, scheduler, API, config) | PR 2 | `pytest tests/test_autonomous_handler.py tests/test_activity_api.py -v` | Mock deps + scheduler | `autonomous.py`, `activity.py` route, `main.py` changes |
| 3 | Frontend card + integration | PR 3 | `npm run build && npm run test` | Browser dashboard | `dashboard.tsx`, `nova-api.ts` |

## Phase 1: Database + Repository (Work Unit 1 → PR 1)

- [x] 1.1 Add `ActivityLog` model to `backend/app/db/models.py` — columns: id (UUID PK), goal_id (UUID FK nullable), user_id (UUID FK), action (String), status (String), goal_title (String nullable), goal_priority (Integer nullable), approval_id (String nullable), reason (Text nullable), details (JSONB nullable), created_at (timestamptz). Indexes: ix_activity_log_user_created, ix_activity_log_goal. ~35 lines
- [x] 1.2 Create `backend/app/db/activity_repository.py` — `ActivityLogRepository` class with `create()`, `list_recent(limit=20)`, `get_by_id()` methods. Follow `GoalRepository` pattern (async_sessionmaker, `async with self._session_factory()`). ~80 lines
- [x] 1.3 Write tests in `backend/tests/test_activity_repository.py` — test create entry, list_recent ordering desc, default limit 20, empty DB returns [], get_by_id found/not-found. Use SQLite async test DB or mock. ~60 lines

## Phase 2: Autonomous Handler + Config (Work Unit 2 → PR 2)

- [x] 2.1 Add settings to `backend/app/core/config.py` — `NOVA_AUTONOMOUS_INTERVAL_SECONDS` (default 3600), `NOVA_AUTONOMOUS_USER_ID` (str, default ""), `NOVA_AUTONOMOUS_ENABLED` (bool, default True). ~5 lines
- [x] 2.2 Create `backend/app/scheduler/autonomous.py` — `AutonomousReviewHandler` class. Constructor takes goal_repository, autonomy_manager, approvals_manager, activity_repository, event_bus, user_id. `async def handle(job)` method: calls `get_next_actions()`, for each goal checks `AutonomyManager.can_perform("execute_task")` then `ApprovalsManager.request("autonomous_task")`, creates ActivityLog entry per goal, publishes event via EventBus. Handles blocked/skipped/failed cases per spec. ~120 lines
- [x] 2.3 Write tests in `backend/tests/test_autonomous_handler.py` — mock all deps, test: no goals → skipped entry, autonomy level blocks → skipped, approval required → blocked, execution success → executed entry + event, execution failure → failed entry + event, multiple goals processed independently. ~100 lines

## Phase 3: Scheduler Wiring + API Endpoint (Work Unit 2 → PR 2)

- [x] 3.1 Modify `backend/app/main.py` lifespan — create Scheduler via `SchedulerFactory.create_scheduler()`, store on `app.state.scheduler`, start scheduler, create `ActivityLogRepository`, create `AutonomousReviewHandler`, register autonomous loop as `asyncio.Task` on `app.state.autonomous_loop` if `NOVA_AUTONOMOUS_ENABLED` and `NOVA_AUTONOMOUS_USER_ID` set. Cancel loop on shutdown, stop scheduler after loop cancelled. ~50 lines
- [x] 3.2 Create `backend/app/api/v1/routes/activity.py` — `GET /api/v1/activity` endpoint with `limit` query param (default 20), returns `{"entries": [...], "total": N}`. Use `ActivityLogRepository` from `app.state`. ~40 lines
- [x] 3.3 Modify `backend/app/api/v1/router.py` — import activity router, `router.include_router(activity_router)`. ~3 lines
- [x] 3.4 Write tests in `backend/tests/test_activity_api.py` — test GET /api/v1/activity returns 200 with entries, test empty DB returns [], test limit param works. ~40 lines

## Phase 4: Frontend — Activity Card (Work Unit 3 → PR 3)

- [x] 4.1 Add `ActivityEntry` interface and `activity()` method to `frontend/lib/nova-api.ts` — interface matches design spec, method calls `GET /api/v1/activity?limit=5`. ~20 lines
- [x] 4.2 Add "Actividad reciente" Card to `frontend/app/nova/dashboard.tsx` — fetch activity on mount, render entries with status badge (green=executed, red=failed, yellow=skipped), goal_title, timestamp. Empty state: "No activity yet". Place below existing sections. ~40 lines
- [x] 4.3 Verify frontend builds: `cd frontend && npm run build`. ~0 lines (verification only)

## Phase 5: Integration + Cleanup

- [x] 5.1 Verify scheduler starts on boot — `docker compose restart backend && docker compose logs backend --tail=30` shows scheduler started and loop registered. ~0 lines
- [x] 5.2 Verify activity log persists — create a test goal, trigger autonomous cycle, check `GET /api/v1/activity` returns entry. ~0 lines
- [x] 5.3 Verify dashboard renders — open browser, check "Actividad reciente" Card appears. ~0 lines
