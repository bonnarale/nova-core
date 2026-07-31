"""Create learning_artifacts, kg_entities, kg_relationships tables.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── learning_artifacts ──────────────────────────────────────────────
    op.create_table(
        "learning_artifacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("artifact_type", sa.String(30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True, default=""),
        sa.Column("tags", JSONB, nullable=True, default=list),
        sa.Column("source_execution_id", sa.String(255), nullable=True),
        sa.Column("source_task_id", sa.String(255), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("agent_id", sa.String(100), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True, default=0.0),
        sa.Column("importance_score", sa.Float(), nullable=True, default=0.0),
        sa.Column("access_count", sa.Integer(), nullable=False, default=0),
        sa.Column("metadata_", JSONB, nullable=True, default=dict),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index("ix_la_artifact_type", "learning_artifacts", ["artifact_type"])
    op.create_index("ix_la_user_id", "learning_artifacts", ["user_id"])
    op.create_index("ix_la_source_execution", "learning_artifacts", ["source_execution_id"])

    # ── kg_entities (stub for Phase 2) ──────────────────────────────────
    op.create_table(
        "kg_entities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True, default=""),
        sa.Column("tags", JSONB, nullable=True, default=list),
        sa.Column("properties", JSONB, nullable=True, default=dict),
        sa.Column("status", sa.String(20), nullable=False, default="ACTIVE"),
        sa.Column("confidence", sa.Float(), nullable=True, default=1.0),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index("ix_kge_type", "kg_entities", ["entity_type"])
    op.create_index("ix_kge_name", "kg_entities", ["name"])

    # ── kg_relationships (stub for Phase 2) ─────────────────────────────
    op.create_table(
        "kg_relationships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            UUID(as_uuid=True),
            sa.ForeignKey("kg_entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_id",
            UUID(as_uuid=True),
            sa.ForeignKey("kg_entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relationship_type", sa.String(30), nullable=False),
        sa.Column("properties", JSONB, nullable=True, default=dict),
        sa.Column("weight", sa.Float(), nullable=True, default=1.0),
        sa.Column("status", sa.String(20), nullable=False, default="ACTIVE"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index("ix_kgr_source", "kg_relationships", ["source_id"])
    op.create_index("ix_kgr_target", "kg_relationships", ["target_id"])
    op.create_index("ix_kgr_type", "kg_relationships", ["relationship_type"])


def downgrade() -> None:
    op.drop_table("kg_relationships")
    op.drop_table("kg_entities")
    op.drop_index("ix_la_source_execution", table_name="learning_artifacts")
    op.drop_index("ix_la_user_id", table_name="learning_artifacts")
    op.drop_index("ix_la_artifact_type", table_name="learning_artifacts")
    op.drop_table("learning_artifacts")
