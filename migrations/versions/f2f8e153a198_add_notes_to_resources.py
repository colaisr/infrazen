"""add_notes_to_resources

Revision ID: f2f8e153a198
Revises: 3f5e7a9b1c2d
Create Date: 2025-10-26 23:38:45.089295

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2f8e153a198'
down_revision: Union[str, Sequence[str], None] = '3f5e7a9b1c2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add notes column to resources table."""
    op.add_column('resources', sa.Column('notes', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema - Remove notes column from resources table."""
    op.drop_column('resources', 'notes')
