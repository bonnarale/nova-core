"""Create activity_log table.

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "activity_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "goal_id",
            UUID(as_uuid=True),
            sa.ForeignKey("goals.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("goal_title", sa.String(255), nullable=True),
        sa.Column("goal_priority", sa.Integer(), nullable=True),
        sa.Column("approval_id", sa.String(100), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("details", JSONB, nullable=True, default=dict),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_activity_log_user_created",
        "activity_log",
        ["user_id", "created_at"],
    )
    op.create_index("ix_activity_log_goal", "activity_log", ["goal_id"])


def downgrade() -> None:
    op.drop_index("ix_activity_log_goal", table_name="activity_log")
    op.drop_index("ix_activity_log_user_created", table_name="activity_log")
    op.drop_table("activity_log")
