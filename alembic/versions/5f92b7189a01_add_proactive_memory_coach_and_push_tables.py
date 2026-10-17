"""add_proactive_memory_coach_and_push_tables

Revision ID: 5f92b7189a01
Revises: 3e81a9f4c012
Create Date: 2026-10-13 05:07:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f92b7189a01'
down_revision: Union[str, Sequence[str], None] = '3e81a9f4c012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema safely and additively."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    # 1. Update topic_memory_states
    if "topic_memory_states" in tables:
        mem_cols = [c["name"] for c in inspector.get_columns("topic_memory_states")]
        with op.batch_alter_table("topic_memory_states", schema=None) as batch_op:
            if "no_need_suppressed" not in mem_cols:
                batch_op.add_column(sa.Column("no_need_suppressed", sa.Boolean(), server_default="0"))
            if "suppressed_at" not in mem_cols:
                batch_op.add_column(sa.Column("suppressed_at", sa.DateTime(), nullable=True))

    # 2. Update notifications
    if "notifications" in tables:
        notif_cols = [c["name"] for c in inspector.get_columns("notifications")]
        with op.batch_alter_table("notifications", schema=None) as batch_op:
            if "action_state" not in notif_cols:
                batch_op.add_column(sa.Column("action_state", sa.String(length=50), server_default="active"))
            if "last_action_at" not in notif_cols:
                batch_op.add_column(sa.Column("last_action_at", sa.DateTime(), nullable=True))

    # 3. Create web_push_subscriptions
    if "web_push_subscriptions" not in tables:
        op.create_table(
            "web_push_subscriptions",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("endpoint", sa.Text(), nullable=False),
            sa.Column("p256dh", sa.String(length=255), nullable=False),
            sa.Column("auth", sa.String(length=255), nullable=False),
            sa.Column("user_agent", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "web_push_subscriptions" in tables:
        op.drop_table("web_push_subscriptions")

    if "notifications" in tables:
        with op.batch_alter_table("notifications", schema=None) as batch_op:
            batch_op.drop_column("last_action_at")
            batch_op.drop_column("action_state")

    if "topic_memory_states" in tables:
        with op.batch_alter_table("topic_memory_states", schema=None) as batch_op:
            batch_op.drop_column("suppressed_at")
            batch_op.drop_column("no_need_suppressed")
