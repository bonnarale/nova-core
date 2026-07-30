# Proposal: Fase C — Autonomous Execution Engine

## Intent

Transform NOVA from a reactive chat-driven system into an autonomous agent that proactively reviews Projects/Goals, identifies pending tasks, and executes them — respecting the existing approval gate. Activity must be visible in the Dashboard.

## Scope

### In Scope

- Wire Scheduler into `app.state.scheduler` in `main.py` lifespan
- Create `AutonomousLoop` — background asyncio task that calls `run_pending()` every N hours
- Register job handlers: `review_goals`, `execute_pending_actions`, `log_activity`
- Add `ActivityLog` model + Postgres table for persisting autonomous actions
- Add `/api/v1/activity` endpoint (list recent activity)
- Add "Actividad reciente" section to Dashboard frontend
- Activity log entries created automatically when autonomous loop executes jobs

### Out of Scope

- Persisting scheduler state to Postgres (in-memory accepted for now — jobs lost on restart)
- Persisting Projects to Postgres (already in-memory, separate concern)
- Modifying the approval gate logic (already supports `autonomous_task`)
- Multi-tenant autonomous execution (single-user for now)
- Real-time WebSocket activity streaming (polling is sufficient)

## Capabilities

### New Capabilities

- `autonomous-loop`: Background scheduler loop that periodically reviews goals/projects and executes pending autonomous actions
- `activity-log`: Persistent activity log tracking all autonomous executions with timestamps, status, and results

### Modified Capabilities

- `scheduler-integration`: Scheduler must be wired into app.state and started during lifespan (currently disconnected)

## Approach

### Key Decisions

1. **Accept in-memory scheduler persistence** — The scheduler is already fully in-memory. Adding Postgres persistence for jobs is a separate, larger effort. For Fase C, jobs are recreated on restart via a startup registration step. Rationale: unblocks autonomous behavior immediately; persistence is a follow-up.

2. **Activity log goes to Postgres** — Unlike scheduler state, activity records are audit-trail data that MUST survive restarts. Use a new `activity_log` table via SQLAlchemy. Rationale: users need to see what NOVA did, even after restart.

3. **Autonomous loop as asyncio.Task** — Run as a background task in the FastAPI lifespan, not as a scheduled job itself. Rationale: avoids circular dependency (scheduler can't schedule itself); simpler lifecycle management.

4. **Approval gate integration** — Every autonomous action checks `ApprovalsManager` before execution. If approval is required and not granted, the action is logged as "blocked" and skipped. Rationale: safety first; the existing `autonomous_task` action type already has policies defined.

5. **Configurable interval** — Default 4 hours, configurable via environment variable `NOVA_AUTONOMOUS_INTERVAL_HOURS`. Rationale: allows tuning without code changes.

### Architecture

```
main.py lifespan
  ├── Scheduler (app.state.scheduler) — started, jobs registered
  ├── AutonomousLoop (app.state.autonomous_loop)
  │     ├── runs every N hours
  │     ├── calls GoalRepository.get_next_actions()
  │     ├── for each action: checks approval gate
  │     ├── if approved: executes via registered handler
  │     ├── logs result to ActivityLog (Postgres)
  │     └── publishes event to EventBus
  └── ActivityLog API
        └── GET /api/v1/activity → recent entries for Dashboard
```

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/app/main.py` | Modified | Wire scheduler, create autonomous loop, register startup jobs |
| `backend/app/scheduler/` | Modified | Add `autonomous_loop.py` (background loop) |
| `backend/app/scheduler/executor.py` | Modified | Register autonomous job handlers |
| `backend/app/db/models.py` | Modified | Add `ActivityLog` SQLAlchemy model |
| `backend/app/api/v1/routes/` | New | `activity.py` — GET endpoint for activity feed |
| `backend/app/api/v1/router.py` | Modified | Include activity router |
| `frontend/app/nova/dashboard.tsx` | Modified | Add "Actividad reciente" section |
| `frontend/lib/nova-api.ts` | Modified | Add `getActivity()` API method |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Scheduler jobs lost on restart | High (accepted) | Startup re-registration of autonomous jobs; activity log persists in Postgres |
| Autonomous loop interferes with user actions | Medium | Approval gate blocks risky actions; configurable interval; loop can be paused via API |
| Activity log table grows unbounded | Low | Add TTL cleanup job or pagination limit on query |
| Autonomous actions consume excessive LLM tokens | Medium | Set `max_retries=1` and `timeout=60` on autonomous jobs; limit actions per cycle |

## Rollback Plan

1. Set `NOVA_AUTONOMOUS_ENABLED=false` env var to disable the loop without code changes
2. Remove `autonomous_loop.py` and revert `main.py` lifespan changes
3. Activity log table can be dropped independently (no FK dependencies)

## Dependencies

- Scheduler module (already exists, 14 files)
- GoalRepository with `get_next_actions()` (already exists, Postgres-backed)
- ApprovalsManager with `autonomous_task` policy (already exists)
- EventBus for publishing activity events (already exists)

## Success Criteria

- [ ] `app.state.scheduler` is set in `main.py` lifespan and scheduler starts on boot
- [ ] Autonomous loop runs every N hours and calls `get_next_actions()`
- [ ] Actions are executed only when approval gate permits
- [ ] Activity log entries appear in Postgres `activity_log` table
- [ ] `GET /api/v1/activity` returns recent entries with correct data
- [ ] Dashboard "Actividad reciente" section displays activity entries
- [ ] `docker compose restart backend && sleep 8 && docker compose logs backend --tail=30` shows scheduler started and loop registered
- [ ] No changes to existing chat-driven behavior

## Proposal question round

Before finalizing, I have these questions to sharpen the proposal:

1. **Autonomy level gating**: Should the autonomous loop respect the `AutonomyManager` level (0.0–1.0), only executing actions within the current level's capabilities? Or does the approval gate alone provide sufficient control?

2. **Default interval**: Is 4 hours the right default, or should it be shorter (1 hour) for faster iteration during development?

3. **Activity granularity**: Should each autonomous cycle produce ONE activity entry (batch summary) or ONE entry per goal/action reviewed (detailed)?

4. **Dashboard section placement**: Should "Actividad reciente" appear as a new Card below the existing sections, or replace the current "Approvals" section?
