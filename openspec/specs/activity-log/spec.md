# Activity Log Specification

## Purpose

Persist a durable audit trail of all autonomous actions in Postgres. Each entry records what was reviewed, what happened, and when — surviving server restarts.

## Requirements

### Requirement: Activity Log Model

The system MUST define an `ActivityLog` SQLAlchemy model mapped to the `activity_log` table in Postgres. The table MUST persist across restarts.

#### Scenario: Table created on startup

- GIVEN the app starts and connects to Postgres
- WHEN the database is initialized
- THEN the `activity_log` table exists with the correct schema

#### Scenario: Schema columns

- GIVEN the `activity_log` table
- WHEN inspected
- THEN it contains: `id` (UUID PK), `timestamp` (timestamptz, server default now), `status` (varchar), `goal_id` (UUID, nullable), `goal_title` (varchar, nullable), `action_summary` (text, nullable), `error_message` (text, nullable), `autonomy_level` (varchar, nullable), `metadata` (JSONB, nullable)

### Requirement: Activity Log Persistence

The system MUST write activity log entries to Postgres via an `ActivityLogRepository`. Writes MUST be durable (committed to DB), not in-memory.

#### Scenario: Entry persisted after successful execution

- GIVEN an autonomous action completed successfully
- WHEN the activity log entry is created
- THEN a row exists in the `activity_log` table with status "executed"
- AND the row is queryable via the API

#### Scenario: Entry persisted after failed execution

- GIVEN an autonomous action failed with an error
- WHEN the activity log entry is created
- THEN a row exists in the `activity_log` table with status "failed"
- AND `error_message` contains the error text

#### Scenario: Entry persisted after skipped goal

- GIVEN a goal was skipped (blocked or autonomy too low)
- WHEN the activity log entry is created
- THEN a row exists in the `activity_log` table with status "skipped"
- AND `metadata` contains the skip reason

### Requirement: Activity Log Query

The system MUST expose a method to retrieve recent activity log entries, ordered by timestamp descending.

#### Scenario: List recent entries

- GIVEN 5 activity log entries exist in the database
- WHEN `list_recent(limit=3)` is called
- THEN 3 entries are returned, ordered by timestamp descending (newest first)

#### Scenario: Empty database

- GIVEN no activity log entries exist
- WHEN `list_recent()` is called
- THEN an empty list is returned

#### Scenario: Default limit

- GIVEN 50 activity log entries exist
- WHEN `list_recent()` is called without a limit
- THEN 20 entries are returned (default limit)

### Requirement: Activity Log API Endpoint

The system MUST expose a `GET /api/v1/activity` endpoint that returns recent activity entries for the Dashboard.

#### Scenario: Successful response

- GIVEN activity log entries exist
- WHEN `GET /api/v1/activity?limit=10` is called
- THEN response is HTTP 200 with body `{ "entries": [...], "total": N }`
- AND each entry contains `id`, `timestamp`, `status`, `goal_id`, `goal_title`, `action_summary`, `error_message`, `autonomy_level`

#### Scenario: Query with limit parameter

- GIVEN activity log entries exist
- WHEN `GET /api/v1/activity?limit=5` is called
- THEN at most 5 entries are returned

#### Scenario: No entries

- GIVEN no activity log entries exist
- WHEN `GET /api/v1/activity` is called
- THEN response is HTTP 200 with `{ "entries": [], "total": 0 }`

### Requirement: Activity Log Frontend Display

The system MUST display a "Actividad reciente" Card in the Dashboard showing the latest autonomous activity entries.

#### Scenario: Dashboard card renders

- GIVEN the Dashboard page loads
- WHEN activity data is fetched from `GET /api/v1/activity?limit=5`
- THEN a Card titled "Actividad reciente" is rendered below existing sections

#### Scenario: Activity entry display

- GIVEN an activity entry has status "executed" and goal_title "Build API"
- WHEN rendered in the Dashboard
- THEN the entry shows the goal title, status badge (green for executed), and timestamp

#### Scenario: Activity entry with error

- GIVEN an activity entry has status "failed" and error_message "timeout"
- WHEN rendered in the Dashboard
- THEN the entry shows a red status badge and the error message

#### Scenario: Empty activity

- GIVEN no activity entries exist
- WHEN the Dashboard loads
- THEN the "Actividad reciente" Card shows "No activity yet" or equivalent empty state
