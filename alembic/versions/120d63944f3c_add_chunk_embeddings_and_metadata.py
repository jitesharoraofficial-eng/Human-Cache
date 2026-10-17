"""add_chunk_embeddings_and_metadata

Revision ID: 120d63944f3c
Revises: 1769dc31f55e
Create Date: 2026-10-12 22:38:44.753713

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '120d63944f3c'
down_revision: Union[str, Sequence[str], None] = '1769dc31f55e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if table already exists (safe for pre-created SQLite)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    if "chunk_embeddings" not in tables:
        op.create_table(
            "chunk_embeddings",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("chunk_id", sa.String(length=36), sa.ForeignKey("source_chunks.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("document_id", sa.String(length=36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("embedding_json", sa.Text(), nullable=False),
            sa.Column("dimension", sa.Integer(), nullable=False),
            sa.Column("model_name", sa.String(length=100), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    chunk_cols = [c["name"] for c in inspector.get_columns("source_chunks")]
    if "section_heading" not in chunk_cols:
        with op.batch_alter_table("source_chunks", schema=None) as batch_op:
            batch_op.add_column(sa.Column("section_heading", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("chunk_embeddings")
    with op.batch_alter_table("source_chunks", schema=None) as batch_op:
        batch_op.drop_column("section_heading")
