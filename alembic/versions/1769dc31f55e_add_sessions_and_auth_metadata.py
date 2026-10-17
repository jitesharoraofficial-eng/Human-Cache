"""add_sessions_and_auth_metadata

Revision ID: 1769dc31f55e
Revises: 9d7ebfcbcfca
Create Date: 2026-10-12 06:08:47.033255

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1769dc31f55e'
down_revision: Union[str, Sequence[str], None] = '9d7ebfcbcfca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_demo_user", sa.Boolean(), server_default=sa.text("0"), nullable=False))
        batch_op.add_column(sa.Column("last_login_at", sa.DateTime(), nullable=True))

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("session_token_hash", sa.String(length=64), unique=True, index=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), default=False, nullable=False),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("ip_address", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("user_sessions")
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("last_login_at")
        batch_op.drop_column("is_demo_user")
