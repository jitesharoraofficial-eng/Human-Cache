"""add_concept_inventories_and_flashcard_metadata

Revision ID: d2370fa2a744
Revises: 5f92b7189a01
Create Date: 2026-10-13 05:30:26.620653

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2370fa2a744'
down_revision: Union[str, Sequence[str], None] = '5f92b7189a01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create document_concept_inventories table
    op.create_table(
        'document_concept_inventories',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('document_id', sa.String(length=36), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('outline_json', sa.JSON(), nullable=True),
        sa.Column('concepts_json', sa.JSON(), nullable=True),
        sa.Column('sections_count', sa.Integer(), server_default='0'),
        sa.Column('concepts_count', sa.Integer(), server_default='0'),
        sa.Column('status', sa.String(length=50), server_default='verified'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True)
    )

    # 2. Add detail_level, version, and section_name to flashcard_decks
    with op.batch_alter_table('flashcard_decks') as batch_op:
        batch_op.add_column(sa.Column('detail_level', sa.String(length=50), server_default='semi-detailed'))
        batch_op.add_column(sa.Column('version', sa.Integer(), server_default='1'))
        batch_op.add_column(sa.Column('section_name', sa.String(length=255), nullable=True))

    # 3. Add detail_level, concept_id, section_name, and source_citation to flashcards
    with op.batch_alter_table('flashcards') as batch_op:
        batch_op.add_column(sa.Column('detail_level', sa.String(length=50), server_default='semi-detailed'))
        batch_op.add_column(sa.Column('concept_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('section_name', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('source_citation', sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('flashcards') as batch_op:
        batch_op.drop_column('source_citation')
        batch_op.drop_column('section_name')
        batch_op.drop_column('concept_id')
        batch_op.drop_column('detail_level')

    with op.batch_alter_table('flashcard_decks') as batch_op:
        batch_op.drop_column('section_name')
        batch_op.drop_column('version')
        batch_op.drop_column('detail_level')

    op.drop_table('document_concept_inventories')
