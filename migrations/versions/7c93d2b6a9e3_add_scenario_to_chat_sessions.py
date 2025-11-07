"""add_scenario_to_chat_sessions

Revision ID: 7c93d2b6a9e3
Revises: 339d0e4c48e5
Create Date: 2025-11-07 21:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c93d2b6a9e3'
down_revision: Union[str, Sequence[str], None] = '339d0e4c48e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add scenario/context support for chat sessions."""
    # Add new columns
    op.add_column('chat_sessions', sa.Column('scenario', sa.String(length=32), nullable=False, server_default='recommendation'))
    op.add_column('chat_sessions', sa.Column('context', sa.Text(), nullable=True))

    # Ensure existing rows have scenario set to recommendation
    op.execute("UPDATE chat_sessions SET scenario = 'recommendation' WHERE scenario IS NULL")

    # Allow recommendation_id to be nullable for non-recommendation chats
    op.alter_column('chat_sessions', 'recommendation_id', existing_type=sa.Integer(), nullable=True)

    # Drop server default so future inserts must specify scenario explicitly if different
    op.alter_column('chat_sessions', 'scenario', server_default=None)

    # Add helpful index for lookup by user and scenario
    op.create_index('ix_chat_sessions_user_scenario', 'chat_sessions', ['user_id', 'scenario'])


def downgrade() -> None:
    """Revert scenario/context support additions."""
    # Remove analytics sessions (they have NULL recommendation_id)
    op.execute('DELETE FROM chat_sessions WHERE recommendation_id IS NULL')

    # Restore NOT NULL constraint on recommendation_id
    op.alter_column('chat_sessions', 'recommendation_id', existing_type=sa.Integer(), nullable=False)

    # Drop added index
    op.drop_index('ix_chat_sessions_user_scenario', table_name='chat_sessions')

    # Drop added columns
    op.drop_column('chat_sessions', 'context')
    op.drop_column('chat_sessions', 'scenario')

