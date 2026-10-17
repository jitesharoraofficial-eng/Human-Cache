"""add_capture_inbox_table

Revision ID: 3e81a9f4c012
Revises: 120d63944f3c
Create Date: 2026-10-13 04:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e81a9f4c012'
down_revision: Union[str, Sequence[str], None] = '120d63944f3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema safely and additively."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "capture_inbox" not in tables:
        op.create_table(
            "capture_inbox",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("source_type", sa.String(length=50), nullable=False),
            sa.Column("source_url", sa.String(length=1000), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("content_text", sa.Text(), nullable=False),
            sa.Column("cleaned_html", sa.Text(), nullable=True),
            sa.Column("file_path", sa.String(length=500), nullable=True),
            sa.Column("file_type", sa.String(length=50), nullable=True),
            sa.Column("file_size_bytes", sa.Integer(), server_default="0"),
            sa.Column("recommended_category_id", sa.String(length=36), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
            sa.Column("recommended_category_name", sa.String(length=100), nullable=True),
            sa.Column("recommendation_confidence", sa.Float(), server_default="0.0"),
            sa.Column("recommendation_reason", sa.String(length=255), nullable=True),
            sa.Column("alternative_categories", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(length=50), server_default="pending_review"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("document_id", sa.String(length=36), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("capture_inbox")
