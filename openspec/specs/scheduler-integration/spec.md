# Scheduler Integration Specification

## Purpose

Wire the existing in-memory Scheduler into the FastAPI app lifecycle so it starts on boot, is accessible via `app.state.scheduler`, and can have jobs registered at startup.

## Requirements

### Requirement: Scheduler Wired into App State

The system MUST create a `Scheduler` instance and store it on `app.state.scheduler` during the FastAPI lifespan startup. The scheduler MUST be started before any jobs are registered.

#### Scenario: Scheduler available on app.state

- GIVEN the FastAPI app starts
- WHEN the lifespan handler runs
- THEN `app.state.scheduler` is a `Scheduler` instance
- AND `app.state.scheduler.is_running()` returns `True`

#### Scenario: Scheduler started before job registration

- GIVEN the lifespan handler is initializing
- WHEN the scheduler is created and started
- THEN `scheduler.start()` completes before any `schedule_job()` calls

### Requirement: Scheduler Shutdown

The system MUST stop the scheduler during FastAPI lifespan shutdown, after all dependent tasks are cancelled.

#### Scenario: Scheduler stops on shutdown

- GIVEN the app is shutting down
- WHEN the lifespan cleanup block runs
- THEN `scheduler.stop()` is called
- AND `scheduler.is_running()` returns `False`

### Requirement: Autonomous Job Registration on Startup

The system MUST register the autonomous loop job handler in the scheduler's executor during startup. The job MUST use an interval trigger matching `NOVA_AUTONOMOUS_INTERVAL_HOURS`.

#### Scenario: Job registered with interval trigger

- GIVEN `NOVA_AUTONOMOUS_INTERVAL_HOURS=1` (default)
- WHEN the app starts and the scheduler is running
- THEN a job named "autonomous_cycle" is registered with `JobType.INTERVAL`
- AND the trigger interval is 3600 seconds

#### Scenario: Job uses configurable interval

- GIVEN `NOVA_AUTONOMOUS_INTERVAL_HOURS=4`
- WHEN the app starts
- THEN the registered job has trigger interval of 14400 seconds

#### Scenario: Job has timeout and retry limits

- GIVEN the autonomous job is registered
- WHEN inspected
- THEN the job has `timeout=300` (5 minutes) and `max_retries=1`

### Requirement: Scheduler API Endpoints

The existing scheduler API endpoints MUST remain functional and accessible. The scheduler router MUST be included in the v1 API router.

#### Scenario: Scheduler endpoints accessible

- GIVEN the app is running
- WHEN `GET /api/v1/scheduler/health` is called
- THEN response is HTTP 200 with scheduler health information

#### Scenario: List jobs includes autonomous job

- GIVEN the autonomous job is registered
- WHEN `GET /api/v1/scheduler/jobs` is called
- THEN the response includes the "autonomous_cycle" job

### Requirement: In-Memory Persistence Acceptance

Scheduler job state is in-memory and NOT persisted to Postgres. Jobs are lost on restart and re-registered via the startup step. This is an accepted tradeoff for Fase C.

#### Scenario: Jobs lost on restart

- GIVEN the scheduler has registered jobs
- WHEN the server restarts
- THEN all previous job state is lost
- AND the startup step re-registers the autonomous job

#### Scenario: No Postgres dependency for scheduler

- GIVEN the scheduler module
- WHEN inspected
- THEN it does not import or depend on any Postgres models or repositories
