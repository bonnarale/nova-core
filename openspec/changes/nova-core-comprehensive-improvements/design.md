# Design: nova-core-comprehensive-improvements

## Technical Approach

Extend existing Learning and Long-Term Memory subsystems with three additive capabilities: enhanced success metrics (quality, resource, impact tracking), user preference memory (CRUD + semantic search via LTM), and error pattern detection (recurring failure analysis stored as LTM). All changes follow existing dataclass + ABC + Strategy patterns. No database migrations required — new fields are additive, new memory types are enum additions.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|----------|--------|-------------|-----------|
| Metrics storage | Extend `ExecutionOutcome` dataclass | Separate MetricsStore | Keeps metrics co-located with outcomes; OutcomeStore already persists them |
| Preference memory | New `PreferenceManager` over existing `MemoryStore` | Separate PreferenceStore | Reuses LTM infrastructure (CRUD, dedup, lifecycle, semantic search) |
| Error patterns | New `ErrorPatternAnalyzer` reads from `OutcomeStore` | Embed in SuccessTracker | Single Responsibility — tracker aggregates, analyzer detects patterns |
| Conflict resolution | Semantic similarity via existing `DeduplicationEngine` | New similarity engine | Reuses proven Jaccard + embedding approach |
| Pattern threshold | Configurable (default 3 occurrences) | Hard-coded | Allows tuning without code changes |

## Data Flow

```
Task EventBus → OutcomeTracker → ExecutionOutcome (extended)
                                       │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
             SuccessTracker     ErrorPatternAnalyzer   (future)
             (quality/resource   (pattern detection)
              aggregation)
                    │                   │
                    ▼                   ▼
              MetricsAPI         LongTermMemory
                                 (memory_type=error_pattern)

User interactions → PreferenceManager → LongTermMemory
                                        (memory_type=preference)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/learning/models.py` | Modify | Add `OutputQuality`, `ResourceMetrics`, `SystemImpact` dataclasses; extend `ExecutionOutcome` with quality_score, resource_metrics, system_impact fields |
| `backend/app/learning/success_tracker.py` | Modify | Add `compute_average_quality_by_strategy()`, `compute_resource_utilization_by_strategy()`, `get_metrics_by_execution_id()`, `get_metrics_by_time_range()`, `get_aggregated_metrics_by_strategy()` |
| `backend/app/long_term_memory/models.py` | Modify | Add `PREFERENCE = "preference"` and `ERROR_PATTERN = "error_pattern"` to `MemoryType` enum |
| `backend/app/long_term_memory/manager.py` | Modify | Add preference-specific methods: `create_preference()`, `get_preferences_by_user()`, `update_preference()`, `delete_preference()`, `search_preferences()`, `resolve_preference_conflict()` |
| `backend/app/learning/error_pattern_analyzer.py` | Create | New `ErrorPatternAnalyzer` class: `detect_patterns()`, `analyze_pattern()`, `get_pattern_by_signature()`, `get_patterns_by_strategy()`, `get_top_severity_patterns()`, `get_fix_suggestion()`, `run_pattern_lifecycle()` |
| `tests/backend/test_enhanced_metrics.py` | Create | Tests for quality scoring, resource metrics, system impact, aggregation APIs |
| `tests/backend/test_preference_memory.py` | Create | Tests for preference CRUD, search, conflict resolution |
| `tests/backend/test_error_pattern_analyzer.py` | Create | Tests for pattern detection, severity, suggestions, lifecycle |

## Interfaces / Contracts

```python
# --- Extended models (learning/models.py) ---

@dataclass
class OutputQuality:
    score: int  # 0-100, None for partial/failure
    scoring_method: str = "manual"  # "manual" | "heuristic"

@dataclass
class ResourceMetrics:
    memory_used_mb: float | None = None
    cpu_time_ms: float | None = None
    tokens_used: int | None = None

@dataclass
class SystemImpact:
    latency_ms: float | None = None
    throughput_ops_per_sec: float | None = None

# ExecutionOutcome gains: quality_score: int | None,
#   resource_metrics: ResourceMetrics | None, system_impact: SystemImpact | None

# --- New error_pattern_analyzer.py ---

class ErrorPatternAnalyzer:
    def __init__(self, outcome_store: OutcomeStore, ltm_manager: LongTermMemoryManager): ...

    async def detect_patterns(self, min_occurrences: int = 3) -> list[ErrorPattern]: ...
    async def analyze_pattern(self, pattern_id: str) -> PatternAnalysis: ...
    async def get_pattern_by_signature(self, signature: str) -> ErrorPattern | None: ...
    async def get_patterns_by_strategy(self, strategy: str) -> list[ErrorPattern]: ...
    async def get_top_severity_patterns(self, limit: int = 10) -> list[ErrorPattern]: ...
    async def get_fix_suggestion(self, pattern_id: str) -> str | None: ...
    async def run_pattern_lifecycle(self, retention_days: int = 90) -> LifecycleResult: ...

@dataclass
class ErrorPattern:
    id: str
    error_signature: str
    occurrence_count: int
    affected_strategies: list[str]
    severity_score: float  # 0.0-1.0
    suggested_fix: str | None = None
    root_cause_candidates: list[str] = field(default_factory=list)

@dataclass
class PatternAnalysis:
    severity_score: float
    root_cause_candidates: list[str]
    occurrence_count: int
    affected_strategies: list[str]

# --- Extended PreferenceManager methods (long_term_memory/manager.py) ---

async def create_preference(self, user_id: str, content: str,
    tags: list[str] | None = None, categories: list[str] | None = None,
    metadata: dict[str, Any] | None = None) -> LongTermMemory: ...

async def get_preferences_by_user(self, user_id: str,
    tag: str | None = None, category: str | None = None,
    limit: int = 50) -> list[LongTermMemory]: ...

async def update_preference(self, memory_id: str,
    content: str | None = None, metadata: dict[str, Any] | None = None) -> LongTermMemory | None: ...

async def delete_preference(self, memory_id: str) -> bool: ...
async def permanent_delete_preference(self, memory_id: str) -> bool: ...

async def search_preferences(self, user_id: str, query: str,
    limit: int = 10) -> RetrievalResult: ...

async def resolve_preference_conflict(self, existing_id: str,
    new_content: str, resolution: str = "supersede") -> LongTermMemory | None: ...
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | OutputQuality validation (0-100 range), ResourceMetrics optional fields, SystemImpact fields | Dataclass creation + field validation |
| Unit | SuccessTracker new aggregation methods | FakeOutcomeStore with seeded data |
| Unit | PreferenceManager CRUD, soft/permanent delete, search, conflict resolution | FakeMemoryStore + FakeMemoryRetriever |
| Unit | ErrorPatternAnalyzer detection threshold, severity scoring, lifecycle | FakeOutcomeStore + FakeMemoryStore |
| Integration | Full metrics pipeline: record → aggregate → retrieve | OutcomeTracker → SuccessTracker → MetricsAPI |
| Integration | Preference round-trip: create → search → update → delete | PreferenceManager over FakeMemoryStore |
| Integration | Error pattern: detect → analyze → suggest → archive | ErrorPatternAnalyzer over both stores |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary.

## Migration / Rollout

No migration required. All changes are additive:
- New optional fields on `ExecutionOutcome` default to `None`
- New enum values (`PREFERENCE`, `ERROR_PATTERN`) are additions, not modifications
- New classes are independent and injected via constructors
- Existing tests remain unchanged

## Open Questions

- [ ] Should quality scoring be heuristic-based (automatic) or require manual annotation? (Proposal Q1 — default to manual with heuristic future)
- [ ] Should error pattern detection run on every outcome or batch/scheduled? (Proposal Q3 — default to on-demand via `detect_patterns()`)
