# Database

## Overview

NOVA CORE uses SQLAlchemy 2.0 async ORM with PostgreSQL (via asyncpg) and Alembic for migrations.

## ORM Models

### ConversationSession
Tracks user conversation sessions.
- `id` — UUID primary key
- `user_id` — User identifier
- `created_at`, `updated_at` — Timestamps
- `status` — Session status (active, closed)
- `metadata` — JSON metadata

### ConversationMessage
Individual messages within a session.
- `id` — UUID primary key
- `session_id` — FK to ConversationSession
- `role` — Message role (user, assistant, system)
- `content` — Message content
- `created_at` — Timestamp

### OrchestratorTask
Task tracking for the orchestrator.
- `id` — UUID primary key
- `goal_id` — FK to Goal
- `name` — Task name
- `status` — Task state
- `priority` — Task priority
- `assignee` — Assigned agent
- `metadata` — JSON metadata

### Goal
User goals and objectives.
- `id` — UUID primary key
- `user_id` — User identifier
- `name` — Goal name
- `description` — Goal description
- `status` — Goal state
- `priority` — Goal priority
- `parent_id` — FK for sub-goals

### Agent
Agent registration and configuration.
- `id` — UUID primary key
- `name` — Agent name
- `type` — Agent type
- `status` — Agent status
- `capabilities` — JSON capabilities

### UserProfile
User profile information.
- `id` — UUID primary key
- `user_id` — User identifier
- `display_name` — Display name
- `preferences` — JSON preferences
- `created_at` — Timestamp

### LongTermMemoryEntry
Persistent memory entries.
- `id` — UUID primary key
- `content` — Memory content
- `memory_type` — Memory type (episodic, semantic, procedural)
- `importance` — Importance score
- `status` — Memory status

### WorkflowDefinitionModel
Workflow template definitions.
- `id` — UUID primary key
- `name` — Workflow name
- `description` — Description
- `steps` — JSON step definitions
- `status` — Workflow status
- `version` — Version string

### WorkflowExecutionModel
Workflow execution instances.
- `id` — UUID primary key
- `workflow_id` — FK to WorkflowDefinitionModel
- `status` — Execution status
- `results` — JSON results
- `started_at`, `completed_at` — Timestamps

### WorkflowEventModel
Workflow execution events.
- `id` — UUID primary key
- `execution_id` — FK to WorkflowExecutionModel
- `event_type` — Event type
- `payload` — JSON payload
- `created_at` — Timestamp

### KnowledgeGraphEntityModel
Knowledge graph entities.
- `id` — UUID primary key
- `name` — Entity name
- `entity_type` — Entity type (concept, person, place, etc.)
- `status` — Entity status
- `properties` — JSON properties

### KnowledgeGraphRelationshipModel
Knowledge graph relationships.
- `id` — UUID primary key
- `source_id` — FK to entity
- `target_id` — FK to entity
- `relationship_type` — Relationship type
- `status` — Relationship status
- `weight` — Relationship weight

## Repository Pattern

Each entity has a corresponding repository abstracting data access:

```
RepositoryProvider (ABC)
├── ConversationRepository
├── GoalRepository
├── TaskRepository
├── AgentRepository
├── UserProfileRepository
└── ...
```

## Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Connection Pool

Configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Connection URL |
| `DB_POOL_SIZE` | `10` | Pool size |
| `DB_MAX_OVERFLOW` | `20` | Max overflow |
| `DB_POOL_TIMEOUT` | `30` | Pool timeout |
