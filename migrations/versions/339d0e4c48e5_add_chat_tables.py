"""add_chat_tables

Revision ID: 339d0e4c48e5
Revises: b8136224cf9c
Create Date: 2025-11-05 15:45:35.198933

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '339d0e4c48e5'
down_revision: Union[str, Sequence[str], None] = 'b8136224cf9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create chat_sessions table
    op.create_table(
        'chat_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('recommendation_id', sa.Integer, sa.ForeignKey('optimization_recommendations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('last_activity_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('message_count', sa.Integer, nullable=False, default=0),
        sa.Column('status', sa.Enum('active', 'archived', name='chat_session_status'), nullable=False, server_default='active')
    )
    
    # Create indexes for chat_sessions
    op.create_index('ix_chat_sessions_user_id', 'chat_sessions', ['user_id'])
    op.create_index('ix_chat_sessions_recommendation_id', 'chat_sessions', ['recommendation_id'])
    op.create_index('ix_chat_sessions_last_activity_at', 'chat_sessions', ['last_activity_at'])
    op.create_index('ix_chat_sessions_user_rec', 'chat_sessions', ['user_id', 'recommendation_id'])
    
    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.Enum('user', 'assistant', 'system', name='chat_message_role'), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('tokens', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now())
    )
    
    # Create indexes for chat_messages
    op.create_index('ix_chat_messages_session_id', 'chat_messages', ['session_id'])
    op.create_index('ix_chat_messages_created_at', 'chat_messages', ['created_at'])
    op.create_index('ix_chat_messages_session_created', 'chat_messages', ['session_id', 'created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes first
    op.drop_index('ix_chat_messages_session_created', 'chat_messages')
    op.drop_index('ix_chat_messages_created_at', 'chat_messages')
    op.drop_index('ix_chat_messages_session_id', 'chat_messages')
    
    # Drop chat_messages table
    op.drop_table('chat_messages')
    
    # Drop chat_sessions indexes
    op.drop_index('ix_chat_sessions_user_rec', 'chat_sessions')
    op.drop_index('ix_chat_sessions_last_activity_at', 'chat_sessions')
    op.drop_index('ix_chat_sessions_recommendation_id', 'chat_sessions')
    op.drop_index('ix_chat_sessions_user_id', 'chat_sessions')
    
    # Drop chat_sessions table
    op.drop_table('chat_sessions')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS chat_message_role")
    op.execute("DROP TYPE IF EXISTS chat_session_status")
