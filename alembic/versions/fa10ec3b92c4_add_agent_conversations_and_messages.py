"""add_agent_conversations_and_messages

Revision ID: fa10ec3b92c4
Revises: d2370fa2a744
Create Date: 2026-10-15 20:03:59.882140

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa10ec3b92c4'
down_revision: Union[str, Sequence[str], None] = 'd2370fa2a744'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Additive upgrade schema for Agent conversations and messages."""
    op.create_table(
        'agent_conversations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('topic_id', sa.String(length=36), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_conversations_user_id'), 'agent_conversations', ['user_id'], unique=False)

    op.create_table(
        'agent_messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('conversation_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tool_calls', sa.JSON(), nullable=True),
        sa.Column('tool_call_id', sa.String(length=100), nullable=True),
        sa.Column('citations', sa.JSON(), nullable=True),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['agent_conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_messages_conversation_id'), 'agent_messages', ['conversation_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_agent_messages_conversation_id'), table_name='agent_messages')
    op.drop_table('agent_messages')
    op.drop_index(op.f('ix_agent_conversations_user_id'), table_name='agent_conversations')
    op.drop_table('agent_conversations')
