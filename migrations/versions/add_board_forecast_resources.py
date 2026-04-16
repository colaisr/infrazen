"""add board_forecast_resources for business context cost forecasts

Revision ID: a9f8e7d6c5b4
Revises: e4c1a7b2d9f0
Create Date: 2026-04-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a9f8e7d6c5b4'
down_revision: Union[str, Sequence[str], None] = 'e4c1a7b2d9f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'board_forecast_resources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('board_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('monthly_cost', sa.Float(), nullable=False, server_default='0'),
        sa.Column('position_x', sa.Float(), nullable=False),
        sa.Column('position_y', sa.Float(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['board_id'], ['business_boards.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['group_id'], ['board_groups.id'], ondelete='SET NULL'),
    )
    op.create_index(op.f('ix_board_forecast_resources_board_id'), 'board_forecast_resources', ['board_id'], unique=False)
    op.create_index(op.f('ix_board_forecast_resources_group_id'), 'board_forecast_resources', ['group_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_board_forecast_resources_group_id'), table_name='board_forecast_resources')
    op.drop_index(op.f('ix_board_forecast_resources_board_id'), table_name='board_forecast_resources')
    op.drop_table('board_forecast_resources')
