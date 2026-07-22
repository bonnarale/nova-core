# Tasks: nova-core-comprehensive-improvements

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 500–700 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 |
| Delivery strategy | ask-on-risk |
| Chain strategy | feature-branch-chain |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Foundation models + enum extensions | PR 1 | `pytest tests/backend/test_enhanced_metrics.py::TestOutputQuality` | N/A — pure dataclass validation | `learning/models.py`, `long_term_memory/models.py` |
| 2 | SuccessTracker aggregation methods | PR 2 | `pytest tests/backend/test_enhanced_metrics.py::TestSuccessTrackerExtended` | N/A — unit tests with FakeOutcomeStore | `learning/success_tracker.py` |
| 3 | PreferenceManager + ErrorPatternAnalyzer | PR 3 | `pytest tests/backend/test_preference_memory.py tests/backend/test_error_pattern_analyzer.py` | N/A — unit tests with fake stores | `long_term_memory/manager.py`, `learning/error_pattern_analyzer.py` |

## Phase 1: Foundation Models

- [x] 1.1 Add `OutputQuality`, `ResourceMetrics`, `SystemImpact` dataclasses to `backend/app/learning/models.py`
- [x] 1.2 Extend `ExecutionOutcome` with `quality_score`, `resource_metrics`, `system_impact` optional fields
- [x] 1.3 Add `PREFERENCE` and `ERROR_PATTERN` to `MemoryType` enum in `backend/app/long_term_memory/models.py`
- [x] 1.4 Write `tests/backend/test_enhanced_metrics.py` — OutputQuality validation (0-100 range, null for partial/failure), ResourceMetrics optional fields, SystemImpact fields, ExecutionOutcome serialization

## Phase 2: SuccessTracker Extensions

- [ ] 2.1 Add `compute_average_quality_by_strategy()` to `backend/app/learning/success_tracker.py`
- [ ] 2.2 Add `compute_resource_utilization_by_strategy()` method
- [ ] 2.3 Add `get_metrics_by_execution_id()` method
- [ ] 2.4 Add `get_metrics_by_time_range()` method
- [ ] 2.5 Add `get_aggregated_metrics_by_strategy()` method
- [ ] 2.6 Extend `tests/backend/test_enhanced_metrics.py` — test empty store, quality averaging, resource utilization, metrics retrieval, time-range filtering

## Phase 3: PreferenceManager

- [ ] 3.1 Add `create_preference()` to `backend/app/long_term_memory/manager.py` — creates LongTermMemory with `memory_type="preference"`
- [ ] 3.2 Add `get_preferences_by_user()` with tag/category filters
- [ ] 3.3 Add `update_preference()` and `update_preference_metadata()` methods
- [ ] 3.4 Add `delete_preference()` (soft) and `permanent_delete_preference()` methods
- [ ] 3.5 Add `search_preferences()` with semantic search
- [ ] 3.6 Add `resolve_preference_conflict()` with supersede resolution
- [ ] 3.7 Write `tests/backend/test_preference_memory.py` — CRUD, filters, soft/permanent delete, search, conflict resolution

## Phase 4: ErrorPatternAnalyzer

- [ ] 4.1 Create `backend/app/learning/error_pattern_analyzer.py` with `ErrorPatternAnalyzer` class, `ErrorPattern` and `PatternAnalysis` dataclasses
- [ ] 4.2 Implement `detect_patterns(min_occurrences=3)` — groups failures by normalized error signature
- [ ] 4.3 Implement `analyze_pattern()` — computes severity_score from frequency and affected strategies
- [ ] 4.4 Implement retrieval methods: `get_pattern_by_signature()`, `get_patterns_by_strategy()`, `get_top_severity_patterns()`
- [ ] 4.5 Implement `get_fix_suggestion()` and `run_pattern_lifecycle()` (archive resolved, purge old)
- [ ] 4.6 Write `tests/backend/test_error_pattern_analyzer.py` — threshold detection, cross-strategy patterns, severity scoring, lifecycle archival

## Phase 5: Integration Verification

- [ ] 5.1 Run full test suite: `pytest tests/backend/test_enhanced_metrics.py tests/backend/test_preference_memory.py tests/backend/test_error_pattern_analyzer.py -v`
- [ ] 5.2 Verify existing tests pass: `pytest tests/backend/test_success_tracker.py tests/backend/test_long_term_memory.py -v`
- [ ] 5.3 Verify no regressions: `pytest tests/backend/ -v --tb=short`
