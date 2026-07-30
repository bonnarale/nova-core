# Autonomous Loop Specification

## Purpose

Enable NOVA to proactively review active Goals, identify pending tasks, and execute them autonomously — subject to dual gating (AutonomyManager level + approval gate). Each cycle persists one activity log entry per goal reviewed.

## Requirements

### Requirement: Autonomous Cycle Execution

The system SHALL run a background loop that periodically reviews active Goals and executes pending autonomous actions. The loop MUST be configurable via the `NOVA_AUTONOMOUS_INTERVAL_HOURS` environment variable (default: 1 hour).

#### Scenario: Cycle runs on interval

- GIVEN the autonomous loop is started during app lifespan
- WHEN the configured interval (default 1 hour) elapses
- THEN the loop calls `GoalManager.get_next_actions()` for the default user
- AND processes each returned goal independently

#### Scenario: Cycle completes with no active goals

- GIVEN the autonomous loop is started
- WHEN `get_next_actions()` returns an empty list
- THEN the loop creates a single activity log entry with status "skipped" and reason "no active goals"
- AND waits for the next interval

#### Scenario: Interval configurable via environment

- GIVEN `NOVA_AUTONOMOUS_INTERVAL_HOURS=2` is set
- WHEN the app starts
- THEN the autonomous loop runs every 2 hours instead of the default 1 hour

### Requirement: Dual Gate Check

The system MUST enforce both AutonomyManager level gating AND approval gate before executing any autonomous action. Both gates MUST pass for execution to proceed.

#### Scenario: AutonomyManager level permits execution

- GIVEN the AutonomyManager governor level is `AUTONOMOUS` or `FULL`
- AND the goal is active and not blocked
- WHEN the autonomous loop evaluates the goal
- THEN the autonomy gate passes and the action proceeds to approval check

#### Scenario: AutonomyManager level blocks execution

- GIVEN the AutonomyManager governor level is `MANUAL`
- WHEN the autonomous loop evaluates any goal
- THEN the loop creates an activity log entry with status "skipped" and reason "autonomy level too low"
- AND no approval request is created

#### Scenario: Approval gate permits execution

- GIVEN the autonomy gate passed
- AND the approval gate checks `ApprovalsManager.requires_approval("autonomous_task")`
- WHEN the policy does NOT require approval (or approval was pre-granted)
- THEN the action executes

#### Scenario: Approval gate blocks execution

- GIVEN the autonomy gate passed
- AND the approval gate requires approval for `autonomous_task`
- WHEN no approval has been granted
- THEN the loop creates an activity log entry with status "blocked" and reason "approval required"
- AND no execution occurs

### Requirement: Goal Processing

The system MUST process each goal from `get_next_actions()` independently. If one goal fails, other goals MUST still be processed.

#### Scenario: Multiple goals processed independently

- GIVEN `get_next_actions()` returns 3 goals
- WHEN the loop processes goal 1 and it fails
- THEN goals 2 and 3 are still processed
- AND each goal produces its own activity log entry

#### Scenario: Goal is blocked

- GIVEN a goal has status "blocked" (has a `block_reason`)
- WHEN the loop evaluates this goal
- THEN the activity log entry records status "skipped" with reason equal to the block_reason
- AND the loop moves to the next goal

### Requirement: Loop Lifecycle

The autonomous loop MUST be started during FastAPI lifespan startup and stopped during shutdown. The loop task MUST be stored on `app.state.autonomous_loop` for lifecycle management.

#### Scenario: Loop starts on app boot

- GIVEN the FastAPI app starts
- WHEN the lifespan handler runs
- THEN `app.state.autonomous_loop` is set to a running asyncio.Task
- AND the scheduler is started before the loop

#### Scenario: Loop stops on app shutdown

- GIVEN the FastAPI app is shutting down
- WHEN the lifespan handler runs the cleanup block
- THEN the autonomous loop task is cancelled
- AND the loop awaits graceful completion

#### Scenario: Loop disabled via environment

- GIVEN `NOVA_AUTONOMOUS_ENABLED=false` is set
- WHEN the app starts
- THEN no autonomous loop task is created
- AND no activity log entries are produced

### Requirement: Activity Logging

Every autonomous cycle MUST produce one activity log entry per goal reviewed. Entries MUST be persisted to Postgres via the `activity_log` table.

#### Scenario: Successful execution logged

- GIVEN a goal was successfully executed
- WHEN the execution completes
- THEN an activity log entry is created with status "executed", the goal ID, and a summary of the action taken

#### Scenario: Failed execution logged

- GIVEN a goal execution raises an exception
- WHEN the exception is caught
- THEN an activity log entry is created with status "failed", the goal ID, and the error message
- AND the loop continues to the next goal

### Requirement: Event Publishing

The system MUST publish an event to the EventBus after each autonomous action completes (success or failure).

#### Scenario: Event published on success

- GIVEN an autonomous action completed successfully
- WHEN the activity log entry is created
- THEN an event with type `autonomous.action.completed` is published to the EventBus

#### Scenario: Event published on failure

- GIVEN an autonomous action failed
- WHEN the activity log entry is created
- THEN an event with type `autonomous.action.failed` is published to the EventBus
