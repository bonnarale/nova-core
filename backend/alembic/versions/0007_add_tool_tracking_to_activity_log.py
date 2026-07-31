"""Add tool tracking fields to activity_log

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tool tracking columns
    op.add_column("activity_log", sa.Column("tool_name", sa.String(100), nullable=True))
    op.add_column("activity_log", sa.Column("tool_params", JSONB, nullable=True))
    op.add_column("activity_log", sa.Column("tool_result", JSONB, nullable=True))
    op.add_column("activity_log", sa.Column("duration_ms", sa.Integer(), nullable=True))
    op.add_column("activity_log", sa.Column("session_id", UUID(as_uuid=True), nullable=True))

    # Add indexes for tool queries
    op.create_index("ix_activity_log_tool", "activity_log", ["tool_name"])
    op.create_index("ix_activity_log_session", "activity_log", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_activity_log_session", table_name="activity_log")
    op.drop_index("ix_activity_log_tool", table_name="activity_log")
    op.drop_column("activity_log", "session_id")
    op.drop_column("activity_log", "duration_ms")
    op.drop_column("activity_log", "tool_result")
    op.drop_column("activity_log", "tool_params")
    op.drop_column("activity_log", "tool_name")
