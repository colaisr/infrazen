"""add generated reports table

Revision ID: 8139f6939d1c
Revises: 7c93d2b6a9e3
Create Date: 2025-11-07 22:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8139f6939d1c'
down_revision: Union[str, Sequence[str], None] = '7c93d2b6a9e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'generated_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('status', sa.Enum('in_progress', 'ready', 'failed', name='reportstatus'), nullable=False),
        sa.Column('content_html', sa.Text(), nullable=True),
        sa.Column('context_json', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_generated_reports_role'), 'generated_reports', ['role'], unique=False)
    op.create_index(op.f('ix_generated_reports_status'), 'generated_reports', ['status'], unique=False)
    op.create_index(op.f('ix_generated_reports_user_id'), 'generated_reports', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_generated_reports_user_id'), table_name='generated_reports')
    op.drop_index(op.f('ix_generated_reports_status'), table_name='generated_reports')
    op.drop_index(op.f('ix_generated_reports_role'), table_name='generated_reports')
    op.drop_table('generated_reports')
    op.execute('DROP TYPE IF EXISTS reportstatus')

