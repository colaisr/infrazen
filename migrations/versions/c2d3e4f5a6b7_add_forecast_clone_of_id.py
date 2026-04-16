"""add clone_of_id to board_forecast_resources for split cost across groups

Revision ID: c2d3e4f5a6b7
Revises: a9f8e7d6c5b4
Create Date: 2026-04-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, Sequence[str], None] = 'a9f8e7d6c5b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'board_forecast_resources',
        sa.Column('clone_of_id', sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f('ix_board_forecast_resources_clone_of_id'),
        'board_forecast_resources',
        ['clone_of_id'],
        unique=False,
    )
    op.create_foreign_key(
        'fk_board_forecast_resources_clone_of_id',
        'board_forecast_resources',
        'board_forecast_resources',
        ['clone_of_id'],
        ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint('fk_board_forecast_resources_clone_of_id', 'board_forecast_resources', type_='foreignkey')
    op.drop_index(op.f('ix_board_forecast_resources_clone_of_id'), table_name='board_forecast_resources')
    op.drop_column('board_forecast_resources', 'clone_of_id')
