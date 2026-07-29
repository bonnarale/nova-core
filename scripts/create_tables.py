"""Drop and recreate tables to match SQLAlchemy models exactly."""
import asyncio
import asyncpg
import os


DROP_AND_CREATE = {
    "agents": """
        DROP TABLE IF EXISTS agents CASCADE;
        CREATE TABLE agents (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            role VARCHAR NOT NULL,
            description TEXT DEFAULT '',
            system_prompt TEXT DEFAULT '',
            allowed_tools JSONB DEFAULT '[]',
            memory_scope VARCHAR DEFAULT 'session',
            permissions JSONB DEFAULT '{}',
            supported_models JSONB DEFAULT '[]',
            status VARCHAR DEFAULT 'active',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "goals": """
        DROP TABLE IF EXISTS goals CASCADE;
        CREATE TABLE goals (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            priority INTEGER NOT NULL DEFAULT 3,
            progress INTEGER NOT NULL DEFAULT 0,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "orchestrator_tasks": """
        DROP TABLE IF EXISTS orchestrator_tasks CASCADE;
        CREATE TABLE orchestrator_tasks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            goal TEXT NOT NULL,
            plan JSONB DEFAULT '{}',
            steps JSONB DEFAULT '[]',
            current_step INTEGER NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'CREATED',
            dependencies JSONB DEFAULT '[]',
            artifacts JSONB DEFAULT '{}',
            events JSONB DEFAULT '[]',
            assigned_agent VARCHAR(100),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            started_at TIMESTAMP,
            completed_at TIMESTAMP
        )
    """,
    "workflow_definitions": """
        DROP TABLE IF EXISTS workflow_definitions CASCADE;
        CREATE TABLE workflow_definitions (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            description TEXT DEFAULT '',
            steps JSONB DEFAULT '[]',
            status VARCHAR DEFAULT 'draft',
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "workflow_executions": """
        DROP TABLE IF EXISTS workflow_executions CASCADE;
        CREATE TABLE workflow_executions (
            id VARCHAR PRIMARY KEY,
            workflow_id VARCHAR NOT NULL,
            status VARCHAR DEFAULT 'pending',
            current_step INTEGER DEFAULT 0,
            result JSONB,
            metadata JSONB DEFAULT '{}',
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "workflow_events": """
        DROP TABLE IF EXISTS workflow_events CASCADE;
        CREATE TABLE workflow_events (
            id VARCHAR PRIMARY KEY,
            execution_id VARCHAR NOT NULL,
            event_type VARCHAR NOT NULL,
            data JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "knowledge_graph_entities": """
        DROP TABLE IF EXISTS knowledge_graph_entities CASCADE;
        CREATE TABLE knowledge_graph_entities (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            entity_type VARCHAR NOT NULL,
            properties JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "knowledge_graph_relationships": """
        DROP TABLE IF EXISTS knowledge_graph_relationships CASCADE;
        CREATE TABLE knowledge_graph_relationships (
            id VARCHAR PRIMARY KEY,
            source_id VARCHAR NOT NULL,
            target_id VARCHAR NOT NULL,
            relationship_type VARCHAR NOT NULL,
            properties JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "long_term_memory": """
        DROP TABLE IF EXISTS long_term_memory CASCADE;
        CREATE TABLE long_term_memory (
            id VARCHAR PRIMARY KEY,
            memory_type VARCHAR NOT NULL,
            content TEXT NOT NULL,
            summary TEXT,
            tags JSONB DEFAULT '[]',
            categories JSONB DEFAULT '[]',
            entities JSONB DEFAULT '[]',
            importance_score INTEGER DEFAULT 0,
            status VARCHAR DEFAULT 'active',
            linked_memory_ids JSONB DEFAULT '[]',
            source VARCHAR,
            source_id VARCHAR,
            user_id UUID,
            project_id VARCHAR,
            agent_id VARCHAR,
            access_count INTEGER DEFAULT 0,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            accessed_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """,
}


async def main():
    conn = await asyncpg.connect(
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        user=os.environ.get("POSTGRES_USER", "nova_core"),
        password=os.environ.get("POSTGRES_PASSWORD", "nova-core-postgres-password"),
        database=os.environ.get("POSTGRES_DB", "nova_core"),
    )

    for table_name, sql in DROP_AND_CREATE.items():
        print(f"Recreating table: {table_name}")
        await conn.execute(sql)

    rows = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
    )
    print("\nAll tables:")
    for r in rows:
        print(f"  - {r['tablename']}")

    await conn.close()


asyncio.run(main())
