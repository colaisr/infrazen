"""add business context tables

Revision ID: 3f5e7a9b1c2d
Revises: 2c4970b953a4
Create Date: 2025-10-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '3f5e7a9b1c2d'
down_revision: Union[str, Sequence[str], None] = 'remove_aws_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create business context tables."""
    
    # Create business_boards table
    op.create_table(
        'business_boards',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('canvas_state', sa.JSON(), nullable=True),
        sa.Column('viewport', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_business_boards_user_id'), 'business_boards', ['user_id'], unique=False)
    
    # Create board_groups table
    op.create_table(
        'board_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('board_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('fabric_id', sa.String(length=100), nullable=False),
        sa.Column('position_x', sa.Float(), nullable=False),
        sa.Column('position_y', sa.Float(), nullable=False),
        sa.Column('width', sa.Float(), nullable=False),
        sa.Column('height', sa.Float(), nullable=False),
        sa.Column('color', sa.String(length=20), nullable=False, server_default='#3B82F6'),
        sa.Column('calculated_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['board_id'], ['business_boards.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('board_id', 'fabric_id', name='unique_fabric_id_per_board')
    )
    op.create_index(op.f('ix_board_groups_board_id'), 'board_groups', ['board_id'], unique=False)
    
    # Create board_resources table
    op.create_table(
        'board_resources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('board_id', sa.Integer(), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=False),
        sa.Column('position_x', sa.Float(), nullable=False),
        sa.Column('position_y', sa.Float(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['board_id'], ['business_boards.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resource_id'], ['resources.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['group_id'], ['board_groups.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('board_id', 'resource_id', name='unique_resource_per_board')
    )
    op.create_index(op.f('ix_board_resources_board_id'), 'board_resources', ['board_id'], unique=False)
    op.create_index(op.f('ix_board_resources_resource_id'), 'board_resources', ['resource_id'], unique=False)
    op.create_index(op.f('ix_board_resources_group_id'), 'board_resources', ['group_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema - remove business context tables."""
    
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_index(op.f('ix_board_resources_group_id'), table_name='board_resources')
    op.drop_index(op.f('ix_board_resources_resource_id'), table_name='board_resources')
    op.drop_index(op.f('ix_board_resources_board_id'), table_name='board_resources')
    op.drop_table('board_resources')
    
    op.drop_index(op.f('ix_board_groups_board_id'), table_name='board_groups')
    op.drop_table('board_groups')
    
    op.drop_index(op.f('ix_business_boards_user_id'), table_name='business_boards')
    op.drop_table('business_boards')

