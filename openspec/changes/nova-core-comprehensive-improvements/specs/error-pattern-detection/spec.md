# Delta for error-pattern-detection

## ADDED Requirements

### Requirement: ErrorPatternStorage

The system MUST store identified error patterns as LongTermMemory entries with memory_type="error_pattern".

#### Scenario: Create error pattern from recurring failures

- GIVEN multiple execution outcomes with similar error messages
- WHEN ErrorPatternDetector analyzes outcomes
- THEN the system creates a LongTermMemory with memory_type="error_pattern"
- AND the pattern includes error signature, frequency, and affected strategies

#### Scenario: Pattern includes suggested fix

- GIVEN an error pattern with known resolution
- WHEN the pattern is stored
- THEN the pattern includes suggested_fix field (string or null)

### Requirement: ErrorPatternDetection

The system MUST identify recurring error patterns from execution outcomes.

#### Scenario: Detect pattern from repeated error messages

- GIVEN 3+ execution outcomes with error messages matching a common template
- WHEN DetectPatterns is called
- THEN the system identifies a pattern with error_signature (normalized error message)
- AND the pattern includes occurrence_count

#### Scenario: Detect pattern across strategies

- GIVEN error patterns occurring across multiple strategies
- WHEN DetectPatterns is called
- THEN the pattern includes affected_strategies list

#### Scenario: No pattern detected for isolated errors

- GIVEN a single error occurrence
- WHEN DetectPatterns is called
- THEN no pattern is created (threshold not met)

### Requirement: ErrorPatternAnalysis

The system MUST analyze patterns for insights.

#### Scenario: Compute pattern severity

- GIVEN an error pattern with occurrence_count and affected strategies
- WHEN AnalyzePattern is called
- THEN the system computes severity_score (0-1) based on frequency and impact

#### Scenario: Identify root cause candidates

- GIVEN an error pattern
- WHEN AnalyzePattern is called
- THEN the system returns root_cause_candidates (list of possible causes)

### Requirement: ErrorPatternRetrieval

The system MUST retrieve error patterns.

#### Scenario: Get patterns by error signature

- GIVEN an error signature string
- WHEN GetPatternBySignature is called
- THEN the system returns the matching pattern

#### Scenario: Get patterns by strategy

- GIVEN a strategy name
- WHEN GetPatternsByStrategy is called
- THEN the system returns all patterns affecting that strategy

#### Scenario: Get top severity patterns

- GIVEN a limit parameter
- WHEN GetTopSeverityPatterns is called
- THEN the system returns patterns sorted by severity_score descending

### Requirement: ErrorPatternSuggestion

The system MUST suggest fixes for known patterns.

#### Scenario: Suggest fix for pattern with known resolution

- GIVEN an error pattern with suggested_fix populated
- WHEN GetFixSuggestion is called
- THEN the system returns the suggested fix string

#### Scenario: No fix suggestion available

- GIVEN an error pattern with suggested_fix null
- WHEN GetFixSuggestion is called
- THEN the system returns null and indicates no known fix

### Requirement: ErrorPatternLifecycle

The system MUST manage pattern lifecycle.

#### Scenario: Archive resolved patterns

- GIVEN an error pattern with status="resolved"
- WHEN RunPatternLifecycle is called
- THEN the pattern status becomes ARCHIVED

#### Scenario: Purge old archived patterns

- GIVEN archived patterns older than retention period
- WHEN RunPatternLifecycle is called
- THEN those patterns are permanently deleted