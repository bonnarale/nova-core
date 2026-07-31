# Proposal: nova-core-comprehensive-improvements

## Intent

Enhance nova-core's learning system, memory capabilities, and orchestration foundations to enable data-driven improvements and prepare for real agent implementations. The exploration identified 5 improvement areas with Phase 1 (Success Metrics + User Preference Memory) as the recommended first slice.

## Scope

### In Scope
- Enhanced success metrics beyond success/failure (output quality, resource utilization, system impact)
- User preference memory type for explicit learning from interactions
- Error pattern detection for recurring failures
- Comprehensive test coverage for new features
- Backward-compatible changes to existing Learning and Long-Term Memory systems

### Out of Scope
- Real agent implementations (stub agents remain as-is)
- External integrations (Git, CI/CD, Monitoring, Documentation)
- Parallel orchestration (sequential execution continues)
- Agent capability depth improvements
- UI/frontend changes

## Capabilities

### New Capabilities
- `success-metrics-enhanced`: Enhanced tracking of execution outcomes with quality scores, resource metrics, and system impact
- `user-preference-memory`: Explicit storage and retrieval of user preferences, interaction patterns, and learned behaviors
- `error-pattern-detection`: Analysis of recurring failures to identify known issues and suggested fixes

### Modified Capabilities
- None (existing specs don't exist; this will create new specs)

## Approach

**Phase 1 (First Slice):** Enhance SuccessTracker and LongTermMemory systems
1. Add OutputQuality and ResourceMetrics models to learning models
2. Extend SuccessTracker with quality/resource tracking methods
3. Add Preference memory type with CRUD operations
4. Implement error pattern analysis in SuccessTracker
5. Add comprehensive tests for all new functionality

**Future Phases (deferred):**
- Agent implementations (planner, researcher, coder)
- External integrations
- Parallel orchestration

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/app/learning/models.py` | Modified | Add OutputQuality, ResourceMetrics, ErrorPattern models |
| `backend/app/learning/success_tracker.py` | Modified | Add quality/resource tracking, error pattern analysis |
| `backend/app/long_term_memory/models.py` | Modified | Add Preference memory type |
| `backend/app/long_term_memory/manager.py` | Modified | Add preference CRUD methods |
| `tests/backend/test_success_tracker.py` | Modified | Add tests for new metrics |
| `tests/backend/test_preference_memory.py` | New | Tests for preference memory functionality |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Breaking existing Learning system | Low | Additive changes only, no existing API modifications |
| Test coverage gaps | Medium | Require comprehensive tests for all new functionality |
| Memory model changes | Low | New type addition, not modification of existing types |
| Performance impact | Low | New tracking is optional and backward-compatible |

## Rollback Plan

1. Revert all changes to learning and long_term_memory modules
2. Remove new test files
3. Existing functionality remains unchanged (no breaking changes introduced)
4. No database migrations required (new types are additive)

## Dependencies

- Existing Learning system infrastructure (OutcomeTracker, SuccessTracker)
- Existing Long-Term Memory system (CRUD, semantic search)
- pytest and pytest-asyncio for testing

## Success Criteria

- [ ] Enhanced SuccessTracker tracks output quality scores (0-100)
- [ ] Resource metrics (memory, CPU, tokens) are captured per execution
- [ ] User preference memory type supports CRUD operations
- [ ] Error pattern detection identifies recurring failures
- [ ] All new functionality has >90% test coverage
- [ ] Existing tests continue to pass (no regressions)
- [ ] Performance impact <5% for existing operations

## Proposal Question Round

**Assumptions needing review:**
1. **Business problem**: Nova-core has basic success/failure tracking but lacks quality metrics needed for data-driven improvements
2. **Target users**: System administrators and developers using nova-core for AI-assisted workflows
3. **Business rules**: New metrics must be optional and backward-compatible
4. **Product outcome**: Better visibility into system performance enabling targeted improvements
5. **Current-state gap**: Limited metrics prevent data-driven optimization of agents and workflows

**Questions for clarification:**
1. Should output quality scoring be automatic (based on heuristics) or require human annotation?
2. What specific user preferences should be tracked initially (response style, detail level, domain expertise)?
3. Should error pattern detection be real-time or batch analysis?
4. Are there specific resource metrics most valuable for optimization (token usage vs. memory vs. CPU)?
5. Should preference memory be per-user or per-project scope by default?
