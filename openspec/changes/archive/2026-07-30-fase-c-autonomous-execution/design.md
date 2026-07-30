# Design: Fase C — Autonomous Execution Engine

## Technical Approach

Make NOVA autonomous by wiring the existing in-memory scheduler into `app.state`, creating a background autonomous loop that reviews Goals, checks both AutonomyManager level AND approval gate before executing, and persisting activity to a new Postgres `activity_log` table. The Dashboard gets a new "Actividad reciente" Card.

## Architecture Decisions

### Decision: Dual Gate — AutonomyManager + Approval Gate

**Choice**: Check `AutonomyManager.can_perform()` first, then `ApprovalsManager.request("autonomous_task")` for approval.
**Alternatives considered**: Approval gate alone (rejects per user); AutonomyManager alone (no safety net).
**Rationale**: AutonomyManager controls WHAT actions are allowed at current level; approval gate controls WHETHER this specific action is granted. Both must pass.

### Decision: Background asyncio.Task, Not Scheduler Job

**Choice**: Run autonomous loop as `asyncio.Task` in FastAPI lifespan, NOT as a scheduler job.
**Alternatives considered**: Register as scheduler interval job.
**Rationale**: Scheduler jobs are lost on restart anyway. An asyncio.Task is simpler to lifecycle-manage (start/stop with lifespan) and avoids circular dependency (scheduler scheduling itself).

### Decision: One Activity Entry Per Goal Reviewed

**Choice**: Each goal reviewed produces one `ActivityLog` row.
**Alternatives considered**: Batch summary per cycle.
**Rationale**: Per-user decision. Granular entries give better dashboard visibility and audit trail.

### Decision: Postgres for Activity Log

**Choice**: SQLAlchemy async model in `app.db.models`, queried via new `ActivityLogRepository`.
**Alternatives considered**: In-memory (would lose on restart).
**Rationale**: Activity is audit-trail data that must survive restarts. Follows existing `GoalRepository` pattern.

### Decision: 1-Hour Interval, Configurable via Env Var

**Choice**: Default 3600s, overridden by `NOVA_AUTONOMOUS_INTERVAL_SECONDS` env var.
**Alternatives considered**: Fixed interval.
**Rationale**: Allows tuning without code changes; env var follows existing config pattern.

## Data Flow

```
main.py lifespan startup
  │
  ├─→ SchedulerFactory.create_scheduler() → app.state.scheduler
  │
  ├─→ register_autonomous_job(scheduler, ...)
  │     └─ Creates interval job "autonomous-review" (every 1h)
  │
  └─→ (on each tick)
        │
        ▼
    autonomous_review_handler(job)
        │
        ├─→ GoalRepository.get_next_actions(user_id) → list[Goal]
        │
        ├─→ For each goal:
        │     ├─→ AutonomyManager.can_perform("execute_task")?
        │     │     └─ NO → ActivityLog(status="skipped", reason="level_insufficient")
        │     │
        │     ├─→ ApprovalsManager.request("autonomous_task", description=...)
        │     │     └─ rejected → ActivityLog(status="blocked", reason="budget_exceeded")
        │     │     └─ pending → ActivityLog(status="pending_approval", approval_id=...)
        │     │
        │     ├─→ (if auto-approved or level allows without approval)
        │     │     └─→ Execute action → ActivityLog(status="executed"|"failed")
        │     │
        │     └─→ ActivityLogRepository.create(entry)
        │
        └─→ Return summary
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/scheduler/autonomous.py` | Create | `AutonomousReviewHandler` — the core job handler that reviews goals, checks gates, executes actions, logs activity |
| `backend/app/db/models.py` | Modify | Add `ActivityLog` SQLAlchemy model (id, goal_id, user_id, action, status, reason, approval_id, details, created_at) |
| `backend/app/db/activity_repository.py` | Create | `ActivityLogRepository` — CRUD for activity_log table (create, list_recent, get_by_id) |
| `backend/app/api/v1/routes/activity.py` | Create | `GET /api/v1/activity` — returns recent activity entries for Dashboard |
| `backend/app/api/v1/router.py` | Modify | Include activity router |
| `backend/app/main.py` | Modify | Wire scheduler into app.state, register autonomous job, init ActivityLogRepository, shutdown cleanup |
| `backend/app/core/config.py` | Modify | Add `NOVA_AUTONOMOUS_INTERVAL_SECONDS` and `NOVA_AUTONOMOUS_USER_ID` settings |
| `frontend/lib/nova-api.ts` | Modify | Add `ActivityEntry` interface and `activity()` method to NovaWebAPI |
| `frontend/app/nova/dashboard.tsx` | Modify | Add "Actividad reciente" Card below existing sections |

## Interfaces / Contracts

### ActivityLog Model (Postgres)

```python
class ActivityLog(Base):
    __tablename__ = "activity_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_id = Column(UUID(as_uuid=True), ForeignKey("goals.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(50), nullable=False)  # "reviewed", "executed", "skipped", "blocked", "failed"
    status = Column(String(20), nullable=False)   # "executed", "pending_approval", "blocked", "skipped", "failed"
    goal_title = Column(String(255), nullable=True)
    goal_priority = Column(Integer, nullable=True)
    approval_id = Column(String(100), nullable=True)
    reason = Column(Text, nullable=True)
    details = Column(JSONB, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_activity_log_user_created", "user_id", "created_at"),
        Index("ix_activity_log_goal", "goal_id"),
    )
```

### AutonomousReviewHandler Signature

```python
class AutonomousReviewHandler:
    def __init__(
        self,
        goal_repository: GoalRepository,
        autonomy_manager: AutonomyManager,
        approvals_manager: ApprovalsManager,
        activity_repository: ActivityLogRepository,
        user_id: UUID,
    ) -> None:

    async def handle(self, job: Job) -> dict[str, Any]:
        """Review goals and execute pending autonomous actions."""
```

### Activity Log API Response

```json
{
  "entries": [
    {
      "id": "uuid",
      "goal_id": "uuid",
      "goal_title": "Build REST API",
      "action": "reviewed",
      "status": "executed",
      "goal_priority": 3,
      "approval_id": null,
      "reason": null,
      "details": {},
      "created_at": "2026-07-30T10:00:00Z"
    }
  ],
  "total": 12,
  "limit": 20,
  "offset": 0
}
```

### Frontend ActivityEntry Interface

```typescript
interface ActivityEntry {
  id: string;
  goal_id: string | null;
  goal_title: string | null;
  action: string;
  status: string;
  goal_priority: number | null;
  approval_id: string | null;
  reason: string | null;
  details: Record<string, unknown>;
  created_at: string;
}
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | AutonomousReviewHandler logic | Mock GoalRepository, AutonomyManager, ApprovalsManager, ActivityLogRepository; test each branch (can_perform, approval required, execution success/failure) |
| Unit | ActivityLogRepository CRUD | Use SQLite test DB or async mock; verify create, list_recent, ordering |
| Integration | Scheduler + handler registration | Create scheduler via factory, register handler, verify job is scheduled and run_pending triggers it |
| E2E | Dashboard shows activity | Start backend, create goals, trigger autonomous cycle, verify GET /api/v1/activity returns entries; verify frontend renders Card |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary.

## Migration / Rollout

- **New table**: `activity_log` — created via `Base.metadata.create_all()` (existing pattern uses async engine; no Alembic migration yet in this project).
- **Env vars**: `NOVA_AUTONOMOUS_INTERVAL_SECONDS` (default 3600), `NOVA_AUTONOMOUS_USER_ID` (required — UUID of user whose goals are reviewed).
- **Feature flag**: If `NOVA_AUTONOMOUS_USER_ID` is not set, autonomous loop does not start. This provides a safe rollout path.

## Open Questions

- [ ] Should `NOVA_AUTONOMOUS_USER_ID` be required or default to a hardcoded UUID? (Recommendation: required, no sensible default for multi-user future)
- [ ] When approval is pending, should the handler create the ActivityLog entry immediately with status `pending_approval`, or wait for resolution? (Recommendation: create immediately so dashboard shows activity)
- [ ] Should the autonomous loop have a configurable max goals per cycle (e.g., 5) to limit LLM token usage? (Recommendation: yes, default 5, configurable via env var)
