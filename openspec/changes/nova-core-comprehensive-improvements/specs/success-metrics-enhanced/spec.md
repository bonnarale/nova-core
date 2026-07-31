# Delta for success-metrics-enhanced

## ADDED Requirements

### Requirement: OutputQualityTracking

The system MUST capture output quality scores (0-100) for each execution outcome.

#### Scenario: Record quality score for successful execution

- GIVEN an execution outcome with outcome="success"
- WHEN the outcome is recorded via SuccessTracker
- THEN the system stores a quality_score integer between 0 and 100
- AND the quality_score is associated with the execution_id

#### Scenario: Quality score omitted for partial/failure

- GIVEN an execution outcome with outcome="partial" or "failure"
- WHEN the outcome is recorded
- THEN the system stores quality_score as null (not applicable)

#### Scenario: Quality score validation

- GIVEN a quality_score value outside 0-100 range
- WHEN the outcome is recorded
- THEN the system rejects the recording with a validation error

### Requirement: ResourceMetricsTracking

The system MUST capture resource utilization metrics per execution outcome.

#### Scenario: Record memory usage

- GIVEN an execution outcome
- WHEN the outcome is recorded
- THEN the system stores memory_used_mb (float) representing peak memory usage

#### Scenario: Record CPU time

- GIVEN an execution outcome
- WHEN the outcome is recorded
- THEN the system stores cpu_time_ms (float) representing total CPU time

#### Scenario: Record token usage

- GIVEN an execution outcome from an LLM-based execution
- WHEN the outcome is recorded
- THEN the system stores tokens_used (int) representing total tokens consumed

#### Scenario: Resource metrics optional

- GIVEN an execution outcome without resource metrics
- WHEN the outcome is recorded
- THEN the system stores resource metrics as null values

### Requirement: SystemImpactTracking

The system MUST capture system impact metrics per execution outcome.

#### Scenario: Record latency impact

- GIVEN an execution outcome
- WHEN the outcome is recorded
- THEN the system stores latency_ms (float) representing end-to-end latency

#### Scenario: Record throughput impact

- GIVEN an execution outcome
- WHEN the outcome is recorded
- THEN the system stores throughput_ops_per_sec (float) representing operations per second

### Requirement: AggregatedMetrics

The system MUST compute aggregated quality and resource metrics per strategy.

#### Scenario: Compute average quality per strategy

- GIVEN multiple execution outcomes with quality scores for strategy "X"
- WHEN ComputeAverageQualityByStrategy is called
- THEN the system returns average quality score for strategy "X"

#### Scenario: Compute resource utilization per strategy

- GIVEN multiple execution outcomes with resource metrics for strategy "X"
- WHEN ComputeResourceUtilizationByStrategy is called
- THEN the system returns average memory, CPU, and token usage for strategy "X"

### Requirement: MetricsRetrievalAPI

The system MUST provide API to retrieve quality and resource metrics.

#### Scenario: Retrieve metrics by execution ID

- GIVEN an execution ID with recorded metrics
- WHEN GetMetricsByExecutionId is called
- THEN the system returns full metrics object (quality, resource, impact)

#### Scenario: Retrieve aggregated metrics by strategy

- GIVEN a strategy name with multiple outcomes
- WHEN GetAggregatedMetricsByStrategy is called
- THEN the system returns aggregated metrics (averages, counts)

#### Scenario: Retrieve metrics with time range filter

- GIVEN a start and end timestamp
- WHEN GetMetricsByTimeRange is called
- THEN the system returns metrics for outcomes within that range